"""Exact bounded G2 measurements on supplied states and toy histories."""
from collections import Counter, defaultdict
from dataclasses import dataclass
from fractions import Fraction
from hashlib import sha256


MAX_NODES, MAX_EDGES, MAX_HORIZON, MAX_FRONTIER, MAX_MATCHES = 8, 8, 3, 50000, 64


def _integer(value):
    return type(value) is int and value >= 0


def _state(nodes, edges):
    if not _integer(nodes) or nodes > MAX_NODES:
        raise ValueError('node domain')
    edges = tuple(tuple(edge) for edge in edges)
    if len(edges) > MAX_EDGES:
        raise ValueError('edge domain')
    ids = set()
    for edge in edges:
        if len(edge) != 3:
            raise ValueError('edge must contain ID and two endpoints')
        edge_id, source, target = edge
        if not all(_integer(x) for x in edge) or edge_id in ids or source >= nodes or target >= nodes:
            raise ValueError('invalid edge occurrence')
        ids.add(edge_id)
    return nodes, tuple(sorted(edges)), max(ids, default=-1) + 1


def _targets(targets, initial_ids):
    targets = tuple(targets)
    if any(not _integer(x) for x in targets) or len(set(targets)) != len(targets) or not set(targets) <= set(initial_ids):
        raise ValueError('invalid target occurrence set')
    return frozenset(targets)


def _matches(state):
    nodes, edges, _ = state
    incoming, outgoing = [[] for _ in range(nodes)], [[] for _ in range(nodes)]
    for edge in edges:
        outgoing[edge[1]].append(edge)
        incoming[edge[2]].append(edge)
    pairs = [(a, b) for vertex in range(nodes) for a in incoming[vertex]
             for b in outgoing[vertex] if a[0] != b[0]]
    if len(pairs) > MAX_MATCHES:
        raise ValueError('match domain')
    return pairs


def exposure(nodes, edges, targets):
    state = _state(nodes, edges)
    target = _targets(targets, [edge[0] for edge in state[1]])
    pairs = _matches(state)
    incidence = Counter({edge[0]: 0 for edge in state[1]})
    hit = 0
    for a, b in pairs:
        incidence[a[0]] += 1
        incidence[b[0]] += 1
        hit += a[0] in target or b[0] in target
    count = len(pairs)
    return dict(matches=count, occurrence_match_counts=dict(sorted(incidence.items())),
                target_union_matches=hit,
                probability_avoid=Fraction(count - hit, count) if count else None,
                status='defined' if count else 'no_eligible_match')


@dataclass(frozen=True)
class Horizon:
    initial_ids: frozenset
    horizon: int
    states: dict
    terminal_by_event: tuple


def exact_horizon(nodes, edges, rhs, horizon):
    state = _state(nodes, edges)
    if not _integer(horizon) or horizon > MAX_HORIZON:
        raise ValueError('horizon domain')
    rhs = tuple(tuple(arc) for arc in rhs)
    if len(rhs) > 3 or rhs != tuple(sorted(rhs)) or any(
            len(arc) != 2 or any(not _integer(x) or x > 3 for x in arc) for arc in rhs):
        raise ValueError('invalid canonical RHS')
    fresh = any(3 in arc for arc in rhs)
    if nodes + fresh * horizon > MAX_NODES or len(state[1]) + max(0, len(rhs) - 2) * horizon > MAX_EDGES:
        raise ValueError('prospective measurement domain')
    initial_ids = frozenset(edge[0] for edge in state[1])
    states = {state: Fraction(1)}
    terminal = []
    for _ in range(horizon):
        next_states = defaultdict(Fraction)
        stopped = Fraction()
        for current, mass in states.items():
            pairs = _matches(current)
            if not pairs:
                stopped += mass
                continue
            n, active, next_id = current
            branch_mass = mass / len(pairs)
            for a, b in pairs:
                binding = (a[1], a[2], b[2], n)
                remaining = tuple(edge for edge in active if edge[0] not in (a[0], b[0]))
                emitted = tuple((next_id + i, binding[source], binding[target])
                                for i, (source, target) in enumerate(rhs))
                successor = (n + fresh, remaining + emitted, next_id + len(rhs))
                next_states[successor] += branch_mass
                if len(next_states) > MAX_FRONTIER:
                    raise ValueError('frontier domain')
        terminal.append(stopped)
        states = dict(next_states)
    return Horizon(initial_ids, horizon, states, tuple(terminal))


