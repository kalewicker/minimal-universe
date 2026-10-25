"""Source-bound synthetic R05f calibration; no world runs or holdout reads."""
import argparse
from collections import Counter
from fractions import Fraction
from hashlib import sha256
from itertools import permutations, product
import json
from math import factorial
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis import g2_observer_v1 as observer
from analysis import g2_measurements as legacy
from analysis.measurements import degree_null as r02_null
from audit_r05e import preflight as r05e_preflight, oracle_radius, rare_support_witness
from calibrate_r05c import fixtures, subsets, oracle_exposure, paired_checks, paired_fixture


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def sha(path):
    return sha256(path.read_bytes()).hexdigest()


def encoded(value):
    if isinstance(value, Fraction):
        return [value.numerator, value.denominator]
    if isinstance(value, dict):
        return {str(k): encoded(v) for k, v in value.items()}
    if isinstance(value, (tuple, list)):
        return [encoded(v) for v in value]
    return value


def canonical(value):
    return json.dumps(encoded(value), sort_keys=True, separators=(',', ':')).encode('ascii')


def independent_score(nodes, arcs):
    if nodes < 2:
        return None
    adjacent = set(arcs)
    reciprocals = {frozenset((u, v)) for u, v in adjacent if u != v and (v, u) in adjacent}
    return Fraction(len(reciprocals), nodes * (nodes - 1) // 2)


def independent_draw(root, query, digest, draw, size):
    """Direct SHA concatenation and separate RNG/rejection implementation."""
    header = json.dumps({'schema': 'mu-g2-null-word-v1', 'root': root, 'query': query,
                         'graph': digest, 'draw': draw}, sort_keys=True, separators=(',', ':')).encode('ascii')
    counter = 0
    order = list(range(size))
    position = size - 1
    while position > 0:
        bound = position + 1
        cutoff = (1 << 64) % bound
        while True:
            raw = sha256(header + b'\n' + str(counter).encode('ascii')).digest()
            word = int.from_bytes(raw[0:8], byteorder='big')
            counter += 1
            if word >= cutoff:
                selected = word % bound
                break
        saved = order[position]
        order[position] = order[selected]
        order[selected] = saved
        position -= 1
    return order, counter


def endpoint_controls():
    base = dict(nodes=2, edges=[(0, 0, 1), (1, 1, 0)], parent_ids=[0, 1], targets=[0],
                parent_event=7, event=57, horizon=50)
    cases = {}
    cases['intact'] = observer.observed_endpoint(**base)
    require(cases['intact']['observed_untouched'] is True, 'intact identity')
    for name, ids in [('recreated', [2, 3]), ('lost', [1])]:
        arcs = [(identity, i % 2, (i + 1) % 2) for i, identity in enumerate(ids)]
        cases[name] = observer.observed_endpoint(**dict(base, edges=arcs))
        require(cases[name]['observed_untouched'] is False and
                cases[name]['local']['status'] == 'target_already_consumed', 'lost target status')
    for status in ('terminal_before_horizon', 'resource_censored', 'domain_unsupported', 'undefined'):
        cases[status] = observer.observed_endpoint(**dict(base, nodes=None, edges=None, event=10, status=status))
        require(cases[status]['observed_untouched'] is None and cases[status]['local'] is None,
                'unavailable endpoint padded')
    cases['no_match'] = observer.observed_endpoint(**dict(base, edges=[(0, 0, 1)]))
    require(cases['no_match']['local']['probability_avoid'] is None, 'empty eligibility')
    cases['deterministic'] = observer.observed_endpoint(**dict(base, scheduler='lex_first'))
    require(cases['deterministic']['local']['probability_avoid'] is None and
            cases['deterministic']['local']['matches'] == 2, 'scheduler probability claim')
    # Existing arithmetic supports long horizons without executing a trajectory.
    pairs = [paired_fixture('r05f-complete'), paired_fixture('r05f-unavailable')]
    for row in pairs:
        for name in ('target', 'sham'):
            row[name]['horizon'] = 50
    pairs[1]['target'].update(status='resource_censored', density_h=None, matches_h=None)
    cases['paired_50'] = legacy.paired_bookkeeping(pairs, 50)
    require(cases['paired_50']['mean_effect'] is None and cases['paired_50']['total_pairs'] == 2 and
            cases['paired_50']['complete_pairs'] == 1, 'incomplete parent denominator')
    return cases


def controls(emit):
    counts = Counter()
    for size in range(9):
        seen = set()
        for choices in product(*(range(i + 1) for i in range(size - 1, 0, -1))):
            it = iter(choices)
            order = tuple(observer.shuffle(size, lambda bound: next(it)))
            require(set(order) == set(range(size)) and order not in seen, 'labelled permutation bijection')
            seen.add(order)
            counts['choice_vectors'] += 1
            emit(dict(kind='bijection', size=size, choices=choices, order=order))
        require(len(seen) == factorial(size), 'missing labelled permutation')
    arcs = list(product(range(3), repeat=2))
    for size in range(4):
        for edges in product(arcs, repeat=size):
            exact = observer.exact_null(3, edges)
            old = r02_null(3, edges)
            require(exact['status'] == old['status'] and exact['distribution'] == old['distribution'], 'R02 exact null')
            dispatched = observer.degree_null(3, edges, root='0' * 64, query='exact-control', quota=56)
            require(dispatched == dict(exact, quota=56, mode='exact'), 'exact fallback dispatch')
            require(observer.score(3, edges) == independent_score(3, edges), 'exact score oracle')
            counts['exact_score_controls'] += 1
            emit(dict(kind='exact_null', edges=edges, result=exact))
    for nodes, edges in fixtures([0, 1, 2, 3, 4]):
        for targets in subsets(edges):
            actual = observer.exposure(nodes, edges, targets)
            require(actual == legacy.exposure(nodes, edges, targets) == oracle_exposure(nodes, edges, targets),
                    'legacy exposure regression')
            counts['legacy_exposure_controls'] += 1
    for nodes, edges in [(1, [(i, 0, 0) for i in range(64)]),
                         (64, [(i, i, (i + 1) % 64) for i in range(64)]),
                         (64, [(i, 0, i + 1) for i in range(63)])]:
        for targets in ([], [0], [0, 1], [e[0] for e in edges]):
            actual = observer.exposure(nodes, edges, targets)
            require(actual == oracle_exposure(nodes, edges, targets), 'large exposure direct pairs')
            counts['large_exposure_controls'] += 1
            emit(dict(kind='large_exposure', nodes=nodes, edges=edges, targets=targets, result=actual))
    endpoint = endpoint_controls()
    emit(dict(kind='endpoint_controls', cases=endpoint))
    return dict(counts), endpoint


def preflight():
    protocol = json.loads((ROOT / 'protocols/r05f.json').read_text())
    require(protocol['protocol_id'] == 'R05f-v1' and protocol['calibration_authorized'] is True and
            protocol['campaign_authorized'] is False and protocol['holdout_authorized'] is False and
            protocol['promotion_authorized'] is False, 'R05f scope')
    for name, digest in protocol['pins_sha256'].items():
        require(sha(ROOT / name) == digest, 'source/input digest: ' + name)
    r05e_preflight(json.loads((ROOT / 'protocols/r05e.json').read_text()))
    prior = json.loads((ROOT / 'reports/r05e.json').read_text())
    require(prior['audit_status'] == 'pass', 'R05e admission')
    for name, digest in prior['source_sha256'].items():
        require(sha(ROOT / name) == digest, 'R05e source: ' + name)
    design = json.loads((ROOT / 'protocols/r05e-observer-design.json').read_text())
    require(protocol['query_id_format'] == 'mu/R05f-cal-v1/{graph_id}/root/{root_index}', 'query identity format')
    require(protocol['budgets'] == design['calibration_plan']['future_budget'], 'unchanged budgets')
    return protocol, design


def calibrate(stream=None):
    start = time.monotonic()
    protocol, design = preflight()
    trace = sha256()
    trace_bytes = 0

    def emit(row):
        nonlocal trace_bytes
        data = canonical(row) + b'\n'
        trace.update(data)
        trace_bytes += len(data)
        require(trace_bytes <= protocol['budgets']['retained_bytes'] - 1048576, 'retention budget')
        require(time.monotonic() - start <= protocol['budgets']['global_wall_seconds'], 'global wall budget')
        if stream is not None:
            stream.write(data)

    counts, endpoints = controls(emit)
    plan = design['calibration_plan']
    for name, expected in [('choice_vectors', 46234), ('exact_score_controls', 820),
                           ('legacy_exposure_controls', 10239), ('large_exposure_controls', 12)]:
        require(counts[name] == expected, 'control count: ' + name)
    require(observer.SAMPLES == 16384 and observer.DELTA == Fraction(1, 100) and observer.GRID == 1000000,
            'frozen sampling precision')
    r = oracle_radius(16384, 56, Fraction(1, 100), 1000000)[1]
    require(observer.radius(56) == r, 'independent radius certificate')
    queries, small_covered, draws = [], 0, 0
    graphs = plan['small_graphs'] + plan['large_graphs']
    roots = design['rng']['root_seeds']
    for index, g in enumerate(graphs):
        n = g['nodes']
        edges = sorted(map(tuple, g['edges']))
        sources, targets = [e[0] for e in edges], [e[1] for e in edges]
        source_counts, target_counts = Counter(sources), Counter(targets)
        digest = sha256(json.dumps(dict(schema='mu-g2-null-graph-v1', nodes=n, edges=edges),
                                  sort_keys=True, separators=(',', ':')).encode('ascii')).hexdigest()
        require(digest == observer.graph_digest(n, edges), 'graph identity independent encoding')
        small = index < len(plan['small_graphs'])
        truth = r02_null(n, edges) if small else None
        exact_mean = sum((v * p for v, p in truth['distribution'].items()), Fraction()) if small else None
        for root_index, root in enumerate(roots):
            query = protocol['query_id_format'].format(graph_id=g['id'], root_index=root_index)
            emit(dict(kind='query_start', query=query, graph=g, graph_sha256=digest, root=root,
                      samples=16384, quota=56, exact_mean=exact_mean))
            histogram = Counter()
            attempted = 0

            def check_draw(draw, order, value, words):
                nonlocal attempted, draws
                replay, replay_words = independent_draw(root, query, digest, draw, len(edges))
                require(order == replay and words == replay_words, 'independent full draw/RNG replay')
                shuffled = list(zip(sources, (targets[i] for i in order)))
                require(len(shuffled) == len(edges) and Counter(u for u, _ in shuffled) == source_counts and
                        Counter(v for _, v in shuffled) == target_counts, 'stub degree invariance')
                require(value == independent_score(n, shuffled), 'independent per-draw score')
                histogram[value] += 1
                attempted += words
                draws += 1
                permutation = bytes(order)
                emit(dict(kind='draw', draw=draw, permutation=permutation.hex(),
                          permutation_sha256=sha256(permutation).hexdigest(), score=value, words=words))

            result = observer.degree_null(n, edges, root=root, query=query, quota=56,
                                          calibration_force_sample=small, on_draw=check_draw)
            emit(dict(kind='query_end', result=result))
            require(result.get('samples') == 16384 and sum(histogram.values()) == 16384,
                    'incomplete query; no retry')
            require(result['words'] == attempted and result['histogram'] == histogram, 'query accounting')
            mean = sum((v * c for v, c in histogram.items()), Fraction()) / 16384
            interval = [max(Fraction(), mean - r), min(Fraction(1), mean + r)]
            require(result['mean'] == mean and result['interval'] == interval, 'independent mean and interval')
            expected_status = 'witnessed_nonconstant' if len(histogram) > 1 else 'sampled_constant_unresolved'
            require(result['status'] == expected_status, 'sampled degeneracy claim')
            require(result['contrast_interval'] == [independent_score(n, edges) - interval[1],
                                                    independent_score(n, edges) - interval[0]], 'contrast interval')
            covered = interval[0] <= exact_mean <= interval[1] if small else None
            queries.append(dict(graph_id=g['id'], root_index=root_index, result=result,
                                exact_mean=exact_mean, coverage=covered))
            if small:
                require(covered, 'consumed known-mean coverage failure; stop without seed replacement')
                small_covered += 1
            print(f'completed {len(queries)}/56 queries; {draws} draws', flush=True)
    require(len(queries) == 56 and small_covered == 32 and draws == 917504, 'full frozen matrix count')
    rare = rare_support_witness(next(g for g in graphs if g['id'] == 'rare_support2x64'))
    paired = paired_checks(json.loads((ROOT / 'protocols/r05c.json').read_text())['paired_cases'])
    emit(dict(kind='paired_regression', results=paired))
    preflight()  # All source pins and prerequisite boundaries still intact.
    return encoded(dict(protocol_id='R05f-v1', audit_status='pass', counts=dict(counts, queries=56,
                        small_covered=small_covered, large_invariants_only=24, null_draws=draws),
                        radius=r, queries=queries, rare_support=rare, endpoint_controls=endpoints,
                        trace_sha256=trace.hexdigest(), trace_bytes=trace_bytes,
                        source_sha256=protocol['pins_sha256'], protocol_sha256=sha(ROOT / 'protocols/r05f.json'),
                        scientific_status='untested', native_world_runs=0, holdout_jobs_executed=0,
                        promotion_authorized=False, campaign_authorized=False,
                        geometric_ceiling_preserved=True, preserved_intervention_horizon=50))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output-directory', type=Path)
    group.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.verify:
        require(calibrate() == json.loads(args.verify.read_text()), 'R05f replay receipt mismatch')
        print('R05f receipt independently replayed; no artifacts written')
        return
    args.output_directory.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    execution = dict(protocol_id='R05f-v1', audit_status='fail')
    with (args.output_directory / 'started.json').open('x') as f:
        json.dump(dict(protocol_sha256=sha(ROOT / 'protocols/r05f.json')), f)
    try:
        with (args.output_directory / 'draws.jsonl').open('xb') as stream:
            result = calibrate(stream)
        with (args.output_directory / 'calibration.json').open('x') as f:
            json.dump(result, f, sort_keys=True, indent=2)
            f.write('\n')
        execution.update(audit_status='pass', receipt_sha256=sha(args.output_directory / 'calibration.json'),
                         trace_sha256=result['trace_sha256'])
    except Exception as error:
        execution['error'] = f'{type(error).__name__}: {error}'.replace(str(ROOT), '<repo>')
    execution['elapsed_seconds'] = time.monotonic() - start
    execution['retained_bytes_before_receipt'] = sum(p.stat().st_size for p in args.output_directory.iterdir())
    if (execution['elapsed_seconds'] > 600 or execution['retained_bytes_before_receipt'] + 4096 > 536870912):
        execution.update(audit_status='fail', error='final registered budget exceeded')
    with (args.output_directory / 'execution.json').open('x') as f:
        json.dump(execution, f, sort_keys=True, indent=2)
        f.write('\n')
    print(json.dumps(execution, sort_keys=True))
    raise SystemExit(0 if execution['audit_status'] == 'pass' else 1)


if __name__ == '__main__':
    main()
