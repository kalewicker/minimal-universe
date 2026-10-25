"""Source-bound synthetic edge-budget calibration; no scientific world runs."""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction
from hashlib import sha256
from itertools import product
import json
from math import comb, factorial, prod
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis import edge_budget_v1 as observer
from analysis import g2_observer_v1 as primitives
from audit_r05e import oracle_radius
from design_r06a import synthetic_graphs, oracle_scores, unique_orders
from review_r05g import check_pins, encoded, canonical, sha


def require(condition, reason):
    if not condition:
        raise ValueError(reason)


def oracle_score(nodes, edges):
    del nodes
    if not edges:
        return None
    adjacent = {}
    for a, b in edges:
        adjacent.setdefault(a, set()).add(b)
    pairs = {frozenset((a, b)) for a, targets in adjacent.items() for b in targets
             if a != b and a in adjacent.get(b, ())}
    return Fraction(2 * len(pairs), len(edges))


def oracle_null(nodes, edges):
    """Unique endpoint recursion with explicit labelled multiplicity weights."""
    if not edges:
        return dict(status='undefined_empty_graph', distribution={}, mean=None)
    sources, targets = [a for a, _ in edges], [b for _, b in edges]
    weight = prod(factorial(c) for c in Counter(targets).values())
    histogram = Counter()
    for order in unique_orders(targets):
        histogram[oracle_scores(nodes, list(zip(sources, order)))[1]] += weight
    total = factorial(len(edges))
    require(sum(histogram.values()) == total, 'independent labelled mass')
    distribution = {v: Fraction(c, total) for v, c in histogram.items()}
    return dict(status='informative' if len(histogram) > 1 else 'degenerate', distribution=distribution,
                mean=sum((v * p for v, p in distribution.items()), Fraction()))


def independent_draw(root, query, digest, draw, size):
    header = json.dumps(dict(schema='mu-g2-budget-null-word-v1', root=root, query=query,
                             graph=digest, draw=draw), sort_keys=True, separators=(',', ':')).encode('ascii')
    labels, counter = list(range(size)), 0
    i = size - 1
    while i > 0:
        bound = i + 1
        while True:
            word = int.from_bytes(sha256(header + b'\n' + str(counter).encode('ascii')).digest()[:8], 'big')
            counter += 1
            if word >= (1 << 64) % bound:
                j = word % bound
                break
        saved = labels[i]
        labels[i] = labels[j]
        labels[j] = saved
        i -= 1
    return labels, counter


def rare_truth(graph):
    edges = list(map(tuple, graph['edges']))
    require(graph['nodes'] == 2 and Counter(edges) == {(0, 1): 32, (1, 0): 32}, 'rare-support fixture')
    loops = [(a, a) for a, _ in edges]
    require(Counter(b for _, b in loops) == Counter(b for _, b in edges) and
            oracle_score(2, loops) == 0 and oracle_score(2, edges) == Fraction(1, 32), 'rare support witnesses')
    probability = Fraction(factorial(32) ** 2, factorial(64))
    require(probability == Fraction(1, comb(64, 32)), 'rare-support analytic mass')
    return dict(zero_probability=probability, score_support=[Fraction(), Fraction(1, 32)],
                mean=(1 - probability) / 32,
                argument='Balanced stubs force equal off-diagonal counts. Only the all-loop target assignment has zero reciprocal pairs.')


def paired_fixture(name):
    parent = 'mu/G2-budget-cal-v1/' + name
    bucket = int.from_bytes(sha256(parent.encode('utf-8')).digest()[:8], 'big') % 10
    split = ('discovery' if bucket < 4 else 'detector-development' if bucket < 6
             else 'validation' if bucket < 8 else 'final-test')
    branch = dict(parent=parent, partition=split, scheduler='uniform_match', horizon=50, status='reached',
                  score_0=Fraction(), score_h=Fraction(1, 4), matches_0=2, matches_h=2)
    return dict(parent=parent, target=deepcopy(branch), sham=deepcopy(branch))


