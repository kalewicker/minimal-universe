"""R05f metrology: supplied G2 states only; never executes world transitions.

Sampling intervals describe Monte Carlo error under the ideal iid permutation
model. The deterministic SHA stream is reproducible, not a proof of iid draws.
"""
from collections import Counter, defaultdict
from fractions import Fraction
from hashlib import sha256
from itertools import permutations
import json
import math
import re

SAMPLES = 16384
DELTA = Fraction(1, 100)
GRID = 1000000


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode('ascii')


def natural(value):
    return type(value) is int and value >= 0


def graph(nodes, edges):
    edges = tuple(tuple(e) for e in edges)
    if not natural(nodes) or nodes > 64 or len(edges) > 64:
        raise ValueError('observer domain: at most 64 nodes and 64 edges')
    if any(len(e) != 2 or any(not natural(v) or v >= nodes for v in e) for e in edges):
        raise ValueError('invalid endpoints')
    return tuple(sorted(edges))


def graph_digest(nodes, edges):
    return sha256(canonical(dict(schema='mu-g2-null-graph-v1', nodes=nodes,
                                 edges=graph(nodes, edges)))).hexdigest()


def score(nodes, edges):
    arcs = set(edges)
    return (Fraction(sum(u < v and (v, u) in arcs for u, v in arcs), math.comb(nodes, 2))
            if nodes >= 2 else None)


