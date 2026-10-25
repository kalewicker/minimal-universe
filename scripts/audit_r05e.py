"""Static long-horizon observer design audit. No null sampling or world execution."""
import argparse
from collections import Counter
from fractions import Fraction
import hashlib
from itertools import permutations, product
import json
from math import comb, factorial, isqrt
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audit_r04 import require
from plan_r05d import project, rule_id, rules
from verify_r05d import preflight as preflight_r05d


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value):
    if isinstance(value, Fraction):
        return [value.numerator, value.denominator]
    if isinstance(value, dict):
        return {str(key): encoded(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [encoded(item) for item in value]
    return value


def canonical(value):
    return json.dumps(encoded(value), sort_keys=True, separators=(',', ':'))


def certified_radius(draws, quota, delta=Fraction(1, 100), grid=1000000):
    if any(type(v) is not int or v <= 0 for v in (draws, quota, grid)) or not isinstance(delta, Fraction) or not 0 < delta < 1:
        raise ValueError('invalid precision parameters')
    ratio = 2 * quota / delta
    ceiling = (ratio.numerator + ratio.denominator - 1) // ratio.denominator
    level = (ceiling - 1).bit_length()
    square = Fraction(level * grid * grid, 2 * draws)
    units = isqrt(square.numerator // square.denominator)
    if units * units * square.denominator < square.numerator:
        units += 1
    return level, Fraction(units, grid)


def oracle_radius(draws, quota, delta, grid):
    level, bound = 0, Fraction(1)
    while bound < Fraction(2 * quota) / delta:
        level, bound = level + 1, bound * 2
    target_square = Fraction(level, 2 * draws)
    low, high = 0, 1
    while Fraction(high, grid) ** 2 < target_square:
        high *= 2
    while low < high:
        middle = (low + high) // 2
        if Fraction(middle, grid) ** 2 >= target_square:
            high = middle
        else:
            low = middle + 1
    return level, Fraction(low, grid)


def density_ceiling(nodes, edges):
    if type(nodes) is not int or type(edges) is not int or nodes < 0 or edges < 0:
        raise ValueError('invalid size projection')
    if nodes < 2:
        return None
    pairs = comb(nodes, 2)
    return Fraction(min(edges // 2, pairs), pairs)


def independent_ceiling(nodes, edges):
    if nodes < 2:
        return None
    available = edges
    reciprocal_pairs, vertex_pairs = 0, 0
    for first in range(nodes):
        for _ in range(first):
            vertex_pairs += 1
            if available >= 2:
                available -= 2
                reciprocal_pairs += 1
    return Fraction(reciprocal_pairs, vertex_pairs)


def shuffle_choices(length, choices):
    if type(length) is not int or not 0 <= length <= 8 or len(choices) != max(0, length - 1):
        raise ValueError('invalid exact shuffle control')
    values = list(range(length))
    for index, selected in zip(range(length - 1, 0, -1), choices):
        if type(selected) is not int or not 0 <= selected <= index:
            raise ValueError('invalid shuffle choice')
        values[index], values[selected] = values[selected], values[index]
    return tuple(values)


def count_only_endpoint(rhs, seed, horizon):
    edges = seed['edges']
    eligible = any(i != j and a[1] == b[0] for i, a in enumerate(edges) for j, b in enumerate(edges))
    if horizon and not eligible:
        return None
    nodes, count = seed['nodes'], len(edges)
    growth = int(3 in {endpoint for arc in rhs for endpoint in arc})
    for _ in range(horizon):
        if count < 2:
            return None
        nodes += growth
        count = count - 2 + len(rhs)
    return nodes, count


def preflight(protocol):
    require(protocol['protocol_id'] == 'R05e-v1' and protocol['calibration_executed'] is False and
            protocol['campaign_authorized'] is False and protocol['holdout_authorized'] is False,
            'R05e static scope')
    for name, value in protocol['inputs_sha256'].items():
        require(sha(ROOT / name) == value, 'input digest: ' + name)
    prior = json.loads((ROOT / 'reports/r05d.json').read_text())
    require(prior['audit_status'] == 'pass' and prior['feasibility_status'] == 'not_launch_ready', 'R05d boundary')
    for name, value in prior['source_sha256'].items():
        require(sha(ROOT / name) == value, 'R05d source: ' + name)
    r05d = json.loads((ROOT / 'protocols/r05d.json').read_text())
    seeds = preflight_r05d(r05d)
    design = json.loads((ROOT / 'protocols/r05e-observer-design.json').read_text())
    require(design['status'] == 'registered_design_not_implementation_or_launch' and
            design['calibration_plan']['execution_authorized'] is False, 'design admission')
    require(design['proposed_domain'] == dict(nodes=64, edges=64, matches=4032, successful_event_horizon=50), 'proposed domain')
    require(design['family_failure_budget'] == [1, 100] and design['sample_count'] == 16384 and
            design['mean_interval']['grid'] == 1000000, 'frozen precision design')
    contract = json.loads((ROOT / 'protocols/r02-measurement-contract.json').read_text())
    require(contract['intervention_horizon'] == 50 and Fraction(str(contract['structural_min_effect'])) == Fraction(1, 20),
            'frozen numerical gates')
    return design, r05d, seeds


def audit(stream=None):
    start = time.monotonic()
    protocol = json.loads((ROOT / 'protocols/r05e.json').read_text())
    design, r05d, seeds = preflight(protocol)
    sources = ('protocols/r05e.json', 'protocols/r05e-observer-design.json', 'scripts/audit_r05e.py',
               'tests/test_r05e.py', 'docs/r05e-long-observer.md')
    source_hashes = {name: sha(ROOT / name) for name in sources}
    digest, trace_bytes, counts = hashlib.sha256(), 0, Counter()

    def emit(row):
        nonlocal trace_bytes
        data = (canonical(row) + '\n').encode()
        digest.update(data)
        trace_bytes += len(data)
        require(trace_bytes <= protocol['budgets']['retained_bytes'] - 131072, 'trace byte budget')
        require(time.monotonic() - start <= protocol['budgets']['global_wall_seconds'], 'static audit deadline')
        if stream:
            stream.write(data)

    permutation_counts = {}
    for length in range(9):
        seen = set()
        for choices in product(*(range(index + 1) for index in range(length - 1, 0, -1))):
            outcome = shuffle_choices(length, choices)
            require(outcome not in seen, 'shuffle control is not injective')
            seen.add(outcome)
            counts['shuffle_choice_vectors'] += 1
            emit(dict(kind='labelled_shuffle', length=length, choices=choices, permutation=outcome))
        require(seen == set(permutations(range(length))) and len(seen) == factorial(length), 'shuffle permutation census')
        permutation_counts[str(length)] = len(seen)
    require(counts['shuffle_choice_vectors'] == protocol['expected_shuffle_choice_vectors'] == 46234, 'shuffle count')

    precision = []
    delta = Fraction(*design['family_failure_budget'])
    target = Fraction(*design['precision_audit']['target_radius'])
    grid = design['mean_interval']['grid']
    for draws in design['precision_audit']['sample_counts']:
        for quota in design['precision_audit']['family_quotas']:
            level, radius = certified_radius(draws, quota, delta, grid)
            require((level, radius) == oracle_radius(draws, quota, delta, grid), 'precision oracle')
            sufficient = Fraction(level, 2) / (target * target)
            required_draws = (sufficient.numerator + sufficient.denominator - 1) // sufficient.denominator
            require(certified_radius(required_draws, quota, delta, grid)[1] <= target, 'precision target bound')
            row = dict(draws=draws, quota=quota, family_delta=delta, dyadic_level=level,
                       radius=radius, sufficient_draws_for_target_radius=required_draws, target_radius=target)
            precision.append(row)
            counts['precision_rows'] += 1
            emit(dict(kind='precision', **row))
    require(counts['precision_rows'] == protocol['expected_precision_rows'] == 9, 'precision count')

    cell_status, bounds = Counter(), Counter()
    threshold = Fraction(1, 20)
    domain = design['proposed_domain']
    for rhs in rules():
        identity = rule_id(rhs)
        for seed in seeds:
            counts['rule_seed_cells'] += 1
            original = project(rhs, seed, 50, r05d)
            independent = count_only_endpoint(rhs, seed, 50)
            projection = original['projection']
            if projection is None:
                require(independent is None, 'unavailable arithmetic mismatch')
                row = dict(rule=identity, seed=seed['id'], availability=original['availability'],
                           proposed_domain_fit=None, reciprocal_density_ceiling=None,
                           structural_contrast_status='not_applicable_unavailable')
                cell_status[original['availability']] += 1
            else:
                nodes, edges = projection['endpoint_nodes'], projection['endpoint_edges']
                require(independent == (nodes, edges), 'endpoint arithmetic mismatch')
                fit = (projection['peak_nodes'] <= domain['nodes'] and projection['peak_edges'] <= domain['edges'] and
                       projection['match_count_upper_bound'] <= domain['matches'])
                counts['conditional_cells'] += 1
                counts['proposed_domain_compatible'] += fit
                ceiling = density_ceiling(nodes, edges)
                require(ceiling == independent_ceiling(nodes, edges), 'reciprocal-pair budget ceiling')
                status = ('undefined_density' if ceiling is None else
                          'below_frozen_threshold_upper_bound' if ceiling < threshold else 'not_excluded_by_ceiling')
                cell_status[status] += 1
                if any(3 in arc for arc in rhs):
                    bounds['fresh_conditional_cells'] += 1
                    bounds['fresh_cells_below_ceiling'] += status == 'below_frozen_threshold_upper_bound'
                row = dict(rule=identity, seed=seed['id'], availability=original['availability'],
                           endpoint_nodes=nodes, endpoint_edges=edges, proposed_domain_fit=fit,
                           reciprocal_density_ceiling=ceiling, structural_contrast_status=status)
            emit(dict(kind='conditional_effect_ceiling', horizon=50, **row))
    require(counts['rule_seed_cells'] == protocol['expected_rule_seed_cells'] == 13566, 'full panel count')
    prior_horizon = json.loads((ROOT / 'reports/r05d.json').read_text())['horizon_summaries'][50]
    require(counts['conditional_cells'] == prior_horizon['projections'] and
            counts['proposed_domain_compatible'] == counts['conditional_cells'] and
            sum(cell_status.values()) == 13566, 'proposed coverage and full-panel accounting')

    calibration = design['calibration_plan']
    fixtures = calibration['small_graphs'] + calibration['large_graphs']
    require(len(fixtures) == len({g['id'] for g in fixtures}) == 14 and
            len(design['rng']['root_seeds']) == len(set(design['rng']['root_seeds'])) == 4, 'future fixture identities')
    for graph in fixtures:
        require(graph['nodes'] <= domain['nodes'] and len(graph['edges']) <= domain['edges'] and
                all(0 <= a < graph['nodes'] and 0 <= b < graph['nodes'] for a, b in graph['edges']), 'future fixture domain')
    require(len(fixtures) * 4 == calibration['expected_query_slots'] == 56 and
            56 * design['sample_count'] == calibration['expected_null_draws'] == 917504, 'future draw accounting')
    require(len(calibration['small_graphs']) * 4 == calibration['small_query_slots'] == 32 and
            len(calibration['large_graphs']) * 4 == calibration['large_query_slots'] == 24 and
            all(len(root) == 64 and all(c in '0123456789abcdef' for c in root)
                for root in design['rng']['root_seeds']), 'calibration strata and root keys')
    require(sum(9 ** i for i in range(4)) == 820, 'exact-score control census')

    # Static support witnesses for the rare-support fixture, not random null samples.
    rare = next(g for g in fixtures if g['id'] == 'rare_support2x64')
    source_counts = Counter(a for a, _ in rare['edges'])
    target_counts = Counter(b for _, b in rare['edges'])
    loop_witness = [(a, a) for a, _ in rare['edges']]
    require(source_counts == Counter(a for a, _ in loop_witness) and
            target_counts == Counter(b for _, b in loop_witness), 'rare support degree witness')
    require(set(rare['edges']) == {(0, 1), (1, 0)} and set(loop_witness) == {(0, 0), (1, 1)}, 'rare support score witness')
    rare_support = dict(nodes=2, edges=64, witnessed_scores=[0, 1],
                        zero_score_probability=Fraction(1, comb(64, 32)),
                        consequence='A finite constant sample cannot certify degeneracy.')
    level, radius = certified_radius(16384, 56, delta, grid)
    future_work = dict(query_slots=56, null_score_evaluations=917504,
                       maximum_swaps_per_query=16384 * 63,
                       maximum_word_attempts_per_query=4 * 16384 * 63,
                       calibration_radius=radius, calibration_dyadic_level=level,
                       samples_executed_here=0, runtime_status='not_measured')
    require(all(sha(ROOT / name) == value for name, value in source_hashes.items()), 'source changed')
    return encoded(dict(protocol_id='R05e-v1', audit_status='pass', design_status='not_implemented_or_calibrated',
                        scientific_status='untested', counts=dict(counts), cell_classifications=dict(cell_status),
                        effect_ceiling_summary=dict(bounds), frozen_minimum_structural_effect=threshold,
                        contrast_scope=design['structural_contrast_scope'], labelled_permutation_counts=permutation_counts,
                        precision_table=precision, rare_support_control=rare_support, future_calibration_work=future_work,
                        source_sha256=source_hashes, inputs_sha256=protocol['inputs_sha256'],
                        trace_sha256=digest.hexdigest(), trace_bytes=trace_bytes,
                        null_samples_executed=0, native_runs=0, graph_transitions_executed=0,
                        holdout_jobs_executed=0, campaign_authorized=False, promotion_authorized=False))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output-directory', type=Path)
    group.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.verify:
        require(audit() == json.loads(args.verify.read_text()), 'R05e receipt mismatch')
        print('R05e static observer-design receipt verified without writing artifacts')
    else:
        args.output_directory.mkdir(parents=True, exist_ok=False)
        start = time.monotonic()
        execution = dict(protocol_id='R05e-v1', audit_status='fail')
        with (args.output_directory / 'started.json').open('x') as stream:
            json.dump(dict(protocol_sha256=sha(ROOT / 'protocols/r05e.json')), stream)
        try:
            with (args.output_directory / 'design-checks.jsonl').open('xb') as stream:
                result = audit(stream)
            with (args.output_directory / 'design.json').open('x') as stream:
                json.dump(result, stream, indent=2, sort_keys=True)
                stream.write('\n')
            execution.update(audit_status='pass', design_sha256=sha(args.output_directory / 'design.json'),
                             trace_sha256=sha(args.output_directory / 'design-checks.jsonl'))
            protocol = json.loads((ROOT / 'protocols/r05e.json').read_text())
            require(sum(p.stat().st_size for p in args.output_directory.iterdir() if p.is_file()) + 131072 <=
                    protocol['budgets']['retained_bytes'], 'final retained byte budget')
        except Exception as error:
            execution['audit_status'] = 'fail'
            execution['error'] = f'{type(error).__name__}: {error}'.replace(str(ROOT), '<repo>')
        execution['elapsed_seconds'] = time.monotonic() - start
        execution['retained_bytes_before_receipt'] = sum(p.stat().st_size for p in args.output_directory.iterdir() if p.is_file())
        with (args.output_directory / 'execution.json').open('x') as stream:
            json.dump(execution, stream, indent=2, sort_keys=True)
            stream.write('\n')
        print(canonical(execution))
        raise SystemExit(0 if execution['audit_status'] == 'pass' else 1)
