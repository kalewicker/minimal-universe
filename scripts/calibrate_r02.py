#!/usr/bin/env python3
"""Exhaustive bounded measurement calibration; no world campaign."""
import argparse
from collections import Counter, defaultdict
from fractions import Fraction
from hashlib import sha256
from itertools import combinations, permutations, product
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'analysis'))
import measurements as m


def require(value, why):
    if not value:
        raise ValueError(why)


def oracle_connected(n, flat):
    components = [{i} for i in range(n)]
    for i in range(n):
        for j in range(n):
            if flat[i*n+j]:
                left = next(c for c in components if i in c)
                right = next(c for c in components if j in c)
                if left is not right:
                    components.remove(left)
                    components.remove(right)
                    components.append(left | right)
    return len(components) == 1


def orbit_table(n):
    table = {}
    # Exhaustive labeled templates, lexicographic first representative per orbit.
    for flat in product(range(3), repeat=n*n):
        if flat in table or not oracle_connected(n, flat):
            continue
        label = f'{n}:' + ''.join(map(str, flat))
        for bijection in permutations(range(n)):
            transformed = [0] * (n*n)
            for i in range(n):
                for j in range(n):
                    transformed[bijection[i]*n+bijection[j]] = flat[i*n+j]
            table[tuple(transformed)] = label
    return table


def oracle_motifs(n, edges, tables):
    counts, denominators = Counter(), Counter()
    for size in range(1, min(3, n)+1):
        for subset in combinations(range(n), size):
            denominators[size] += 1
            flat = tuple(sum(u == i and v == j for u, v in edges)
                         for i in subset for j in subset)
            label = tables[size].get(flat)
            if label is not None:
                counts[label] += 1
    return dict(counts=dict(sorted(counts.items())), denominators=dict(denominators),
                connected_subsets=sum(counts.values()), excluded_subsets=0, coverage_complete=True)


def enumerate_survival(initial, targets, output, horizon):
    protected = frozenset(range(targets))
    def visit(active, next_id, remaining):
        if remaining == 0:
            return Fraction(protected <= set(active))
        if not active:
            return None
        result = Fraction()
        for selected in active:
            after = tuple(i for i in active if i != selected) + tuple(range(next_id, next_id+output))
            value = visit(after, next_id+output, remaining-1)
            if value is None:
                return None
            result += value / len(active)
        return result
    return visit(tuple(range(initial)), initial, horizon)


def qualifying():
    return dict.fromkeys(m.FLAGS, True) | dict(
        structural_effect=.1, structural_lower=.01, structural_upper=.2, structural_p=.01,
        intervention_effect=.1, intervention_lower=.01, intervention_upper=.2, intervention_p=.01,
        complete_fraction=1, parents=30, schedulers=2)


