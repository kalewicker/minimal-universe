"""Bounded exact measurements. No simulation or candidate search."""
from collections import Counter
from fractions import Fraction
from hashlib import sha256
from itertools import combinations, permutations
import math


def adjacency(nodes, edges):
    if type(nodes) is not int or not 0 <= nodes <= 64:
        raise ValueError('node count outside measurement domain')
    matrix = [[0] * nodes for _ in range(nodes)]
    for u, v in edges:
        if type(u) is not int or type(v) is not int or not (0 <= u < nodes and 0 <= v < nodes):
            raise ValueError('invalid edge endpoint')
        matrix[u][v] += 1
    return tuple(tuple(row) for row in matrix)


def connected(matrix):
    reached = {0}
    while True:
        expanded = reached | {j for i in reached for j in range(len(matrix))
                              if matrix[i][j] or matrix[j][i]}
        if reached == expanded:
            return len(reached) == len(matrix)
        reached = expanded


def signature(matrix):
    n = len(matrix)
    if not 1 <= n <= 3:
        raise ValueError('motif size outside calibrated domain')
    return str(n) + ':' + ''.join(map(str, min(
        tuple(matrix[i][j] for i in order for j in order)
        for order in permutations(range(n)))))


def motifs(nodes, edges):
    matrix = adjacency(nodes, edges)
    counts, denominators = Counter(), Counter()
    excluded = 0
    eligible = 0
    for size in range(1, min(3, nodes) + 1):
        for subset in combinations(range(nodes), size):
            denominators[size] += 1
            sub = tuple(tuple(matrix[i][j] for j in subset) for i in subset)
            if not connected(sub):
                continue
            eligible += 1
            if any(value > 2 for row in sub for value in row):
                excluded += 1
                continue
            counts[signature(sub)] += 1
    return dict(counts=dict(sorted(counts.items())), denominators=dict(denominators),
                connected_subsets=eligible, excluded_subsets=excluded,
                coverage_complete=excluded == 0)


def reciprocal_density(nodes, edges):
    matrix = adjacency(nodes, edges)
    if nodes < 2:
        return None
    return Fraction(sum(bool(matrix[i][j] and matrix[j][i])
                        for i, j in combinations(range(nodes), 2)), math.comb(nodes, 2))


def survival_probability(initial_edges, target_edges, output_edges, horizon):
    args = (initial_edges, target_edges, output_edges, horizon)
    if any(type(x) is not int or x < 0 for x in args) or target_edges > initial_edges:
        raise ValueError('invalid survival parameters')
    probability = Fraction(1)
    for t in range(horizon):
        total = initial_edges + t * (output_edges - 1)
        if total <= 0:
            return None
        # Once the fixed target set cannot survive, the probability remains zero.
        probability *= max(Fraction(0), Fraction(total - target_edges, total))
    return probability


def untouched(initial_ids, current_ids):
    initial, current = tuple(initial_ids), tuple(current_ids)
    if len(set(initial)) != len(initial) or len(set(current)) != len(current):
        raise ValueError('duplicate edge occurrence identity')
    return set(initial) <= set(current)


def degree_null(nodes, edges):
    edges = tuple(edges)
    adjacency(nodes, edges)
    if len(edges) > 8:
        raise ValueError('exact degree null exceeds eight edges')
    if nodes < 2:
        return {'status': 'undefined', 'distribution': {}}
    sources = tuple(u for u, _ in edges)
    targets = tuple(v for _, v in edges)
    # Every distinct target sequence has the same product of factorial duplicate
    # multiplicities, so deduplicating permutations preserves uniform stub mass.
    distribution = Counter(reciprocal_density(nodes, zip(sources, order))
                           for order in set(permutations(targets)))
    total = sum(distribution.values())
    probabilities = {value: Fraction(count, total) for value, count in distribution.items()}
    return {'status': 'informative' if len(probabilities) > 1 else 'degenerate',
            'distribution': probabilities}


def paired_effect(rows):
    if not rows:
        raise ValueError('empty paired sample')
    seen, effects = set(), []
    for parent, target0, targeth, sham0, shamh in rows:
        if not isinstance(parent, str) or not parent or parent in seen:
            raise ValueError('missing or duplicate independent parent')
        values = (target0, targeth, sham0, shamh)
        if any(v is None or not isinstance(v, (int, Fraction)) or not 0 <= v <= 1 for v in values):
            raise ValueError('undefined or invalid endpoint density')
        seen.add(parent)
        effects.append(Fraction(targeth) - target0 - Fraction(shamh) + sham0)
    return sum(effects, Fraction()) / len(effects)


def partition(parent_key):
    if not isinstance(parent_key, str) or not parent_key:
        raise ValueError('parent key is required')
    bucket = int.from_bytes(sha256(parent_key.encode('utf-8')).digest()[:8], 'big') % 10
    return ('discovery' if bucket < 4 else 'detector-development' if bucket < 6
            else 'validation' if bucket < 8 else 'final-test')


def holm(pvalues):
    if any(not isinstance(p, (float, int)) or not math.isfinite(p) or not 0 <= p <= 1
           for p in pvalues):
        raise ValueError('invalid p-value')
    result = [0.0] * len(pvalues)
    previous = 0.0
    for rank, index in enumerate(sorted(range(len(pvalues)), key=lambda i: pvalues[i])):
        previous = max(previous, min(1.0, (len(pvalues) - rank) * pvalues[index]))
        result[index] = previous
    return result


FLAGS = ('null_informative', 'motif_coverage_complete', 'detector_frozen',
         'heldout_validated', 'parent_split_valid', 'family_complete')
NUMERIC = ('structural_effect', 'structural_lower', 'structural_upper', 'structural_p',
           'intervention_effect', 'intervention_lower', 'intervention_upper', 'intervention_p',
           'complete_fraction', 'parents', 'schedulers')


def promotion(record):
    """Validate supplied statistics only; does not estimate them or certify custody."""
    if set(record) != set(FLAGS + NUMERIC):
        return False
    if any(record[f] is not True for f in FLAGS):
        return False
    if any(type(record[n]) not in (float, int) or not math.isfinite(record[n]) for n in NUMERIC):
        return False
    if type(record['parents']) is not int or type(record['schedulers']) is not int:
        return False
    if record['parents'] < 30 or record['schedulers'] < 2 or record['complete_fraction'] != 1:
        return False
    for prefix in ('structural', 'intervention'):
        effect, low, high, p = (record[f'{prefix}_{field}'] for field in ('effect', 'lower', 'upper', 'p'))
        if not (-2 <= low <= effect <= high <= 2 and effect >= .05 and low > 0 and 0 <= p <= .05):
            return False
    return True
