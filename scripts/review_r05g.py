"""Read-only R05g readiness synthesis. Never samples nulls or evolves graphs."""
import argparse
from collections import Counter
from fractions import Fraction
from hashlib import sha256
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from plan_r05d import project, rule_id, rules
from verify_r05d import arithmetic_profiles, independent_rules


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def encoded(value):
    if isinstance(value, Fraction):
        return [value.numerator, value.denominator]
    if isinstance(value, dict):
        return {str(k): encoded(v) for k, v in value.items()}
    if isinstance(value, (list, tuple)):
        return [encoded(v) for v in value]
    return value


def canonical(value):
    return json.dumps(encoded(value), sort_keys=True, separators=(',', ':')).encode('ascii')


def sha(path):
    return sha256(path.read_bytes()).hexdigest()


def public_file(root, name):
    path = Path(name)
    require(not path.is_absolute() and bool(path.parts) and '..' not in path.parts and
            not path.parts[0].startswith('.') and path.parts[0] != 'results' and
            not path.parts[0].startswith('build'), 'nonpublic input path')
    result = root / path
    require(result.resolve().is_relative_to(root.resolve()), 'input escapes repository')
    return result


def check_pins(root, pins):
    for name, expected in pins.items():
        require(sha(public_file(root, name)) == expected, 'source/input digest: ' + name)