def run(protocol, checks):
    tables = {n: orbit_table(n) for n in (1, 2, 3)}
    spec = protocol['structural_fixtures']
    for alphabet, sizes in [(2, spec['binary_adjacency_nodes']), (3, spec['ternary_adjacency_nodes'])]:
        for n in sizes:
            for flat in product(range(alphabet), repeat=n*n):
                edges = [(i, j) for i in range(n) for j in range(n) for _ in range(flat[i*n+j])]
                expected = oracle_motifs(n, edges, tables)
                require(m.motifs(n, edges) == expected, 'motif/orbit oracle mismatch')
                checks['structural_graphs'] += 1
                for perm in permutations(range(n)):
                    require(m.motifs(n, [(perm[i], perm[j]) for i, j in edges]) == expected,
                            'vertex relabeling changed measurement')
                    checks['relabelings'] += 1
    require(checks['structural_graphs'] == spec['expected_graphs'], 'structural denominator')
    spec = protocol['survival_fixtures']
    for initial in spec['initial_edges']:
        for targets in range(initial+1):
            for output in spec['output_edges']:
                for horizon in spec['horizons']:
                    expected = enumerate_survival(initial, targets, output, horizon)
                    require(m.survival_probability(initial, targets, output, horizon) == expected,
                            'analytical survival mismatch')
                    checks['survival_cases'] += 1
                    checks['unavailable_horizons'] += expected is None
    require(checks['survival_cases'] == spec['expected_cases'], 'survival denominator')
    spec = protocol['null_fixtures']
    n = spec['nodes']
    arcs = tuple(product(range(n), repeat=2))
    for length in spec['edge_counts']:
        strata = defaultdict(Counter)
        sequences = list(product(arcs, repeat=length))
        def degrees(edges):
            return (tuple(sum(u == i for u, _ in edges) for i in range(n)),
                    tuple(sum(v == i for _, v in edges) for i in range(n)))
        for edges in sequences:
            present = set(edges)
            score = Fraction(sum((i,j) in present and (j,i) in present
                                 for i,j in combinations(range(n), 2)), 3)
            strata[degrees(edges)][score] += 1
        for edges in sequences:
            histogram = strata[degrees(edges)]
            expected = {score: Fraction(count, sum(histogram.values())) for score, count in histogram.items()}
            result = m.degree_null(n, edges)
            require(result['distribution'] == expected, 'degree null distribution mismatch')
            require(result['status'] == ('informative' if len(expected)>1 else 'degenerate'), 'null support status')
            checks['null_graphs'] += 1
            checks['degenerate_nulls'] += result['status'] == 'degenerate'
    require(checks['null_graphs'] == spec['expected_graphs'], 'null denominator')
    require(m.paired_effect([('a', 0, 0, 0, 0)]) == 0, 'zero effect')
    require(m.paired_effect([('a', 0, Fraction(1,4), 0, 0)]) == Fraction(1,4), 'delayed effect')
    require(m.paired_effect([('a', 1, 1, 0, 0)]) == 0, 'immediate difference did not cancel')
    for rows in [[('a', None, 0, 0, 0)], [('a', 0, 0, 0, 0), ('a', 0, 0, 0, 0)]]:
        try:
            m.paired_effect(rows)
        except ValueError:
            continue
        raise ValueError('invalid causal pair accepted')
    checks['paired_effect_cases'] = 5
    base = qualifying()
    require(m.promotion(base), 'synthetic qualifying gate failed')
    checks['gate_cases'] += 1
    for flag in m.FLAGS:
        require(not m.promotion(base | {flag: False}), 'gate ignored ' + flag)
        checks['gate_cases'] += 1
    failures = dict(parents=29, schedulers=1, complete_fraction=.99,
                    structural_effect=.04, intervention_effect=.04,
                    structural_lower=0, intervention_lower=0,
                    structural_upper=.09, intervention_upper=.09,
                    structural_p=.051, intervention_p=.051)
    for field, value in failures.items():
        require(not m.promotion(base | {field: value}), 'gate ignored ' + field)
        checks['gate_cases'] += 1
    for record in [base | {'extra': True}, {k:v for k,v in base.items() if k != 'parents'}]:
        require(not m.promotion(record), 'gate accepted unknown/missing field')
        checks['gate_cases'] += 1
    return {'canonical_classes': {str(n): len(set(t.values())) for n,t in tables.items()},
            'interpretation': 'Exact finite calibration only; no real candidate evaluated.'}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    require(not args.output.exists(), 'refusing to overwrite evidence')
    paths = ['protocols/r02.json', 'protocols/r02-measurement-contract.json',
             'analysis/measurements.py', 'scripts/calibrate_r02.py', 'tests/test_measurements.py']
    result = {'protocol_id': 'R02-v1', 'scientific_status': 'untested', 'discovery_executed': False,
              'source_sha256': {p: sha256((ROOT/p).read_bytes()).hexdigest() for p in paths}}
    checks = Counter()
    failure = None
    try:
        result.update(run(json.loads((ROOT/'protocols/r02.json').read_text()), checks))
        result['status'] = 'pass'
    except Exception as error:
        failure = error
        result.update(status='fail', failure=str(error))
    result['checks'] = dict(checks)
    with args.output.open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    print(json.dumps(result, sort_keys=True))
    if failure:
        raise SystemExit(str(failure))


if __name__ == '__main__':
    main()
