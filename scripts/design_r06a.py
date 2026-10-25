"""R06a analytical observable review on synthetic graphs, not a production observer."""
import argparse
from collections import Counter
from fractions import Fraction
from hashlib import sha256
from itertools import combinations_with_replacement, permutations, product
import json
from math import comb, factorial, prod
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis.measurements import reciprocal_density
from review_r05g import check_pins, encoded, canonical, sha

METRICS = ('pair_density', 'edge_budget', 'support_fraction', 'occurrence_fraction')


def require(condition, message):
    if not condition:
        raise ValueError(message)


def scores(nodes, edges):
    """Reference design formulas only; empty denominators remain undefined."""
    edges = tuple(tuple(e) for e in edges)
    require(type(nodes) is int and 0 <= nodes <= 64 and len(edges) <= 64 and
            all(len(e) == 2 and all(type(v) is int and 0 <= v < nodes for v in e) for e in edges),
            'synthetic graph domain')
    counts = Counter(edges)
    nonloop = {arc for arc in counts if arc[0] != arc[1]}
    supported = {arc for arc in nonloop if arc[::-1] in nonloop}
    reciprocal = len(supported) // 2
    occurrences = sum(counts[arc] for arc in nonloop)
    return (Fraction(reciprocal, comb(nodes, 2)) if nodes >= 2 else None,
            Fraction(2 * reciprocal, len(edges)) if edges else None,
            Fraction(2 * reciprocal, len(nonloop)) if nonloop else None,
            Fraction(sum(counts[arc] for arc in supported), occurrences) if occurrences else None)


def oracle_scores(nodes, edges):
    """Separate multiplicity matrix and vertex-pair counting implementation."""
    matrix = [[0] * nodes for _ in range(nodes)]
    for a, b in edges:
        matrix[a][b] += 1
    pairs = support = nonloop = reverse_occurrences = reciprocal = 0
    total = sum(map(sum, matrix))
    for a in range(nodes):
        for b in range(nodes):
            if a < b:
                pairs += 1
                reciprocal += bool(matrix[a][b] and matrix[b][a])
            if a != b:
                support += bool(matrix[a][b])
                nonloop += matrix[a][b]
                if matrix[b][a]:
                    reverse_occurrences += matrix[a][b]
    return (Fraction(reciprocal, pairs) if pairs else None,
            Fraction(reciprocal * 2, total) if total else None,
            Fraction(reciprocal * 2, support) if support else None,
            Fraction(reverse_occurrences, nonloop) if nonloop else None)


def unique_orders(values):
    """Unique endpoint sequences from multiplicities, without label permutations."""
    counts = Counter(values)
    prefix = []

    def visit():
        if len(prefix) == len(values):
            yield tuple(prefix)
        else:
            for value in sorted(counts):
                if counts[value]:
                    counts[value] -= 1
                    prefix.append(value)
                    yield from visit()
                    prefix.pop()
                    counts[value] += 1
    yield from visit()


def summarize(histogram, observed):
    total = sum(histogram.values())
    undefined = histogram.get(None, 0)
    mean = (None if undefined else
            sum((value * count for value, count in histogram.items()), Fraction()) / total)
    status = ('observed_undefined' if observed is None else 'null_contains_undefined' if undefined else
              'degenerate' if len(histogram) == 1 else 'informative')
    return dict(status=status, mean=mean, undefined_mass=Fraction(undefined, total),
                contrast=observed - mean if observed is not None and mean is not None else None,
                distribution=[dict(score=value, count=histogram[value], probability=Fraction(histogram[value], total))
                              for value in sorted(histogram, key=lambda v: (v is not None, v or Fraction()))])


def exact_nulls(nodes, edges, emit=None, identity='unit'):
    require(len(edges) <= 8, 'exact design controls exceed eight edges')
    observed = scores(nodes, edges)
    sources, targets = [a for a, _ in edges], [b for _, b in edges]
    histograms = [Counter() for _ in METRICS]
    for order in permutations(range(len(edges))):
        shuffled = list(zip(sources, (targets[i] for i in order)))
        actual, expected = scores(nodes, shuffled), oracle_scores(nodes, shuffled)
        if emit is not None:
            emit(dict(kind='labelled_null_permutation', graph=identity, labels=order,
                      scores=actual, oracle_scores=expected))
        require(actual == expected, 'independent per-permutation formulas')
        require(Counter(a for a, _ in shuffled) == Counter(sources) and
                Counter(b for _, b in shuffled) == Counter(targets), 'degree preservation')
        for histogram, value in zip(histograms, actual):
            histogram[value] += 1
    independent = [Counter() for _ in METRICS]
    weight = prod(factorial(c) for c in Counter(targets).values())
    for order in unique_orders(targets):
        for histogram, value in zip(independent, oracle_scores(nodes, list(zip(sources, order)))):
            histogram[value] += weight
    require(histograms == independent and all(sum(h.values()) == factorial(len(edges)) for h in histograms),
            'labelled-stub versus unique-endpoint mass accounting')
    return {name: summarize(histogram, value) for name, histogram, value in zip(METRICS, histograms, observed)}


