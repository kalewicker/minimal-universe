"""Run the registered fixture and rejection checks for the R06j adapter."""
import argparse
from copy import deepcopy
from fractions import Fraction as F
from hashlib import sha256
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.bookkeep_r06j import COMPONENTS, canonical, require, summarize


def audit(protocol):
    fixture_path = ROOT / 'fixtures/r06j/panel.json'
    fixture = json.loads(fixture_path.read_bytes())
    result = summarize(fixture)
    require(result['roster_count'] == 4 and result['planned_branch_count'] == 24,
            'planned denominators')
    require(result['admission_counts'] == {'eligible': 2, 'ineligible': 1, 'ambiguous_patch': 1}
            and result['admitted_weight'] == 4, 'admission accounting')

    # Hand-derived from the fixture event counts and known or unknown endpoints.
    expected = {
        'lex_first': ((F(-13, 100), F(101, 400)), (F(-5, 8), F(1, 8)),
                      (F(-7, 8), F(1, 4)), (F(-1, 2), F(5, 8)), (F(-1, 2), F(5, 8))),
        'lex_last': ((F(-2, 5), F(101, 400)), (F(-5, 8), F(1, 8)),
                     (F(-7, 8), F(1, 4)), (F(-1, 2), F(5, 8)), (F(-1, 2), F(5, 8))),
        'uniform_match': ((F(-13, 100), F(-49, 400)), (F(-5, 8), F(-1, 4)),
                          (F(-7, 8), F(-1, 8)), (F(-1, 2), F(1, 4)), (F(-1, 2), F(1, 4))),
    }
    for key, intervals in expected.items():
        row = result['by_scheduler'][key]
        require(row['weighted_bounds'] == dict(zip(COMPONENTS, intervals)), f'{key} manual oracle')
        require(row['parent_count'] == 2 and row['branch_count'] == 8,
                f'{key} fixed denominator')
        require(row['outcome_counts']['reached_snapshot_missing'] == 1
                and row['outcome_counts']['reached_empty'] == 1
                and row['outcome_counts']['terminal_empty'] == 1,
                f'{key} separate endpoint categories')

    shuffled = {key: list(reversed(rows)) for key, rows in fixture.items()}
    require(canonical(summarize(shuffled)) == canonical(result), 'arrival order invariance')
    no_eligible = summarize(dict(parents=fixture['parents'][2:], branches=[]))
    require(no_eligible['roster_count'] == 2 and no_eligible['admitted_weight'] == 0
            and all(row['weighted_bounds'] is None for row in no_eligible['by_scheduler'].values()),
            'empty eligible denominator')

    checks = (
        ('duplicate_parent', 'parents', 0, None, None, 'invalid or duplicate fixture parent'),
        ('nonpositive_weight', 'parents', 0, 'weight', [0, 1], 'positive integers'),
        ('invalid_initial_graph', 'parents', 0, 'initial', {'nodes': 4, 'edges': [[0, 4]]},
         'invalid endpoints'),
        ('foreign_parent', 'parents', 0, 'key', 'production/sample', 'invalid or duplicate fixture parent'),
        ('duplicate_orientation', 'branches', 0, None, None, 'unexpected or duplicate branch slot'),
        ('missing_orientation', 'branches', -1, None, None, 'missing branch record'),
        ('invalid_orientation', 'branches', 0, 'orientation', True, 'invalid slot identity'),
        ('unregistered_scheduler', 'branches', 0, 'scheduler', 'extra', 'unexpected or duplicate'),
        ('misassigned_partition', 'branches', 0, 'partition', 'wrong', 'partition inheritance'),
        ('misordered_patch', 'branches', 0, 'patch', [0, 2, 1, 3], 'patch mismatch'),
        ('branch_for_ineligible_parent', 'branches', 0, 'parent', fixture['parents'][2]['key'],
         'unexpected or duplicate branch slot'),
        ('terminal_with_nonreciprocal_path', 'branches', 0, 'endpoint',
         {'nodes': 4, 'edges': [[0, 1], [1, 2]]}, 'terminal snapshot still has an eligible path'),
        ('missing_snapshot_without_known_reach', 'branches', 4, 'events', 49,
         'missing snapshot requires known reach'),
        ('censor_with_snapshot', 'branches', 5, 'endpoint', {'nodes': 4, 'edges': []},
         'unresolved record has an endpoint'),
        ('unstarted_with_prefix', 'branches', 7, 'events', 1, 'unstarted branch has a prefix'),
    )
    rejected = []
    for name, section, index, field, value, expected_error in checks:
        payload = deepcopy(fixture)
        if field is not None:
            payload[section][index][field] = value
        elif index == -1:
            payload[section].pop()
        else:
            payload[section].append(deepcopy(payload[section][index]))
        try:
            summarize(payload)
        except ValueError as exc:
            require(expected_error in str(exc), f'{name} unexpected rejection: {exc}')
            rejected.append(name)
        else:
            raise ValueError(f'{name} was accepted')

    require(len(rejected) == protocol['expected_rejections'], 'rejection denominator')
    return dict(protocol_id=protocol['protocol_id'], fixture_summary=result,
                rejected_cases=rejected, order_invariance='passed',
                no_eligible_denominator='passed', scientific_status='untested',
                new_graph_transitions=0, empirical_assay_rows_scored=0)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output', type=Path)
    mode.add_argument('--verify', type=Path)
    args = parser.parse_args()
    data = (ROOT / 'protocols/r06j.json').read_bytes()
    protocol = json.loads(data)
    for name, digest in protocol['pins_sha256'].items():
        require(sha256((ROOT / name).read_bytes()).hexdigest() == digest, f'pin {name}')
    binding = dict(protocol_sha256=sha256(data).hexdigest())
    if args.output:
        args.output.mkdir(parents=True)
        (args.output / 'started.json').write_bytes(canonical(binding))
    try:
        receipt = canonical(audit(protocol) | binding)
        if args.verify:
            require(args.verify.read_bytes() == receipt, 'adapter receipt mismatch')
        else:
            (args.output / 'receipt.json').write_bytes(receipt)
        print('Matched three independent scheduler summaries and rejected 15 invalid fixtures.')
    except Exception as exc:
        if args.output:
            (args.output / 'failure.json').write_bytes(canonical(binding | dict(error=str(exc))))
        raise


if __name__ == '__main__':
    main()