def ceiling_status(nodes, edges, threshold):
    require(type(nodes) is int and nodes >= 0 and type(edges) is int and edges >= 0,
            'invalid conditional sizes')
    require(isinstance(threshold, Fraction) and threshold > 0, 'exact positive threshold')
    bound = Fraction(min(edges // 2, nodes * (nodes - 1) // 2), nodes * (nodes - 1) // 2) if nodes > 1 else None
    status = ('undefined_density' if bound is None else 'below_frozen_threshold_upper_bound'
              if bound < threshold else 'not_excluded_by_ceiling')
    return bound, status


def validate_calibration(receipt, design):
    """Validate saved accounting only; do not regenerate or extend null draws."""
    require(receipt['audit_status'] == 'pass' and receipt['scientific_status'] == 'untested' and
            receipt['campaign_authorized'] is False and receipt['promotion_authorized'] is False,
            'calibration is not campaign admission')
    plan = design['calibration_plan']
    graphs = {g['id']: g for g in plan['small_graphs'] + plan['large_graphs']}
    small = {g['id'] for g in plan['small_graphs']}
    expected = {(name, r) for name in graphs for r in range(4)}
    seen, statuses, covered, words = set(), Counter(), 0, 0
    radius = Fraction(*receipt['radius'])
    require(radius == Fraction(2067, 100000), 'calibration-only radius')
    for q in receipt['queries']:
        key = q['graph_id'], q['root_index']
        require(key in expected and key not in seen, 'missing/duplicate calibration identity')
        seen.add(key)
        g, result = graphs[key[0]], q['result']
        require(result['quota'] == 56 and result['samples'] == 16384 and
                result['delta'] == [1, 100] and result['radius'] == receipt['radius'], 'frozen calibration precision')
        require(result['root'] == design['rng']['root_seeds'][key[1]] and
                result['query'] == f'mu/R05f-cal-v1/{key[0]}/root/{key[1]}', 'root/query custody')
        digest = sha256(canonical(dict(schema='mu-g2-null-graph-v1', nodes=g['nodes'],
                                       edges=sorted(g['edges'])))).hexdigest()
        require(result['graph'] == digest, 'graph identity custody')
        hist = {Fraction(v): count for v, count in result['histogram'].items()}
        require(all(0 <= value <= 1 and type(count) is int and count > 0 for value, count in hist.items()) and
                sum(hist.values()) == 16384, 'saved histogram accounting')
        mean = sum((v * c for v, c in hist.items()), Fraction()) / 16384
        interval = [max(Fraction(), mean - radius), min(Fraction(1), mean + radius)]
        require(result['mean'] == encoded(mean) and result['interval'] == encoded(interval), 'saved interval arithmetic')
        status = 'sampled_constant_unresolved' if len(hist) == 1 else 'witnessed_nonconstant'
        require(result['status'] == status, 'sampled degeneracy claim')
        statuses[status] += 1
        require(16384 * max(0, len(g['edges']) - 1) <= result['words'] <= result['word_budget'] ==
                4 * 16384 * max(1, len(g['edges']) - 1), 'RNG word accounting')
        words += result['words']
        if key[0] in small:
            require(q['exact_mean'] is not None, 'missing known mean')
            truth = Fraction(*q['exact_mean'])
            require(interval[0] <= truth <= interval[1] and q['coverage'] is True, 'known-mean coverage')
            covered += 1
        else:
            require(q['exact_mean'] is None and q['coverage'] is None, 'invented large-mean coverage')
    require(seen == expected and covered == 32 and receipt['counts']['null_draws'] == 917504,
            'complete frozen calibration matrix')
    return dict(query_slots=len(seen), known_mean_covered=covered, large_invariants_only=24,
                sample_statuses=dict(statuses), attempted_words=words,
                evidence='saved source-bound receipt accounting; no recalibration',
                campaign_quota=None, campaign_radius=None)


def preflight(root=ROOT):
    protocol = json.loads((root / 'protocols/r05g.json').read_text())
    require(protocol['protocol_id'] == 'R05g-v1' and protocol['world_transitions_authorized'] == 0 and
            protocol['null_samples_authorized'] == 0 and protocol['campaign_authorized'] is False and
            protocol['holdout_authorized'] is False and protocol['promotion_authorized'] is False,
            'read-only review scope')
    check_pins(root, protocol['pins_sha256'])
    # Check current public source/input maps from the named receipts. Do not open
    # custody entries under results/ or replay any experiment merely to review it.
    for name in protocol['receipt_chain']:
        document = json.loads(public_file(root, name).read_text())
        for field in ('source_sha256', 'inputs_sha256', 'prerequisite_sha256', 'pins_sha256'):
            check_pins(root, document.get(field, {}))
    contract = json.loads((root / 'protocols/r02-measurement-contract.json').read_text())
    require(contract['intervention_horizon'] == protocol['horizon'] == 50 and
            Fraction(str(contract['structural_min_effect'])) == Fraction(1, 20) and
            Fraction(str(contract['intervention_min_effect'])) == Fraction(1, 20), 'frozen outcome criteria')
    return protocol


def review(stream=None):
    start = time.monotonic()
    protocol = preflight()
    load = lambda name: json.loads((ROOT / name).read_text())
    design, old_protocol = load('protocols/r05e-observer-design.json'), load('protocols/r05d.json')
    prior_d, prior_e, prior_f = (load(f'reports/r05{s}.json') for s in ('d', 'e', 'f'))
    require(prior_d['feasibility_status'] == 'not_launch_ready' and prior_e['audit_status'] == 'pass', 'prior boundaries')
    calibration = validate_calibration(prior_f, design)
    engineering = load('protocols/r05b.json')['matrix']
    seeds = engineering['seeds'] + engineering['extra_seeds']
    all_rules = list(rules())
    require(all_rules == list(independent_rules()) and len(all_rules) == 969 and
            len(seeds) == len({s['id'] for s in seeds}) == 14, 'full rule/seed panel')
    digest, trace_bytes = sha256(), 0
    classes, availability, ceiling_counts, coverage, motif, density, null_modes = (Counter() for _ in range(7))
    maxima, fresh_bounds = Counter(), []
    for rule_index, rhs in enumerate(all_rules):
        fresh = any(3 in arc for arc in rhs)
        for seed in seeds:
            row = project(rhs, seed, 50, old_protocol)
            oracle = list(arithmetic_profiles(rhs, seed, old_protocol))[-1]
            require(row == oracle, 'independent incremental arithmetic')
            availability[row['availability']] += 1
            p = row['projection']
            record = dict(rule_index=rule_index, rule_sha256=rule_id(rhs), seed_id=seed['id'],
                          fresh_vertex_rule=fresh, rhs_edges=len(rhs), horizon=50,
                          initial=row['initial'], availability=row['availability'],
                          projection=p, observer_domain_fit=None, density_ceiling=None,
                          ceiling_status='not_applicable_unavailable', null_mode=None,
                          observed_endpoint=False, candidate_statistics_evaluated=False)
            if p is not None:
                bound, status = ceiling_status(p['endpoint_nodes'], p['endpoint_edges'], Fraction(1, 20))
                # Independent pair-budget calculation without min/comb formula.
                pairs, remaining, reciprocal = 0, p['endpoint_edges'], 0
                for a in range(p['endpoint_nodes']):
                    for _ in range(a):
                        pairs += 1
                        if remaining >= 2:
                            remaining -= 2
                            reciprocal += 1
                require(bound == (Fraction(reciprocal, pairs) if pairs else None), 'independent density ceiling')
                domain = design['proposed_domain']
                fits = (p['peak_nodes'] <= domain['nodes'] and p['peak_edges'] <= domain['edges'] and
                        p['match_count_upper_bound'] <= domain['matches'])
                mode = ('undefined' if bound is None else 'exact' if p['endpoint_edges'] <= 8 else 'sampled')
                record.update(observer_domain_fit=fits, density_ceiling=bound, ceiling_status=status, null_mode=mode)
                coverage['domain_fit' if fits else 'domain_unsupported'] += 1
                ceiling_counts[status] += 1
                motif[p['motif_coverage']] += 1
                density['initial_defined' if p['initial_density_defined'] else 'initial_undefined'] += 1
                density['endpoint_defined' if p['endpoint_density_defined'] else 'endpoint_undefined'] += 1
                null_modes[mode] += 1
                classes['fresh_conditional' if fresh else 'nonfresh_conditional'] += 1
                if fresh:
                    require(bound is not None and status == 'below_frozen_threshold_upper_bound', 'fresh-rule ceiling')
                    fresh_bounds.append(bound)
                for key in ('peak_nodes', 'peak_edges', 'match_count_upper_bound'):
                    maxima[key] = max(maxima[key], p[key])
            else:
                ceiling_counts[row['availability']] += 1
            data = canonical(record) + b'\n'
            trace_bytes += len(data)
            digest.update(data)
            require(trace_bytes < protocol['budgets']['retained_bytes'] - 1048576, 'review retention budget')
            require(time.monotonic() - start < protocol['budgets']['global_wall_seconds'], 'review deadline')
            if stream is not None:
                stream.write(data)
    require(sum(availability.values()) == 13566 and dict(availability) == prior_d['horizon_summaries'][50]['availability'],
            'full denominator and prior availability')
    require(dict(ceiling_counts) == prior_e['cell_classifications'] and coverage == {'domain_fit': 9520},
            'prior ceilings and newly calibrated size domain')
    require(dict(motif) == prior_d['horizon_summaries'][50]['motif_coverage'], 'motif exclusions retained')
    require(len(fresh_bounds) == 7420 and classes['nonfresh_conditional'] == 2100, 'rule-class accounting')
    old_g1 = load('reports/r04a.json')
    require(old_g1['reserved_jobs'] == 16774 and old_g1['holdout_jobs_executed'] == 0, 'G1 custody boundary')
    preflight()
    return encoded(dict(protocol_id='R05g-v1', audit_status='pass', readiness_status='not_launch_ready',
        decision='close_current_readiness_review_without_launch', scientific_status='untested',
        full_panel_cells=13566, availability=dict(availability), conditional_rule_classes=dict(classes),
        observer_domain=dict(coverage), size_maxima=dict(maxima), cell_classifications=dict(ceiling_counts),
        motif_coverage=dict(motif), density_definedness=dict(density), endpoint_null_modes=dict(null_modes),
        fresh_maximum_density_ceiling=max(fresh_bounds),
        bound_scope='conditional event-50 endpoints; density minus nonnegative degree-null mean; not the paired intervention effect or every possible G2 hypothesis',
        calibration_evidence=calibration, requirements=protocol['requirements'],
        next_boundary=protocol['next_boundary'], source_sha256=protocol['pins_sha256'],
        protocol_sha256=sha(ROOT / 'protocols/r05g.json'), trace_sha256=digest.hexdigest(), trace_bytes=trace_bytes,
        null_samples_executed=0, graph_transitions_executed=0, native_runs=0, trajectory_files_read=0,
        candidate_statistics_evaluated=0, intervention_effects_measured=0, holdout_jobs_executed=0,
        reserved_g1_jobs_unopened_per_prior_receipt=16774, campaign_authorized=False, promotion_authorized=False))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output-directory', type=Path)
    group.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.verify:
        require(review() == json.loads(args.verify.read_text()), 'R05g review receipt mismatch')
        print('R05g read-only receipt verified without null samples, trajectories or native binaries')
        return
    protocol = preflight()
    args.output_directory.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    execution = dict(protocol_id='R05g-v1', audit_status='fail')
    with (args.output_directory / 'started.json').open('x') as f:
        json.dump(dict(protocol_sha256=sha(ROOT / 'protocols/r05g.json')), f)
    try:
        with (args.output_directory / 'cells.jsonl').open('xb') as f:
            result = review(f)
        with (args.output_directory / 'review.json').open('x') as f:
            json.dump(result, f, indent=2, sort_keys=True)
            f.write('\n')
        execution.update(audit_status='pass', receipt_sha256=sha(args.output_directory / 'review.json'),
                         trace_sha256=result['trace_sha256'])
    except Exception as error:
        execution['error'] = f'{type(error).__name__}: {error}'.replace(str(ROOT), '<repo>')
    execution['elapsed_seconds'] = time.monotonic() - start
    execution['retained_bytes_before_receipt'] = sum(p.stat().st_size for p in args.output_directory.iterdir())
    if (execution['elapsed_seconds'] > protocol['budgets']['global_wall_seconds'] or
            execution['retained_bytes_before_receipt'] + 4096 > protocol['budgets']['retained_bytes']):
        execution.update(audit_status='fail', error='final registered review budget exceeded')
    with (args.output_directory / 'execution.json').open('x') as f:
        json.dump(execution, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps(execution, sort_keys=True))
    raise SystemExit(0 if execution['audit_status'] == 'pass' else 1)


if __name__ == '__main__':
    main()