def synthetic_graphs(design):
    yield dict(id='exhaustive/0/0/0', nodes=0, edges=[], family='exhaustive')
    for nodes in (1, 2, 3):
        for length in range(5):
            for index, edges in enumerate(combinations_with_replacement(tuple(product(range(nodes), repeat=2)), length)):
                yield dict(id=f'exhaustive/{nodes}/{length}/{index}', nodes=nodes, edges=edges, family='exhaustive')
    for graph in design['named_graphs']:
        yield dict(graph, family='named')
    for copies in design['scaling']['reciprocal_copies']:
        edges = [(2 * i + a, 2 * i + b) for i in range(copies) for a, b in ((0, 1), (1, 0))]
        yield dict(id=f'copies/{copies}', nodes=2 * copies, edges=edges, family='copies')
    for nodes in design['scaling']['isolate_nodes']:
        yield dict(id=f'isolates/{nodes}', nodes=nodes, edges=[(0, 1), (1, 0)], family='isolates')
    for multiplicity in design['scaling']['parallel_multiplicities']:
        yield dict(id=f'parallels/{multiplicity}', nodes=2,
                   edges=[(0, 1), (1, 0)] * multiplicity, family='parallels')
    for loops in design['scaling']['added_loops']:
        yield dict(id=f'loops/{loops}', nodes=2, edges=[(0, 1), (1, 0)] + [(0, 0)] * loops, family='loops')


def paired_change(values):
    require(len(values) == 4 and all(v is None or type(v) in (int, Fraction) and 0 <= v <= 1 for v in values),
            'invalid supplied endpoint scores')
    return None if any(v is None for v in values) else Fraction(values[1]) - values[0] - values[3] + values[2]


def parent_mean(effects):
    require(bool(effects), 'empty parent denominator')
    return None if any(v is None for v in effects) else sum(effects, Fraction()) / len(effects)


def preflight(root=ROOT):
    protocol = json.loads((root / 'protocols/r06a.json').read_text())
    require(protocol['protocol_id'] == 'R06a-v1' and protocol['world_transitions_authorized'] == 0 and
            protocol['random_null_draws_authorized'] == 0 and protocol['production_metric_adopted'] is False and
            protocol['campaign_authorized'] is False and protocol['holdout_authorized'] is False,
            'analytical design scope')
    check_pins(root, protocol['pins_sha256'])
    for name in protocol['receipt_chain']:
        old = json.loads((root / name).read_text())
        for field in ('source_sha256', 'inputs_sha256', 'prerequisite_sha256', 'pins_sha256'):
            check_pins(root, old.get(field, {}))
    design = json.loads((root / 'protocols/r06a-observable-design.json').read_text())
    require(design['metric_order'] == list(METRICS) and design['production_status'] == 'analytical_candidates_only' and
            design['scientific_effect_threshold'] is None and design['promotion_authorized'] is False,
            'no silent threshold transfer or adoption')
    return protocol, design