def radius(quota, samples=SAMPLES):
    if type(quota) is not int or quota <= 0 or type(samples) is not int or samples <= 0:
        raise ValueError('positive registered quota and sample count required')
    limit, power = 2 * quota / DELTA, 0
    while 2 ** power < limit:
        power += 1
    # Smallest integer q with q*q * 2B >= L * grid^2, using exact arithmetic.
    numerator = power * GRID * GRID
    q = math.isqrt(numerator // (2 * samples))
    if q * q * 2 * samples < numerator:
        q += 1
    return Fraction(q, GRID)


class WordBudgetExceeded(Exception):
    pass


class Words:
    """Per-query attempted-word accounting; per-draw counter resets to zero."""
    def __init__(self, root, query, digest, budget):
        if not isinstance(root, str) or re.fullmatch('[0-9a-f]{64}', root) is None:
            raise ValueError('root must be 64 lowercase hex characters')
        if not isinstance(query, str) or not query:
            raise ValueError('registered query ID required')
        self.root, self.query, self.digest = root, query, digest
        self.budget, self.total, self.counter = budget, 0, 0

    def start(self, draw):
        self.counter = 0
        self.base = sha256(canonical(dict(schema='mu-g2-null-word-v1', root=self.root,
                                         query=self.query, graph=self.digest, draw=draw)) + b'\n')

    def word(self):
        if self.total >= self.budget:
            raise WordBudgetExceeded()
        h = self.base.copy()
        h.update(str(self.counter).encode('ascii'))
        self.counter += 1
        self.total += 1
        return int.from_bytes(h.digest()[:8], 'big')

    def below(self, bound):
        if type(bound) is not int or not 1 <= bound <= 2 ** 64:
            raise ValueError('invalid integer bound')
        threshold = 2 ** 64 % bound
        while True:
            word = self.word()
            if word >= threshold:
                return word % bound


def shuffle(size, below):
    order = list(range(size))
    for i in range(size - 1, 0, -1):
        j = below(i + 1)
        order[i], order[j] = order[j], order[i]
    return order


def exact_null(nodes, edges):
    edges = graph(nodes, edges)
    if len(edges) > 8:
        raise ValueError('exact null exceeds eight edges')
    if nodes < 2:
        return dict(status='undefined', distribution={}, mean=None, interval=None)
    sources, targets = [e[0] for e in edges], [e[1] for e in edges]
    counts = Counter(score(nodes, zip(sources, (targets[i] for i in order)))
                     for order in permutations(range(len(edges))))
    total = math.factorial(len(edges))
    distribution = {value: Fraction(count, total) for value, count in counts.items()}
    mean = sum((v * p for v, p in distribution.items()), Fraction())
    return dict(status='informative' if len(counts) > 1 else 'degenerate',
                distribution=distribution, mean=mean, interval=[mean, mean])


def degree_null(nodes, edges, *, root, query, quota, calibration_force_sample=False, on_draw=None):
    """Fixed B and delta; caller must register all quota slots before sampling.

    on_draw receives (draw, labelled permutation, score, attempted words). It may
    retain diagnostics and abort on external budgets. Such aborts must be kept by
    the caller as incomplete attempts; they never return a partial mean.
    """
    edges = graph(nodes, edges)
    r = radius(quota)
    if type(calibration_force_sample) is not bool or (calibration_force_sample and
            (not isinstance(query, str) or not query.startswith('mu/R05f-cal-v1/'))):
        raise ValueError('force sampling is restricted to registered synthetic calibration')
    if nodes < 2:
        return dict(status='undefined', mean=None, interval=None, quota=quota)
    if len(edges) <= 8 and not calibration_force_sample:
        return dict(exact_null(nodes, edges), quota=quota, mode='exact')
    digest = graph_digest(nodes, edges)
    words = Words(root, query, digest, 4 * SAMPLES * max(len(edges) - 1, 1))
    sources, targets = [e[0] for e in edges], [e[1] for e in edges]
    histogram = Counter()
    completed = 0
    try:
        for draw in range(SAMPLES):
            words.start(draw)
            order = shuffle(len(edges), words.below)
            value = score(nodes, zip(sources, (targets[i] for i in order)))
            histogram[value] += 1
            completed += 1
            if on_draw is not None:
                on_draw(draw, order, value, words.counter)
    except WordBudgetExceeded:
        return dict(status='rng_budget_exhausted', mean=None, interval=None,
                    completed_draws=completed, histogram=dict(histogram), words=words.total,
                    partial_draw=completed, partial_draw_words=words.counter,
                    root=root, query=query, graph=digest, quota=quota)
    mean = sum((v * count for v, count in histogram.items()), Fraction()) / SAMPLES
    interval = [max(Fraction(), mean - r), min(Fraction(1), mean + r)]
    observed = score(nodes, edges)
    return dict(status='witnessed_nonconstant' if len(histogram) > 1 else 'sampled_constant_unresolved',
                mode='sampled', mean=mean, interval=interval, radius=r, histogram=dict(histogram),
                contrast_interval=[observed - interval[1], observed - interval[0]],
                samples=SAMPLES, words=words.total, word_budget=words.budget,
                root=root, query=query, graph=digest, quota=quota, delta=DELTA,
                uncertainty='Monte Carlo only; ideal iid permutation model', scientific_acceptance=False)


def state(nodes, edges):
    edges = tuple(tuple(e) for e in edges)
    if any(len(e) != 3 or not natural(e[0]) for e in edges):
        raise ValueError('invalid occurrence record')
    graph(nodes, [e[1:] for e in edges])
    if len({e[0] for e in edges}) != len(edges):
        raise ValueError('duplicate occurrence ID')
    return edges


def exposure(nodes, edges, targets):
    edges = state(nodes, edges)
    targets = tuple(targets)
    if (len(set(targets)) != len(targets) or any(not natural(t) for t in targets)
            or not set(targets) <= {e[0] for e in edges}):
        raise ValueError('invalid active target occurrence set')
    target = set(targets)
    incoming, outgoing = defaultdict(list), defaultdict(list)
    counts = Counter({e[0]: 0 for e in edges})
    for identity, u, v in edges:
        incoming[v].append(identity)
        outgoing[u].append(identity)
    total = hit = 0
    for v, arrivals in incoming.items():
        for a in arrivals:
            for b in outgoing[v]:
                if a != b:
                    total += 1
                    hit += a in target or b in target
                    counts[a] += 1
                    counts[b] += 1
    return dict(matches=total, occurrence_match_counts=dict(sorted(counts.items())),
                target_union_matches=hit,
                probability_avoid=Fraction(total - hit, total) if total else None,
                status='defined' if total else 'no_eligible_match')


def observed_endpoint(*, nodes, edges, parent_ids, targets, parent_event, event,
                      horizon, status='reached', scheduler='uniform_match'):
    """Caller supplies independently validated history. No history is simulated.

    parent_ids and targets are frozen at parent_event. An unavailable endpoint has
    no fabricated snapshot. Local hazards are not unconditional horizon survival.
    """
    if (not all(natural(x) for x in (parent_event, event, horizon)) or horizon > 50
            or not parent_event <= event <= parent_event + horizon):
        raise ValueError('invalid event interval')
    if scheduler not in ('uniform_match', 'lex_first', 'lex_last'):
        raise ValueError('unknown scheduler')
    parent_ids, targets = tuple(parent_ids), tuple(targets)
    if (any(not natural(i) for i in parent_ids + targets) or len(set(parent_ids)) != len(parent_ids)
            or len(set(targets)) != len(targets) or not set(targets) <= set(parent_ids)):
        raise ValueError('targets must be frozen parent occurrences')
    result = dict(status=status, observed_untouched=None, local=None, parent_event=parent_event,
                  event=event, horizon=horizon, scheduler=scheduler,
                  probability_scope='local next uniform match only; no survival product')
    if status in ('terminal_before_horizon', 'resource_censored', 'domain_unsupported', 'undefined'):
        if nodes is not None or edges is not None:
            raise ValueError('unavailable endpoint must not invent reached state')
        return result
    if status != 'reached' or event != parent_event + horizon:
        raise ValueError('reached endpoint must match requested horizon')
    try:
        edges = state(nodes, edges)
    except ValueError:
        raise ValueError('validate supplied state; use explicit unsupported status for unavailable endpoint') from None
    intact = set(targets) <= {e[0] for e in edges}
    result['observed_untouched'] = intact
    local = exposure(nodes, edges, targets if intact else ())
    if not intact:
        local.update(status='target_already_consumed', probability_avoid=None, target_union_matches=None)
    elif scheduler != 'uniform_match':
        local.update(status='counts_only_deterministic_scheduler', probability_avoid=None)
    result['local'] = local
    return result
