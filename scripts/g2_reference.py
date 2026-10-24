"""Independent dictionary/occurrence-pair G2 replay oracle."""
from copy import deepcopy

MASK = (1 << 64) - 1


def word(state):
    state = (state + 0x9e3779b97f4a7c15) & MASK
    value = ((state ^ (state >> 30)) * 0xbf58476d1ce4e5b9) & MASK
    value = ((value ^ (value >> 27)) * 0x94d049bb133111eb) & MASK
    return state, value ^ (value >> 31)


def sample(state, count):
    if not 0 < count <= MASK:
        raise ValueError('invalid sample bound')
    while True:
        state, value = word(state)
        if value >= (1 << 64) % count:
            return state, value % count


class Reference:
    def __init__(self, config):
        self.config = deepcopy(config)
        self.nodes = config['nodes']
        self.rng = config['rng']
        self.edges = {i: [i, *arc, None] for i, arc in enumerate(config['seed'])}
        self.next_edge = len(self.edges)
        self.events = []

    def matches(self):
        return [[a, b] for a in sorted(self.edges) for b in sorted(self.edges)
                if a != b and self.edges[a][2] == self.edges[b][1]]

    def advance(self):
        matches = self.matches()
        limits = self.config['limits']
        rhs = self.config['rhs']
        if not matches:
            return 'no_eligible_match'
        if len(self.events) >= limits['events']:
            return 'event_cap'
        fresh = any(3 in arc for arc in rhs)
        if self.nodes + fresh > limits['nodes']:
            return 'node_cap'
        if len(self.edges) - 2 + len(rhs) > limits['edges']:
            return 'edge_cap'
        if len(matches) > limits['matches']:
            return 'match_cap'
        scheduler = self.config['scheduler']
        index = 0
        if scheduler == 'lex_last':
            index = len(matches) - 1
        elif scheduler == 'uniform_match':
            self.rng, index = sample(self.rng, len(matches))
        elif scheduler != 'lex_first':
            raise ValueError('unknown scheduler')
        a_id, b_id = matches[index]
        a, b = self.edges.pop(a_id), self.edges.pop(b_id)
        binding = [a[1], a[2], b[2], self.nodes]
        event_id = len(self.events)
        self.events.append(dict(id=event_id, consumed=[a, b], binding=binding[:3],
                                parents=sorted({edge[3] for edge in (a, b) if edge[3] is not None}),
                                fresh=self.nodes if fresh else None,
                                first_output=self.next_edge, output_count=len(rhs),
                                scheduler=scheduler, rng=self.rng))
        self.nodes += fresh
        for i, (source, target) in enumerate(rhs):
            edge_id = self.next_edge + i
            self.edges[edge_id] = [edge_id, binding[source], binding[target], event_id]
        self.next_edge += len(rhs)
        return 'applied'

    def snapshot(self, status):
        return deepcopy(dict(status=status, nodes=self.nodes, next_edge=self.next_edge,
                             rng=self.rng, scheduler=self.config['scheduler'],
                             edges=[self.edges[i] for i in sorted(self.edges)], events=self.events))

    def prefix(self, events):
        while len(self.events) < events:
            status = self.advance()
            if status != 'applied':
                return self.snapshot(status)
        return self.snapshot('checkpoint')

    def run(self):
        while True:
            status = self.advance()
            if status != 'applied':
                return self.snapshot(status)