def audit(stream=None):
    start = time.monotonic()
    protocol, design = preflight()
    digest, trace_bytes, counts = sha256(), 0, Counter()

    def emit(row):
        nonlocal trace_bytes
        data = canonical(row) + b'\n'
        digest.update(data)
        trace_bytes += len(data)
        require(trace_bytes <= protocol['budgets']['retained_bytes'] - 1048576, 'retention budget')
        require(time.monotonic() - start <= protocol['budgets']['global_wall_seconds'], 'design deadline')
        if stream is not None:
            stream.write(data)

    by_id, families = {}, {name: [] for name in ('isolates', 'copies', 'parallels', 'loops')}
    criteria = {name: dict(bounded=True, defined_nonempty=True, total_nonempty_exact_null=True)
                for name in METRICS}
    statuses = {name: Counter() for name in METRICS}
    for graph in synthetic_graphs(design):
        identity, nodes, edges = graph['id'], graph['nodes'], graph['edges']
        require(identity not in by_id, 'duplicate synthetic identity')
        actual, expected = scores(nodes, edges), oracle_scores(nodes, edges)
        emit(dict(kind='synthetic_graph', graph=graph, scores=actual, oracle_scores=expected))
        require(actual == expected and actual[0] == reciprocal_density(nodes, edges), 'raw formula/legacy agreement')
        # Reversing vertex labels is a fixed bijection, not a new fixture search.
        renamed = [(nodes - 1 - a, nodes - 1 - b) for a, b in edges]
        require(scores(nodes, renamed) == actual, 'vertex relabel invariance')
        null = exact_nulls(nodes, edges, emit, identity) if len(edges) <= 8 else None
        counts['graphs'] += 1
        counts['exhaustive_graphs' if graph['family'] == 'exhaustive' else 'named_or_scaling_graphs'] += 1
        counts['exact_null_graphs' if null is not None else 'raw_only_graphs'] += 1
        if null is not None:
            counts['labelled_null_permutations'] += factorial(len(edges))
            counts['exact_metric_null_summaries'] += len(METRICS)
        for name, value in zip(METRICS, actual):
            criteria[name]['bounded'] &= value is None or 0 <= value <= 1
            if edges:
                criteria[name]['defined_nonempty'] &= value is not None
                if null is not None:
                    criteria[name]['total_nonempty_exact_null'] &= value is not None and null[name]['undefined_mass'] == 0
            if null is not None:
                statuses[name][null[name]['status']] += 1
        result = dict(graph=graph, scores=dict(zip(METRICS, actual)), exact_null=null)
        by_id[identity] = result
        if graph['family'] in families:
            families[graph['family']].append(result)
        emit(dict(kind='graph_result', **result))
    require(dict(counts) == protocol['expected'], 'frozen graph/null matrix count')
    for name in METRICS:
        for family, criterion in (('isolates', 'isolate_invariant'), ('copies', 'reciprocal_copy_invariant')):
            values = [row['scores'][name] for row in families[family]]
            criteria[name][criterion] = all(v is not None and v == values[0] for v in values)
    # Prespecified named witnesses make failure to admit a null explicit.
    positive, negative = by_id['reciprocal2'], by_id['separate_loops2']
    require(positive['exact_null']['edge_budget']['contrast'] == Fraction(1, 2) and
            negative['exact_null']['edge_budget']['contrast'] == Fraction(-1, 2), 'synthetic signed contrast witnesses')
    for name in ('support_fraction', 'occurrence_fraction'):
        require(positive['exact_null'][name]['undefined_mass'] == Fraction(1, 2) and
                positive['exact_null'][name]['mean'] is None, 'undefined null mass was conditioned away')
    paired = []
    for case in design['paired_arithmetic_controls']:
        values = [Fraction(*v) if v is not None else None for v in case['scores']]
        effect = paired_change(values)
        require(encoded(effect) == case['expected'], 'paired difference-in-changes arithmetic')
        paired.append(dict(id=case['id'], endpoint_status=case['endpoint_status'], effect=effect))
    require(parent_mean([Fraction(1), None]) is None, 'unavailable parent omitted')
    recommendations = [name for name in METRICS if all(criteria[name].values())]
    emit(dict(kind='design_decision', criteria=criteria, recommend_for_next_calibration=recommendations,
              paired_controls=paired, incomplete_two_parent_mean=None, total_parents=2))
    preflight()
    return encoded(dict(protocol_id='R06a-v1', audit_status='pass', scientific_status='untested',
        design_status='analytical_review_complete_not_production_calibration', counts=dict(counts),
        criteria=criteria, exact_null_statuses={k: dict(v) for k, v in statuses.items()},
        scaling_results=families, positive_and_negative_controls=[positive, negative], paired_controls=paired,
        recommend_for_next_calibration=recommendations, selection_policy=design['selection_policy'],
        hypothesis=design['physical_question'], draft_intervention_estimand=design['intervention_estimand'],
        scientific_effect_threshold=None, production_metric_adopted=False, promotion_authorized=False,
        source_sha256=protocol['pins_sha256'], protocol_sha256=sha(ROOT / 'protocols/r06a.json'),
        trace_sha256=digest.hexdigest(), trace_bytes=trace_bytes, graph_transitions_executed=0,
        random_null_draws_executed=0, native_runs=0, trajectory_files_read=0, holdout_jobs_executed=0,
        g2_rule_or_seed_panels_scored=0, candidate_scientific_statistics_evaluated=0,
        campaign_authorized=False, next_boundary=protocol['next_boundary']))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output-directory', type=Path)
    group.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.verify:
        require(audit() == json.loads(args.verify.read_text()), 'R06a receipt mismatch')
        print('R06a analytical receipt verified without random draws, trajectories or native binaries')
        return
    protocol, _ = preflight()
    args.output_directory.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    execution = dict(protocol_id='R06a-v1', audit_status='fail')
    with (args.output_directory / 'started.json').open('x') as f:
        json.dump(dict(protocol_sha256=sha(ROOT / 'protocols/r06a.json')), f)
    try:
        with (args.output_directory / 'controls.jsonl').open('xb') as f:
            result = audit(f)
        with (args.output_directory / 'design.json').open('x') as f:
            json.dump(result, f, indent=2, sort_keys=True)
            f.write('\n')
        execution.update(audit_status='pass', receipt_sha256=sha(args.output_directory / 'design.json'),
                         trace_sha256=result['trace_sha256'])
    except Exception as error:
        execution['error'] = f'{type(error).__name__}: {error}'.replace(str(ROOT), '<repo>')
    execution['elapsed_seconds'] = time.monotonic() - start
    execution['retained_bytes_before_receipt'] = sum(p.stat().st_size for p in args.output_directory.iterdir())
    if (execution['elapsed_seconds'] > protocol['budgets']['global_wall_seconds'] or
            execution['retained_bytes_before_receipt'] + 4096 > protocol['budgets']['retained_bytes']):
        execution.update(audit_status='fail', error='final analytical review budget exceeded')
    with (args.output_directory / 'execution.json').open('x') as f:
        json.dump(execution, f, indent=2, sort_keys=True)
        f.write('\n')
    print(json.dumps(execution, sort_keys=True))
    raise SystemExit(0 if execution['audit_status'] == 'pass' else 1)


if __name__ == '__main__':
    main()
