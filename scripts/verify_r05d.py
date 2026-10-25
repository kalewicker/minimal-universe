"""Independent static G2 feasibility audit, without graph execution."""
import argparse
from collections import Counter
import hashlib
from itertools import product
import json
from math import factorial
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audit_r04 import require
from audit_r05 import audit as audit_r05
from plan_r05d import project, rule_id, rules


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def independent_rules():
    arcs = [(a, b) for a in range(4) for b in range(4)]
    for length in range(4):
        for ordered in product(arcs, repeat=length):
            if all(ordered[i] <= ordered[i + 1] for i in range(length - 1)):
                yield ordered


def arithmetic_profiles(rhs, seed, protocol):
    """Iterate only integer size counters, never consume edges or substitute an RHS."""
    arcs = seed['edges']
    count = sum(i != j and a[1] == b[0] for i, a in enumerate(arcs) for j, b in enumerate(arcs))
    initial = dict(nodes=seed['nodes'], edges=len(arcs), matches=count,
                   density_defined=seed['nodes'] > 1,
                   motif_coverage_complete=all(arcs.count(arc) <= 2 for arc in arcs))
    growth = int(any(endpoint == 3 for arc in rhs for endpoint in arc))
    output_count = len(rhs)
    # Independently derive the count-only event ceiling by exhausting hypothetical counts.
    ceiling = None
    if not count:
        ceiling = 0
    elif output_count < 2:
        remaining, ceiling = len(arcs), 0
        while remaining >= 2:
            remaining = remaining - 2 + output_count
            ceiling += 1
    vertices, edges = seed['nodes'], len(arcs)
    peak_v, peak_e = vertices, edges
    histories = 1
    for horizon in protocol['horizons']:
        if horizon == 0:
            availability = 'initial_state'
        elif not count:
            availability = 'provably_unavailable_no_initial_match'
        elif ceiling is not None and horizon > ceiling:
            availability = 'provably_unavailable_edge_budget'
        else:
            availability = 'not_established_by_static_sizes'
        result = dict(availability=availability, successful_event_upper_bound=ceiling,
                      initial=initial, projection=None)
        if not availability.startswith('provably_unavailable'):
            kernel, observer, measurement = (protocol[key] for key in
                                           ('kernel_domain', 'observer_domain', 'g2_measurement_domain'))
            pair_bound = sum(2 * i for i in range(peak_e))  # Two roles per unordered occurrence pair.
            local = peak_v <= measurement['nodes'] and peak_e <= measurement['edges'] and pair_bound <= measurement['matches']
            exact = local and horizon <= measurement['exact_horizon']
            motif = ('known_incomplete_at_initial_state' if not initial['motif_coverage_complete'] else
                     'guaranteed_complete' if horizon == 0 or peak_e < 3 else 'not_guaranteed_by_sizes')
            # Sum 1-, 2- and 3-subset counts using integer products, independent of comb().
            subsets = peak_v + peak_v * (peak_v - 1) // 2 + peak_v * (peak_v - 1) * (peak_v - 2) // 6
            nodes_fit = peak_v <= observer['nodes']
            null_fit = peak_e <= observer['null_edges']
            result['projection'] = dict(endpoint_nodes=vertices, endpoint_edges=edges,
                peak_nodes=peak_v, peak_edges=peak_e, match_count_upper_bound=pair_bound,
                kernel_count_caps_fit=(horizon <= kernel['events'] and peak_v <= kernel['nodes'] and peak_e <= kernel['edges']),
                kernel_match_cap_guaranteed=pair_bound <= kernel['matches'],
                observer_node_domain=nodes_fit, degree_null_edge_domain=null_fit,
                local_exposure_domain=local,
                exact_survival_domain=('guaranteed_by_count_bound' if histories <= measurement['frontier_states']
                                       else 'frontier_not_guaranteed') if exact else 'outside_size_or_horizon_domain',
                frontier_history_upper_bound=histories if exact else None,
                initial_density_defined=initial['density_defined'], endpoint_density_defined=vertices >= 2,
                motif_coverage=motif, null_informativeness='not_established',
                motif_subset_work_upper_bound=subsets,
                raw_null_permutation_work_upper_bound=(horizon + 1) * factorial(peak_e) if nodes_fit and null_fit else None)
        yield result
        # Stop incrementing counters at the necessary ceiling; later views are unavailable.
        if horizon < max(protocol['horizons']) and (ceiling is None or horizon < ceiling):
            histories *= count if horizon == 0 else max(0, edges * (edges - 1))
            vertices += growth
            edges += output_count - 2
            peak_v = max(peak_v, vertices)
            peak_e = max(peak_e, edges)


