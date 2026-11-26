"""Check a terminal-aware assay design on fixed synthetic outcome records."""
import argparse
from collections import Counter
from fractions import Fraction
from hashlib import sha256
from itertools import product
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
HORIZON = 50
THRESHOLDS = (Fraction(0), Fraction(1, 2), Fraction(1))
UNRESOLVED = {'resource_censored', 'domain_unsupported', 'not_started'}


def require(ok, message):
    if not ok:
        raise ValueError(message)


def bounds(status, events, score):
    """Return exact interval endpoints for progress, reach and joint structure."""
    require(type(events) is int and 0 <= events <= HORIZON, 'invalid event count')
    require(score is None or isinstance(score, Fraction) and 0 <= score <= 1,
            'invalid reciprocity score')
    zeros = ((0, 0),) * len(THRESHOLDS)
    progress = Fraction(events, HORIZON)
    if status == 'reached':
        require(events == HORIZON, 'reached before horizon')
        joint = tuple((hit, hit) for hit in
                      (int(score is not None and score >= q) for q in THRESHOLDS))
        return ((1, 1), (1, 1), *joint)
    if status == 'terminal':
        require(events < HORIZON, 'terminal at horizon must be recorded as reached')
        require(score in (None, 0), 'terminal graph cannot contain reciprocal edges')
        return ((progress, progress), (0, 0), *zeros)
    require(status in UNRESOLVED and events < HORIZON and score is None,
            'invalid unresolved record')
    require(status != 'not_started' or events == 0, 'unstarted branch has a prefix')
    unknown = ((0, 1),) * len(THRESHOLDS)
    return ((progress, 1), (0, 1), *unknown)


def contrast(branches):
    require(len(branches) == 4, 'expected two target and two sham orientations')
    intervals = [bounds(*branch) for branch in branches]
    return tuple(((a[0] + b[0] - c[1] - d[1]) / Fraction(2),
                  (a[1] + b[1] - c[0] - d[0]) / Fraction(2))
                 for a, b, c, d in zip(*intervals))


def oracle(branch):
    """Enumerate extremal completions including empty and threshold endpoints."""
    status, events, score = branch
    if status in UNRESOLVED:
        possibilities = [(events, None)] + [(HORIZON, q) for q in (None, *THRESHOLDS)]
    else:
        possibilities = [(events, score)]
    return {
        (Fraction(t, HORIZON), int(t == HORIZON),
         *(int(t == HORIZON and q is not None and q >= threshold)
           for threshold in THRESHOLDS))
        for t, q in possibilities
    }


def oracle_contrast(branches):
    values = [tuple((a + b - c - d) / Fraction(2) for a, b, c, d in zip(*arms))
              for arms in product(*(oracle(branch) for branch in branches))]
    return tuple((min(column), max(column)) for column in zip(*values))


def fixtures():
    return (
        ('terminal', 0, None),
        ('terminal', 2, Fraction(0)),
        ('terminal', 49, Fraction(0)),
        ('reached', 50, None),
        ('reached', 50, Fraction(0)),
        ('reached', 50, Fraction(1, 2)),
        ('reached', 50, Fraction(1)),
        ('resource_censored', 49, None),
        ('domain_unsupported', 13, None),
        ('not_started', 0, None),
    )


def encoded(value):
    if isinstance(value, Fraction):
        return [value.numerator, value.denominator]
    raise TypeError(type(value).__name__)


def canonical(value):
    return (json.dumps(value, default=encoded, sort_keys=True, separators=(',', ':')) + '\n').encode()


def review(protocol):
    records = fixtures()
    summary = Counter()
    for branches in product(records, repeat=4):
        result = contrast(branches)
        require(result == oracle_contrast(branches), 'orientation interval oracle disagreement')
        summary['quartets'] += 1
        summary['point_progress_quartets'] += result[0][0] == result[0][1]
        summary['point_reach_quartets'] += result[1][0] == result[1][1]
    require(summary['quartets'] == protocol['expected_quartets'], 'quartet denominator')

    terminal_early = records[1]
    reached_half = records[5]
    terminal_pair = (terminal_early,) * 2
    reached_pair = (reached_half,) * 2
    early_vs_reached = contrast(terminal_pair + reached_pair)
    require(early_vs_reached == ((Fraction(-24, 25), Fraction(-24, 25)),
                               (-1, -1), (-1, -1), (-1, -1), (0, 0)),
            'observed early terminal versus horizon')
    late_vs_early = contrast((records[2],) * 2 + terminal_pair)
    require(late_vs_early[0] == (Fraction(47, 50),) * 2
            and late_vs_early[1] == (0, 0), 'progress within terminal outcomes')
    censored = contrast((records[7],) * 2 + reached_pair)
    require(censored[0] == (Fraction(-1, 50), 0) and censored[1] == (-1, 0),
            'censored event-prefix bounds')
    empty = contrast((records[3],) * 2 + (records[4],) * 2)
    require(empty[0] == empty[1] == (0, 0) and empty[2] == (-1, -1),
            'empty versus defined zero distinction')
    invalid = (('reached', 49, None), ('terminal', 50, None),
               ('not_started', 2, None), ('resource_censored', 50, None),
               ('resource_censored', 2, Fraction(0)),
               ('reached', 50, Fraction(2)), ('reached', True, None),
               ('ineligible_parent', 0, None), ('terminal', 2, Fraction(1, 2)))
    for record in invalid:
        try:
            bounds(*record)
        except ValueError:
            continue
        raise ValueError(f'invalid record accepted: {record!r}')
    return dict(
        protocol_id=protocol['protocol_id'],
        synthetic_branch_records=len(records), invalid_records_rejected=len(invalid),
        checks=dict(summary), thresholds=THRESHOLDS,
        ordered_components=['restricted_progress', 'reach_50', 'joint_q_ge_0',
                            'joint_q_ge_half', 'joint_q_ge_1'],
        controls=dict(early_terminal_vs_reached=early_vs_reached,
                      late_vs_early_terminal=late_vs_early,
                      censored_at_49_vs_reached=censored,
                      empty_vs_defined_zero_at_50=empty),
        scientific_status='untested', outcome_design='proposal',
        new_graph_transitions=0, empirical_assay_rows_scored=0,
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output', type=Path)
    mode.add_argument('--verify', type=Path)
    args = parser.parse_args()
    data = (ROOT / 'protocols/r06i.json').read_bytes()
    protocol = json.loads(data)
    for name, digest in protocol['pins_sha256'].items():
        require(sha256((ROOT / name).read_bytes()).hexdigest() == digest, f'pin {name}')
    binding = dict(protocol_sha256=sha256(data).hexdigest())
    if args.output:
        args.output.mkdir(parents=True)
        (args.output / 'started.json').write_bytes(canonical(binding))

    try:
        report = review(protocol) | binding
        receipt = canonical(report)
        if args.verify:
            require(args.verify.read_bytes() == receipt, 'design receipt mismatch')
        else:
            (args.output / 'receipt.json').write_bytes(receipt)
        print(f"Verified {report['checks']['quartets']:,} synthetic orientation quartets.")
    except Exception as exc:
        if args.output:
            (args.output / 'failure.json').write_bytes(canonical(binding | dict(error=str(exc))))
        raise


if __name__ == '__main__':
    main()
