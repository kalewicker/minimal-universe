"""Read public receipts to close R04 eligibility; never execute a world."""
import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def evaluate(contract, design, launch, run, analysis):
    require(analysis['audit_status'] == 'pass', 'independent audit did not pass')
    require(run['execution_status'] == analysis['execution_status'] == 'complete',
            'execution incomplete')
    for record in (launch, run, analysis):
        require(record['scientific_status'] == 'descriptive_only', 'scope changed')
        require(record['downstream_authorized'] is False, 'downstream scope changed')
        require(record['protocol_id'] == 'R03b-launch-v1', 'unexpected protocol')
    require(launch['holdout_authorized'] is False, 'holdout scope changed')
    require(type(analysis['candidate_promotions']) is int and
            analysis['candidate_promotions'] == 0, 'unexpected candidate promotion')
    n, reserved = launch['expected_discovery_jobs'], launch['expected_reserved_jobs']
    require(run['counts'] == {'complete': n, 'reserved': reserved}, 'run accounting')
    counts = analysis['counts']
    require(counts['completed_jobs'] == n and counts['reserved'] == reserved,
            'analysis accounting')
    require(n + reserved == launch['expected_jobs'], 'registry accounting')
    require(analysis['completed_rule_seed_cells'] == launch['expected_discovery_cells'],
            'cell accounting')
    for key in ('manifest_sha256', 'ledger_sha256', 'seal_sha256'):
        require(run[key] == analysis[key], 'receipt mismatch: ' + key)
    require(run['manifest_sha256'] == launch['manifest_sha256'], 'manifest mismatch')
    horizon = contract['intervention_horizon']
    observed = max(design['snapshots'])
    require(design['snapshots'] == launch['snapshots'] and
            observed == launch['graph_limits']['events'] == design['limits']['events'],
            'observation horizon mismatch')
    require(horizon == design['preserved_intervention_horizon'] == 50 and
            observed < horizon, 'horizon changed; separate review required')
    return {
        'audit_status': 'pass',
        'decision': 'close_conditional_validation_without_launch',
        'eligible_candidates': [],
        'candidate_statistics_evaluated': 0,
        'candidate_effect_status': 'not_evaluated',
        'intervention_status': 'not_executed',
        'registered_observation_horizon': observed,
        'required_intervention_horizon': horizon,
        'discovery_jobs_completed': n,
        'reserved_jobs': reserved,
        'new_world_events': 0,
        'holdout_jobs_executed': 0,
        'holdout_authorized': False,
        'scientific_status': 'no_new_inference',
        'reasons': ['descriptive_registration_prohibits_promotion',
                    'no_promoted_candidates_in_audited_receipt',
                    'intervention_endpoint_not_measured'],
        'claim_limit': 'No eligible candidates from this registration; not evidence that all rules fail or that effects are zero.',
    }


def audit(root=ROOT):
    protocol = json.loads((root / 'protocols/r04a.json').read_text())
    require(protocol['protocol_id'] == 'R04a-v1', 'unexpected audit protocol')
    inputs = {}
    for name, expected in protocol['inputs_sha256'].items():
        require(digest(root / name) == expected, 'input digest mismatch: ' + name)
        inputs[name] = json.loads((root / name).read_text())
    seal = inputs['protocols/r03b-seal.json']
    for name, expected in seal['source_sha256'].items():
        require(digest(root / name) == expected, 'sealed source mismatch: ' + name)
    analysis = inputs['reports/r03b-analysis.json']
    require(analysis['seal_sha256'] == digest(root / 'protocols/r03b-seal.json'),
            'seal identity mismatch')
    custody = inputs['reports/r03b-custody.json']
    public_files = {name: entry for name, entry in custody['files'].items()
                    if not name.startswith('results/')}
    for name, entry in public_files.items():
        require(digest(root / name) == entry['sha256'] and
                (root / name).stat().st_size == entry['bytes'], 'public custody: ' + name)
    result = evaluate(*(inputs[name] for name in (
        'protocols/r02-measurement-contract.json', 'protocols/r03b-design.json',
        'protocols/r03b-launch.json', 'reports/r03b-run.json',
        'reports/r03b-analysis.json')))
    result.update(protocol_id=protocol['protocol_id'],
                  inputs_sha256=protocol['inputs_sha256'],
                  source_sha256={name: digest(root / name) for name in
                                 ('protocols/r04a.json', 'scripts/audit_r04.py',
                                  'tests/test_audit_r04.py')},
                  evidence_scope='Public receipt and source consistency only; bulk trajectories and native binary were not reopened.')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output', type=Path)
    group.add_argument('--verify', type=Path)
    args = parser.parse_args()
    result = audit()
    if args.verify:
        require(json.loads(args.verify.read_text()) == result, 'audit receipt mismatch')
        print('R04a receipt verified')
    else:
        with args.output.open('x') as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write('\n')
        print('R04a complete: no eligible candidates; no validation launched')