METRICS = ('kernel_count_caps_fit', 'kernel_match_cap_guaranteed', 'observer_node_domain',
           'degree_null_edge_domain', 'local_exposure_domain', 'initial_density_defined', 'endpoint_density_defined')


def preflight(protocol):
    require(protocol['protocol_id'] == 'R05d-v1' and not protocol['campaign_authorized'] and
            not protocol['holdout_authorized'] and not protocol['promotion_authorized'], 'static scope')
    require(protocol['horizons'] == list(range(51)) and protocol['ledger_horizons'] == [0, 3, 50], 'registered horizons')
    for name, value in protocol['inputs_sha256'].items():
        require(sha(ROOT / name) == value, 'input digest: ' + name)
    calibration = json.loads((ROOT / 'reports/r05c.json').read_text())
    require(calibration['audit_status'] == 'pass', 'R05c status')
    for name, value in calibration['source_sha256'].items():
        require(sha(ROOT / name) == value, 'R05c source: ' + name)
    prior = [json.loads((ROOT / name).read_text()) for name in
             ('reports/r05b-release.json', 'reports/r05b-sanitize.json')]
    require(prior[0]['audit_status'] == prior[1]['audit_status'] == 'pass' and
            prior[0]['outcome'] == prior[1]['outcome'], 'R05b receipts')
    for receipt in prior:
        for name, value in receipt['source_sha256'].items():
            require(sha(ROOT / name) == value, 'R05b source: ' + name)
    require(audit_r05() == json.loads((ROOT / 'reports/r05a.json').read_text()), 'earlier receipt chain')
    engineering = json.loads((ROOT / 'protocols/r05b.json').read_text())
    require(protocol['kernel_domain'] == {key: engineering['hard_reference_limits'][key]
            for key in ('events', 'nodes', 'edges', 'matches')}, 'kernel domain')
    r05c = json.loads((ROOT / 'protocols/r05c.json').read_text())['measurement_domain']
    require(protocol['g2_measurement_domain'] == dict(nodes=r05c['max_nodes'], edges=r05c['max_edges'],
            matches=r05c['max_matches'], exact_horizon=r05c['max_horizon'], frontier_states=r05c['max_frontier_states']),
            'G2 measurement domain')
    r02 = json.loads((ROOT / 'protocols/r02-measurement-contract.json').read_text())
    require(protocol['required_intervention_horizon'] == r02['intervention_horizon'] == 50, 'frozen intervention horizon')
    require(protocol['observer_domain'] == dict(nodes=64, null_edges=8, motif_nodes=3, motif_arc_multiplicity=2), 'observer domain')
    return engineering['matrix']['seeds'] + engineering['matrix']['extra_seeds']