def survival(distribution, targets):
    if not isinstance(distribution, Horizon):
        raise ValueError('expected exact horizon distribution')
    targets = _targets(targets, distribution.initial_ids)
    reached = sum(distribution.states.values(), Fraction())
    surviving = sum((mass for (_, edges, _), mass in distribution.states.items()
                     if targets <= {edge[0] for edge in edges}), Fraction())
    unavailable = sum(distribution.terminal_by_event, Fraction())
    if reached + unavailable != 1:
        raise ValueError('probability mass not conserved')
    return dict(reached_mass=reached, surviving_reached_mass=surviving,
                consumed_reached_mass=reached - surviving, unavailable_mass=unavailable,
                conditional_survival=surviving / reached if reached else None,
                terminal_mass_by_event=list(distribution.terminal_by_event),
                status='fully_reached' if reached == 1 else 'unavailable' if not reached else 'partly_unavailable')


def partition(parent):
    if not isinstance(parent, str) or not parent.startswith('mu/G2-cal-v1/') or not parent.removeprefix('mu/G2-cal-v1/'):
        raise ValueError('invalid calibration parent namespace')
    bucket = int.from_bytes(sha256(parent.encode()).digest()[:8], 'big') % 10
    return ('discovery' if bucket < 4 else 'detector-development' if bucket < 6
            else 'validation' if bucket < 8 else 'final-test')


BRANCH_FIELDS = {'parent', 'partition', 'scheduler', 'horizon', 'status',
                 'density_0', 'density_h', 'matches_0', 'matches_h'}
STATUSES = {'reached', 'terminal_before_horizon', 'resource_censored', 'domain_unsupported'}


def paired_bookkeeping(rows, horizon, scheduler='uniform_match'):
    if not rows or not _integer(horizon) or scheduler not in ('uniform_match', 'lex_first', 'lex_last'):
        raise ValueError('invalid paired sample')
    seen, output = set(), []
    for row in rows:
        if set(row) != {'parent', 'target', 'sham'}:
            raise ValueError('paired row fields')
        parent = row['parent']
        split = partition(parent)
        if parent in seen:
            raise ValueError('duplicate independent parent')
        seen.add(parent)
        branches = (row['target'], row['sham'])
        for branch in branches:
            if set(branch) != BRANCH_FIELDS or branch['parent'] != parent or branch['partition'] != split:
                raise ValueError('branch identity or partition')
            if type(branch['horizon']) is not int or branch['horizon'] != horizon or branch['scheduler'] != scheduler:
                raise ValueError('branch horizon or scheduler')
            if branch['status'] not in STATUSES:
                raise ValueError('unknown endpoint status')
            for key in ('density_0', 'density_h'):
                value = branch[key]
                if value is not None and (type(value) not in (int, Fraction) or not 0 <= value <= 1):
                    raise ValueError('invalid endpoint density')
            if not _integer(branch['matches_0']):
                raise ValueError('missing initial match count')
            if branch['status'] == 'reached':
                if not _integer(branch['matches_h']):
                    raise ValueError('missing reached match count')
            elif branch['density_h'] is not None or branch['matches_h'] is not None:
                raise ValueError('invented unavailable endpoint')
        reasons = []
        for name, branch in zip(('target', 'sham'), branches):
            if branch['status'] != 'reached':
                reasons.append(name + ':' + branch['status'])
            if branch['density_0'] is None or branch['status'] == 'reached' and branch['density_h'] is None:
                reasons.append(name + ':undefined_density')
        target, sham = branches
        effect = None if reasons else (Fraction(target['density_h']) - target['density_0'] -
                                       Fraction(sham['density_h']) + sham['density_0'])
        output.append(dict(parent=parent, partition=split, effect=effect, unavailable_reasons=reasons,
                           initial_match_counts=[target['matches_0'], sham['matches_0']],
                           endpoint_match_counts=[target['matches_h'], sham['matches_h']],
                           initial_eligibility_changed=target['matches_0'] != sham['matches_0'],
                           endpoint_eligibility_changed=(target['matches_h'] != sham['matches_h'])
                           if all(b['status'] == 'reached' for b in branches) else None))
    complete = sum(row['effect'] is not None for row in output)
    return dict(pairs=output, total_pairs=len(output), complete_pairs=complete,
                unavailable_pairs=len(output) - complete,
                mean_effect=sum((row['effect'] for row in output), Fraction()) / len(output)
                if complete == len(output) else None,
                status='complete' if complete == len(output) else 'incomplete',
                sham_validity='not_established', scientific_acceptance=False)
