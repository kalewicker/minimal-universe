"""Versioned R06b reference measurements on supplied graphs and synthetic pairs.

No world transitions, scientific primary adoption or inference engine. Sampling
intervals concern Monte Carlo error under an ideal iid stub-permutation model.
"""
from collections import Counter
from fractions import Fraction
from hashlib import sha256
from itertools import permutations
from math import factorial

from analysis import g2_observer_v1 as primitives
from analysis.measurements import partition as parent_partition

METRIC = 'mu-g2-edge-budget-v1'
WORD_SCHEMA = 'mu-g2-budget-null-word-v1'
SAMPLES, DELTA, GRID = 16384, Fraction(1, 100), 1000000
CALIBRATION_PREFIX = 'mu/R06b-cal-v1/'
PARENT_PREFIX = 'mu/G2-budget-cal-v1/'


def _score(arcs, count):
    support = set(arcs)
    return Fraction(2 * sum(a < b and (b, a) in support for a, b in support), count) if count else None


def score(nodes, edges):
    edges = primitives.graph(nodes, edges)
    return _score(edges, len(edges))


def observe(nodes, edges):
    edges = primitives.graph(nodes, edges)
    value = _score(edges, len(edges))
    return dict(metric=METRIC, nodes=nodes, edges=len(edges), score=value,
                status='defined' if value is not None else 'undefined_empty_graph')


class Words(primitives.Words):
    """Reuse frozen word accounting/rejection, with a metric-specific header."""
    def start(self, draw):
        self.counter = 0
        self.base = sha256(primitives.canonical(dict(schema=WORD_SCHEMA, root=self.root,
                            query=self.query, graph=self.digest, draw=draw)) + b'\n')


def exact_null(nodes, edges):
    edges = primitives.graph(nodes, edges)
    if len(edges) > 8:
        raise ValueError('exact budget null exceeds eight edges')
    observed = _score(edges, len(edges))
    if observed is None:
        return dict(metric=METRIC, mode='exact', status='undefined_empty_graph', distribution={},
                    mean=None, interval=None, contrast_interval=None)
    sources, targets = [a for a, _ in edges], [b for _, b in edges]
    histogram = Counter(_score(zip(sources, (targets[i] for i in order)), len(edges))
                        for order in permutations(range(len(edges))))
    total = factorial(len(edges))
    distribution = {v: Fraction(c, total) for v, c in histogram.items()}
    mean = sum((v * p for v, p in distribution.items()), Fraction())
    return dict(metric=METRIC, mode='exact', status='informative' if len(histogram) > 1 else 'degenerate',
                distribution=distribution, mean=mean, interval=[mean, mean],
                contrast_interval=[observed - mean, observed - mean])


def degree_null(nodes, edges, *, root, query, quota, calibration_force_sample=False, on_draw=None):
    """Quota counts every preregistered slot, including exact/undefined queries.

    B and delta are fixed. on_draw(draw, labels, score, words) may retain diagnostics
    or abort on an external budget. Such aborts never produce a partial estimate.
    """
    edges = primitives.graph(nodes, edges)
    r = primitives.radius(quota, SAMPLES)
    if type(calibration_force_sample) is not bool or (calibration_force_sample and
            (not isinstance(query, str) or not query.startswith(CALIBRATION_PREFIX))):
        raise ValueError('forced sampling requires the R06b synthetic namespace')
    digest = primitives.graph_digest(nodes, edges)
    words = Words(root, query, digest, 4 * SAMPLES * max(len(edges) - 1, 1))
    metadata = dict(metric=METRIC, graph=digest, root=root, query=query, quota=quota,
                    word_schema=WORD_SCHEMA, delta=DELTA, scientific_acceptance=False)
    if not edges or len(edges) <= 8 and not calibration_force_sample:
        return dict(exact_null(nodes, edges), **{k: v for k, v in metadata.items() if k != 'metric'}, words=0)
    sources, targets = [a for a, _ in edges], [b for _, b in edges]
    histogram = Counter()
    completed = 0
    try:
        for draw in range(SAMPLES):
            words.start(draw)
            labels = primitives.shuffle(len(edges), words.below)
            value = _score(zip(sources, (targets[i] for i in labels)), len(edges))
            histogram[value] += 1
            completed += 1
            if on_draw is not None:
                on_draw(draw, labels, value, words.counter)
    except primitives.WordBudgetExceeded:
        return dict(metadata, mode='sampled', status='rng_budget_exhausted', mean=None, interval=None,
                    contrast_interval=None, histogram=dict(histogram), completed_draws=completed,
                    words=words.total, word_budget=words.budget,
                    partial_draw=completed, partial_draw_words=words.counter)
    mean = sum((v * c for v, c in histogram.items()), Fraction()) / SAMPLES
    interval = [max(Fraction(), mean - r), min(Fraction(1), mean + r)]
    observed = _score(edges, len(edges))
    return dict(metadata, mode='sampled',
                status='witnessed_nonconstant' if len(histogram) > 1 else 'sampled_constant_unresolved',
                mean=mean, interval=interval, contrast_interval=[observed - interval[1], observed - interval[0]],
                histogram=dict(histogram), samples=SAMPLES, radius=r, words=words.total, word_budget=words.budget,
                uncertainty='Monte Carlo only; ideal iid uniform target-stub permutations, not proven by SHA')