def audit(stream=None):
    start = time.monotonic()
    protocol = json.loads((ROOT / 'protocols/r05d.json').read_text())
    seeds = preflight(protocol)
    all_rules = list(rules())
    require(all_rules == list(independent_rules()) and len(all_rules) == protocol['expected_rules'] == 969, 'grammar census')
    require(len(seeds) == len({seed['id'] for seed in seeds}) == protocol['expected_seeds'] == 14, 'seed census')
    sources = ('protocols/r05d.json', 'scripts/plan_r05d.py', 'scripts/verify_r05d.py',
               'tests/test_r05d.py', 'docs/r05d-feasibility.md')
    source_hashes = {name: sha(ROOT / name) for name in sources}
    counts = Counter()
    summaries = [dict(horizon=h, cells=0, availability=Counter(), projections=0,
                      checks={key: Counter() for key in METRICS}, exact_survival=Counter(), motif_coverage=Counter())
                 for h in protocol['horizons']]
    digest, trace_bytes = hashlib.sha256(), 0
    for rule_index, rhs in enumerate(all_rules):
        identity = rule_id(rhs)
        for seed in seeds:
            counts['cells'] += 1
            for horizon, expected in enumerate(arithmetic_profiles(rhs, seed, protocol)):
                row = project(rhs, seed, horizon, protocol)
                require(row == expected, f'arithmetic mismatch: {rule_index}/{seed["id"]}/{horizon}')
                counts['size_views'] += 1
                summary = summaries[horizon]
                summary['cells'] += 1
                summary['availability'][row['availability']] += 1
                projected = row['projection']
                if projected is not None:
                    summary['projections'] += 1
                    for key in METRICS:
                        summary['checks'][key]['within' if projected[key] else 'outside_or_not_guaranteed'] += 1
                    summary['exact_survival'][projected['exact_survival_domain']] += 1
                    summary['motif_coverage'][projected['motif_coverage']] += 1
                if horizon in protocol['ledger_horizons']:
                    data = (canonical(dict(rule_index=rule_index, rule_sha256=identity, rhs=rhs,
                                           seed_id=seed['id'], horizon=horizon, **row)) + '\n').encode()
                    digest.update(data)
                    trace_bytes += len(data)
                    require(trace_bytes <= protocol['budgets']['retained_bytes'] - 65536, 'trace byte budget')
                    if stream:
                        stream.write(data)
                    counts['ledger_rows'] += 1
            require(time.monotonic() - start <= protocol['budgets']['global_wall_seconds'], 'global static deadline')
    require(counts == dict(cells=protocol['expected_cells'], size_views=protocol['expected_size_views'],
                           ledger_rows=protocol['expected_ledger_rows']), 'registered matrix count')
    common = {}
    for key in METRICS:
        accepted = [s['horizon'] for s in summaries
                    if s['checks'][key].get('within', 0) == s['projections']]
        common[key] = max(accepted) if accepted else None
    accepted = [s['horizon'] for s in summaries if
                s['exact_survival'].get('guaranteed_by_count_bound', 0) == s['projections']]
    common['exact_survival_domain'] = max(accepted) if accepted else None
    require(all(sha(ROOT / name) == value for name, value in source_hashes.items()), 'source changed')
    return dict(protocol_id=protocol['protocol_id'], audit_status='pass', scientific_status='untested',
                feasibility_status='not_launch_ready', required_intervention_horizon=50,
                counts=dict(counts), horizon_summaries=summaries, common_reviewed_horizon=common,
                seeds=seeds, trace_sha256=digest.hexdigest(), trace_bytes=trace_bytes,
                source_sha256=source_hashes, inputs_sha256=protocol['inputs_sha256'],
                unestablished_requirements=['future match eligibility and reached endpoints',
                    'informative nulls and motif completeness', 'valid target/sham construction and coupling',
                    'registered parent namespace, replication, split coverage and power',
                    'frozen test families, estimators and resampling RNG', 'measured throughput and output budgets'],
                world_transitions_executed=0, native_runs=0, trajectory_files_read=0,
                holdout_jobs_executed=0, campaign_authorized=False, promotion_authorized=False)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output-directory', type=Path)
    group.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.verify:
        require(audit() == json.loads(args.verify.read_text()), 'R05d receipt mismatch')
        print('R05d static feasibility receipt verified without writing artifacts')
    else:
        args.output_directory.mkdir(parents=True, exist_ok=False)
        start = time.monotonic()
        execution = dict(protocol_id='R05d-v1', audit_status='fail')
        with (args.output_directory / 'started.json').open('x') as stream:
            json.dump(dict(protocol_sha256=sha(ROOT / 'protocols/r05d.json')), stream)
        try:
            with (args.output_directory / 'cells.jsonl').open('xb') as stream:
                result = audit(stream)
            with (args.output_directory / 'feasibility.json').open('x') as stream:
                json.dump(result, stream, indent=2, sort_keys=True)
                stream.write('\n')
            execution.update(audit_status='pass', feasibility_sha256=sha(args.output_directory / 'feasibility.json'),
                             trace_sha256=sha(args.output_directory / 'cells.jsonl'))
        except Exception as error:
            execution['error'] = f'{type(error).__name__}: {error}'.replace(str(ROOT), '<repo>')
        execution['elapsed_seconds'] = time.monotonic() - start
        execution['retained_bytes_before_receipt'] = sum(p.stat().st_size for p in args.output_directory.iterdir() if p.is_file())
        with (args.output_directory / 'execution.json').open('x') as stream:
            json.dump(execution, stream, indent=2, sort_keys=True)
            stream.write('\n')
        print(canonical(execution))
        raise SystemExit(0 if execution['audit_status'] == 'pass' else 1)