def paired_checks(names):
    results = {}
    for name in names:
        row = paired_fixture(name)
        rows, rejection = [row], False
        if name == 'zero':
            pass
        elif name == 'immediate_offset':
            row['target'].update(score_0=Fraction(1, 4), score_h=Fraction(1, 2))
        elif name in ('delayed_quarter', 'eligibility_change'):
            row['target']['score_h'] = Fraction(1, 2)
            if name == 'eligibility_change':
                row['sham'].update(matches_0=1, matches_h=0)
        elif name == 'negative':
            row['target']['score_h'] = Fraction()
        elif name in ('terminal', 'censored', 'unsupported', 'mixed_incomplete'):
            row['target'].update(status={'censored': 'resource_censored', 'unsupported': 'domain_unsupported'}.get(
                name, 'terminal_before_horizon'), score_h=None, matches_h=None)
            if name == 'mixed_incomplete':
                rows.append(paired_fixture('complete-other'))
        elif name in ('undefined_initial', 'undefined_endpoint'):
            row['target']['score_0' if name == 'undefined_initial' else 'score_h'] = None
        elif name == 'aliased_loops':
            for branch in (row['target'], row['sham']):
                branch.update(score_0=observer.score(1, [(0, 0)] * 2), score_h=Fraction())
        else:
            rejection = True
            if name == 'parent_mismatch':
                row['target']['parent'] += '/child'
            elif name == 'split_mismatch':
                row['target']['partition'] = 'invalid'
            elif name == 'horizon_mismatch':
                row['target']['horizon'] = 49
            elif name == 'scheduler_mismatch':
                row['sham']['scheduler'] = 'lex_first'
            elif name == 'duplicate_parent':
                rows.append(deepcopy(row))
            elif name == 'invalid_score':
                row['target']['score_h'] = True
            elif name == 'unknown_status':
                row['target']['status'] = 'unknown'
            elif name == 'invented_endpoint':
                row['target']['status'] = 'resource_censored'
            elif name == 'missing_match_count':
                row['target']['matches_h'] = None
            elif name == 'missing_field':
                del row['target']['horizon']
            elif name == 'wrong_namespace':
                row['parent'] = 'production/unregistered'
            else:
                raise ValueError('unregistered paired fixture')
        try:
            actual = observer.paired_bookkeeping(rows, 50)
        except ValueError:
            require(rejection, 'unexpected paired rejection: ' + name)
            results[name] = dict(status='rejected_as_registered')
            continue
        require(not rejection, 'invalid pair accepted: ' + name)
        expected = []
        for item in rows:
            t, s = item['target'], item['sham']
            values = [t['score_0'], t['score_h'], s['score_0'], s['score_h']]
            unavailable = t['status'] != 'reached' or s['status'] != 'reached' or None in values
            expected.append(None if unavailable else values[1] - values[0] - (values[3] - values[2]))
        mean = None if None in expected else sum(expected, Fraction()) / len(expected)
        require(actual['mean_effect'] == mean and [p['effect'] for p in actual['pairs']] == expected and
                actual['total_pairs'] == len(rows) and actual['complete_pairs'] == sum(v is not None for v in expected),
                'independent paired arithmetic and denominators')
        require(actual['sham_validity'] == 'not_established' and not actual['scientific_acceptance'] and
                not actual['production_metric_adopted'], 'paired scope')
        if name == 'eligibility_change':
            require(actual['pairs'][0]['initial_eligibility_changed'] and
                    actual['pairs'][0]['endpoint_eligibility_changed'], 'hidden eligibility change')
        results[name] = actual
    return results


def preflight():
    protocol = json.loads((ROOT / 'protocols/r06b.json').read_text())
    require(protocol['protocol_id'] == 'R06b-v1' and protocol['calibration_authorized'] and
            not protocol['campaign_authorized'] and not protocol['holdout_authorized'] and
            not protocol['production_metric_adopted'], 'R06b scope')
    check_pins(ROOT, protocol['pins_sha256'])
    for name in protocol['receipt_chain']:
        previous = json.loads((ROOT / name).read_text())
        for field in ('source_sha256', 'inputs_sha256', 'prerequisite_sha256', 'pins_sha256'):
            check_pins(ROOT, previous.get(field, {}))
    prior = json.loads((ROOT / 'reports/r06a.json').read_text())
    require(prior['audit_status'] == 'pass' and prior['recommend_for_next_calibration'] == ['edge_budget'] and
            prior['scientific_effect_threshold'] is None and prior['production_metric_adopted'] is False, 'R06a admission')
    design = json.loads((ROOT / 'protocols/r06b-calibration-design.json').read_text())
    require(design['metric'] == observer.METRIC and design['word_schema'] == observer.WORD_SCHEMA and
            design['samples'] == observer.SAMPLES == primitives.SAMPLES == 16384 and
            observer.DELTA == primitives.DELTA == Fraction(*design['family_delta']) == Fraction(1, 100) and
            observer.GRID == primitives.GRID == design['grid'] == 1000000, 'fixed implementation/precision')
    require(design['quota'] == 892 and design['exact_control_slots'] == 816 and design['matrix_slots'] == 76,
            'all planned exact/undefined/sampled query slots')
    return protocol, design