def partition(parent):
    if not isinstance(parent, str) or not parent.startswith(PARENT_PREFIX) or not parent[len(PARENT_PREFIX):]:
        raise ValueError('synthetic budget parent namespace required; production parents unregistered')
    return parent_partition(parent)


BRANCH_FIELDS = {'parent', 'partition', 'scheduler', 'horizon', 'status',
                 'score_0', 'score_h', 'matches_0', 'matches_h'}
STATUSES = {'reached', 'terminal_before_horizon', 'resource_censored', 'domain_unsupported'}


def paired_bookkeeping(rows, horizon=50, scheduler='uniform_match'):
    """Supplied synthetic subsequent-change arithmetic, not causal validation.

    Initial scores are immediately post intervention. Every parent is retained;
    scores/eligibility provenance, valid shams and power remain unestablished.
    """
    if (not rows or not primitives.natural(horizon) or horizon > 50 or
            scheduler not in ('uniform_match', 'lex_first', 'lex_last')):
        raise ValueError('paired domain or scheduler')
    seen, output = set(), []
    for row in rows:
        if set(row) != {'parent', 'target', 'sham'}:
            raise ValueError('paired row fields')
        parent = row['parent']
        split = partition(parent)
        if parent in seen:
            raise ValueError('duplicate independent parent')
        seen.add(parent)
        branches = row['target'], row['sham']
        for branch in branches:
            if set(branch) != BRANCH_FIELDS or branch['parent'] != parent or branch['partition'] != split:
                raise ValueError('branch parent or inherited partition')
            if type(branch['horizon']) is not int or branch['horizon'] != horizon or branch['scheduler'] != scheduler:
                raise ValueError('branch horizon or scheduler')
            if branch['status'] not in STATUSES:
                raise ValueError('unknown endpoint status')
            for key in ('score_0', 'score_h'):
                value = branch[key]
                if value is not None and (type(value) not in (int, Fraction) or not 0 <= value <= 1):
                    raise ValueError('invalid score')
            if not primitives.natural(branch['matches_0']):
                raise ValueError('missing initial match count')
            if branch['status'] == 'reached':
                if not primitives.natural(branch['matches_h']):
                    raise ValueError('missing reached match count')
            elif branch['score_h'] is not None or branch['matches_h'] is not None:
                raise ValueError('invented unavailable endpoint')
        reasons = []
        for name, branch in zip(('target', 'sham'), branches):
            if branch['status'] != 'reached':
                reasons.append(name + ':' + branch['status'])
            if branch['score_0'] is None or branch['status'] == 'reached' and branch['score_h'] is None:
                reasons.append(name + ':undefined_score')
        target, sham = branches
        effect = None if reasons else (Fraction(target['score_h']) - target['score_0'] -
                                       Fraction(sham['score_h']) + sham['score_0'])
        output.append(dict(parent=parent, partition=split, effect=effect, unavailable_reasons=reasons,
            initial_match_counts=[target['matches_0'], sham['matches_0']],
            endpoint_match_counts=[target['matches_h'], sham['matches_h']],
            initial_eligibility_changed=target['matches_0'] != sham['matches_0'],
            endpoint_eligibility_changed=target['matches_h'] != sham['matches_h']
            if all(b['status'] == 'reached' for b in branches) else None))
    complete = sum(row['effect'] is not None for row in output)
    return dict(metric=METRIC, pairs=output, total_pairs=len(output), complete_pairs=complete,
                unavailable_pairs=len(output) - complete,
                mean_effect=sum((row['effect'] for row in output), Fraction()) / len(output)
                if complete == len(output) else None,
                status='complete' if complete == len(output) else 'incomplete',
                estimand='subsequent paired change; instantaneous score change excluded',
                sham_validity='not_established', scientific_acceptance=False, production_metric_adopted=False)