def calibrate(stream=None):
    start = time.monotonic()
    protocol, design = preflight()
    digest, trace_bytes = sha256(), 0

    def emit(row):
        nonlocal trace_bytes
        data = canonical(row) + b'\n'
        digest.update(data)
        trace_bytes += len(data)
        require(trace_bytes <= protocol['budgets']['retained_bytes'] - 1048576, 'retention budget')
        require(time.monotonic() - start <= protocol['budgets']['global_wall_seconds'], 'global deadline')
        if stream is not None:
            stream.write(data)

    counts, statuses, seen_queries = Counter(), Counter(), set()
    for size in range(9):
        seen = set()
        for choices in product(*(range(i + 1) for i in range(size - 1, 0, -1))):
            iterator = iter(choices)
            labels = tuple(primitives.shuffle(size, lambda bound: next(iterator)))
            require(set(labels) == set(range(size)) and labels not in seen, 'shuffle bijection')
            seen.add(labels)
            counts['choice_vectors'] += 1
            emit(dict(kind='shuffle_bijection', size=size, choices=choices, labels=labels))
        require(len(seen) == factorial(size), 'missing labelled permutation')
    old_design = json.loads((ROOT / 'protocols/r06a-observable-design.json').read_text())
    for graph in synthetic_graphs(old_design):
        n, edges = graph['nodes'], list(map(tuple, graph['edges']))
        value = observer.score(n, edges)
        require(value == oracle_scores(n, edges)[1] == oracle_score(n, edges), 'independent raw budget score')
        counts['raw_control_graphs'] += 1
        if len(edges) <= 8:
            query = 'mu/R06b-cal-v1/exact/' + graph['id']
            seen_queries.add(query)
            actual = observer.degree_null(n, edges, root='0' * 64, query=query, quota=design['quota'])
            expected = oracle_null(n, edges)
            require(actual['mode'] == 'exact' and actual['words'] == 0 and
                    all(actual[k] == expected[k] for k in ('status', 'distribution', 'mean')), 'exact null/default dispatch')
            counts['exact_control_slots'] += 1
            statuses[actual['status']] += 1
            emit(dict(kind='exact_control', graph=graph, result=actual, oracle=expected))
        else:
            emit(dict(kind='raw_only_control', graph=graph, score=value))
    paired = paired_checks(design['paired_cases'])
    emit(dict(kind='paired_controls', results=paired))
    radius = oracle_radius(16384, design['quota'], Fraction(1, 100), 1000000)[1]
    require(primitives.radius(design['quota']) == radius, 'independent radius certificate')
    queries = []
    rare = rare_truth(next(g for g in design['large_graphs'] if g['id'] == 'rare_support2x64'))
    for graph in design['small_graphs'] + design['large_graphs']:
        n, edges = graph['nodes'], sorted(map(tuple, graph['edges']))
        small = len(edges) <= 8
        truth = oracle_null(n, edges)['mean'] if small else rare['mean'] if graph['id'] == 'rare_support2x64' else None
        source, target = [a for a, _ in edges], [b for _, b in edges]
        source_counts, target_counts = Counter(source), Counter(target)
        graph_digest = sha256(json.dumps(dict(schema='mu-g2-null-graph-v1', nodes=n, edges=edges),
                              sort_keys=True, separators=(',', ':')).encode('ascii')).hexdigest()
        for root_index, root in enumerate(design['roots']):
            query = f'mu/R06b-cal-v1/matrix/{graph["id"]}/root/{root_index}'
            require(query not in seen_queries, 'duplicate query slot')
            seen_queries.add(query)
            emit(dict(kind='query_start', query=query, graph=graph, graph_sha256=graph_digest,
                      root=root, quota=design['quota'], samples=16384, known_mean=truth))
            histogram, attempted = Counter(), 0

            def check_draw(draw, labels, value, words):
                nonlocal attempted
                replay, replay_words = independent_draw(root, query, graph_digest, draw, len(edges))
                require(labels == replay and words == replay_words, 'independent full RNG/permutation replay')
                shuffled = list(zip(source, (target[i] for i in labels)))
                require(Counter(a for a, _ in shuffled) == source_counts and Counter(b for _, b in shuffled) == target_counts
                        and len(shuffled) == len(edges), 'degree and occurrence conservation')
                require(value == oracle_score(n, shuffled), 'independent per-draw budget score')
                histogram[value] += 1
                attempted += words
                counts['sampled_draws'] += 1
                permutation = bytes(labels)
                emit(dict(kind='draw', draw=draw, permutation=permutation.hex(),
                          permutation_sha256=sha256(permutation).hexdigest(), score=value, words=words))

            result = observer.degree_null(n, edges, root=root, query=query, quota=design['quota'],
                                           calibration_force_sample=small, on_draw=check_draw)
            emit(dict(kind='query_end', result=result))
            counts['matrix_slots'] += 1
            require(result['graph'] == graph_digest and result['quota'] == design['quota'], 'query graph/quota custody')
            covered = None
            if not edges:
                require(result['status'] == 'undefined_empty_graph' and result['mean'] is None and
                        result['interval'] is None and result['words'] == 0 and not histogram, 'empty query was sampled or imputed')
                counts['undefined_matrix_slots'] += 1
            else:
                require(result.get('samples') == 16384 and sum(histogram.values()) == 16384 and
                        result['histogram'] == histogram and result['words'] == attempted, 'incomplete query/accounting; no retry')
                mean = sum((v * c for v, c in histogram.items()), Fraction()) / 16384
                interval = [max(Fraction(), mean - radius), min(Fraction(1), mean + radius)]
                expected_status = 'sampled_constant_unresolved' if len(histogram) == 1 else 'witnessed_nonconstant'
                require(result['mean'] == mean and result['interval'] == interval and result['status'] == expected_status and
                        result['contrast_interval'] == [oracle_score(n, edges) - interval[1], oracle_score(n, edges) - interval[0]],
                        'rational interval, contrast or status mismatch')
                counts['sampled_matrix_slots'] += 1
                if truth is not None:
                    covered = interval[0] <= truth <= interval[1]
                    require(covered, 'consumed known-mean coverage failure; no new seed or precision change')
                    counts['small_mean_covered' if small else 'analytic_large_mean_covered'] += 1
                else:
                    counts['large_invariant_slots'] += 1
            queries.append(dict(graph_id=graph['id'], root_index=root_index, result=result, known_mean=truth, coverage=covered))
            print(f'completed {len(queries)}/76 matrix slots; {counts["sampled_draws"]} draws', flush=True)
    require(dict(counts) == protocol['expected'] and len(seen_queries) == design['quota'], 'full registered matrix/quota counts')
    preflight()
    return encoded(dict(protocol_id='R06b-v1', metric=observer.METRIC, audit_status='pass', scientific_status='untested',
        counts=dict(counts), exact_control_statuses=dict(statuses), quota=design['quota'], radius=radius, queries=queries,
        rare_support=rare, paired_controls=paired, source_sha256=protocol['pins_sha256'],
        protocol_sha256=sha(ROOT / 'protocols/r06b.json'), trace_sha256=digest.hexdigest(), trace_bytes=trace_bytes,
        production_metric_adopted=False, scientific_effect_threshold=None, campaign_authorized=False,
        graph_transitions_executed=0, native_runs=0, trajectory_files_read=0, holdout_jobs_executed=0,
        g2_rule_or_seed_panels_scored=0, scientific_candidate_statistics_evaluated=0,
        next_boundary=protocol['next_boundary']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output-directory', type=Path)
    group.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.verify:
        require(calibrate() == json.loads(args.verify.read_text()), 'R06b receipt replay mismatch')
        print('R06b receipt independently replayed without retained artifacts or native binaries')
        return
    protocol, _ = preflight()
    args.output_directory.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    execution = dict(protocol_id='R06b-v1', audit_status='fail')
    with (args.output_directory / 'started.json').open('x') as f:
        json.dump(dict(protocol_sha256=sha(ROOT / 'protocols/r06b.json')), f)
    try:
        with (args.output_directory / 'calibration.jsonl').open('xb') as f:
            result = calibrate(f)
        with (args.output_directory / 'calibration.json').open('x') as f:
            json.dump(result, f, indent=2, sort_keys=True)
            f.write('\n')
        execution.update(audit_status='pass', receipt_sha256=sha(args.output_directory / 'calibration.json'),
                         trace_sha256=result['trace_sha256'])
    except Exception as error:
        execution['error'] = f'{type(error).__name__}: {error}'.replace(str(ROOT), '<repo>')
    execution['elapsed_seconds'] = time.monotonic() - start
    execution['retained_bytes_before_receipt'] = sum(p.stat().st_size for p in args.output_directory.iterdir())
    if (execution['elapsed_seconds'] > protocol['budgets']['global_wall_seconds'] or
            execution['retained_bytes_before_receipt'] + 4096 > protocol['budgets']['retained_bytes']):
        execution.update(audit_status='fail', error='final registered calibration budget exceeded')
    with (args.output_directory / 'execution.json').open('x') as f:
        json.dump(execution, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps(execution, sort_keys=True))
    raise SystemExit(0 if execution['audit_status'] == 'pass' else 1)


if __name__ == '__main__':
    main()
