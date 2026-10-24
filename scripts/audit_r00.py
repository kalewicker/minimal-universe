#!/usr/bin/env python3
"""Small, deterministic R00 specification checks. Not a discovery simulator."""
import argparse
from collections import Counter
from dataclasses import dataclass, replace
from functools import lru_cache
from hashlib import sha256
from itertools import combinations, combinations_with_replacement, permutations, product
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def require(condition, message):
    if not condition:
        raise ValueError(message)


@dataclass(frozen=True)
class Edge:
    identity: int
    source: int
    target: int
    producer: int | None = None


@dataclass(frozen=True)
class Graph:
    nodes: int
    edges: tuple[Edge, ...]
    next_edge: int
    events: int = 0


def seed_graph(seed):
    edges = tuple(Edge(i, *arc) for i, arc in enumerate(seed['edges']))
    require(all(0 <= e.source < seed['nodes'] and 0 <= e.target < seed['nodes']
                for e in edges), 'invalid seed endpoints')
    return Graph(seed['nodes'], edges, len(edges))


def rules(max_edges):
    arcs = tuple(product(range(3), repeat=2))
    return tuple(rhs for k in range(max_edges + 1)
                 for rhs in combinations_with_replacement(arcs, k))


def uses_fresh(rhs):
    return any(2 in arc for arc in rhs)


def step(graph, rhs, edge_id):
    consumed = next(e for e in graph.edges if e.identity == edge_id)
    binding = (consumed.source, consumed.target, graph.nodes)
    emitted = tuple(Edge(graph.next_edge + i, binding[a], binding[b], graph.events)
                    for i, (a, b) in enumerate(rhs))
    remaining = tuple(e for e in graph.edges if e.identity != edge_id)
    result = Graph(graph.nodes + int(uses_fresh(rhs)), remaining + emitted,
                   graph.next_edge + len(rhs), graph.events + 1)
    require(consumed.producer is None or consumed.producer < graph.events,
            'ancestry must point backward')
    return result, consumed.producer


def canonical(graph):
    """Permutation oracle for tiny graphs; retain isolates through node count."""
    require(graph.nodes <= 7, 'permutation oracle limited to seven nodes')
    return (graph.nodes, min(tuple(sorted((p[e.source], p[e.target])
                                         for e in graph.edges))
                             for p in permutations(range(graph.nodes))))


@lru_cache(None)
def terms(leaves):
    if leaves == 1:
        return ('i',)
    return tuple((a, b) for left in range(1, leaves)
                 for a in terms(left) for b in terms(leaves - left))


def leaves(term):
    return 1 if term == 'i' else leaves(term[0]) + leaves(term[1])


def redexes(term, path=()):
    if term == 'i':
        return ()
    here = (path,) if term[0] == 'i' else ()
    return here + redexes(term[0], path + (0,)) + redexes(term[1], path + (1,))


IOTA_K = ('i', ('i', ('i', 'i')))
IOTA_S = ('i', IOTA_K)


def expand(term, path):
    if not path:
        require(term != 'i' and term[0] == 'i', 'not an iota redex')
        return ((term[1], IOTA_S), IOTA_K)
    children = list(term)
    children[path[0]] = expand(children[path[0]], path[1:])
    return tuple(children)


def audit(protocol):
    registry = rules(protocol['graph_rhs_max_edges'])
    counts = {
        'rules': len(registry),
        'no_fresh_rules': sum(not uses_fresh(r) for r in registry),
        'fresh_rules': sum(uses_fresh(r) for r in registry),
        'discovery_subset_rules': sum(uses_fresh(r) and len(r) in (2, 3) for r in registry),
    }
    for name, value in counts.items():
        require(value == protocol['expected_' + name], 'unexpected ' + name)
    require(len(set(registry)) == len(registry), 'duplicate rules')
    checks = Counter()
    for rhs in registry:
        for seed in protocol['seeds'].values():
            initial = seed_graph(seed)
            state = initial
            checks['graph_fixtures'] += 1
            for t in range(1, protocol['graph_steps_per_fixture'] + 1):
                if not state.edges:
                    require(len(rhs) == 0 or not initial.edges, 'unexpected halt')
                    break
                state, parent = step(state, rhs, min(e.identity for e in state.edges))
                require(state.nodes == initial.nodes + int(uses_fresh(rhs)) * t,
                        'node formula')
                require(len(state.edges) == len(initial.edges) + (len(rhs)-1)*t,
                        'edge formula')
                require(len({e.identity for e in state.edges}) == len(state.edges),
                        'duplicate edge identity')
                require(all(0 <= e.source < state.nodes and 0 <= e.target < state.nodes
                            for e in state.edges), 'invalid endpoint')
                require(parent is None or 0 <= parent < t-1, 'invalid parent')
                checks['graph_events'] += 1
            for a, b in combinations(initial.edges, 2):
                ab, _ = step(initial, rhs, a.identity)
                ab, _ = step(ab, rhs, b.identity)
                ba, _ = step(initial, rhs, b.identity)
                ba, _ = step(ba, rhs, a.identity)
                require(canonical(ab) == canonical(ba), 'commutation failure')
                checks['diamond_pairs'] += 1
    for n in range(1, protocol['iota_max_leaves'] + 1):
        for term in terms(n):
            checks['iota_terms'] += 1
            paths = redexes(term)
            require(bool(paths) == (n > 1), 'redex existence')
            for path in paths:
                after = expand(term, path)
                require(leaves(after) == n + 8, 'expansion leaf delta')
                require(bool(redexes(after)), 'expansion unexpectedly normalizes')
                checks['iota_expansion_steps'] += 1
    require(checks['iota_terms'] == protocol['expected_iota_terms'], 'term census count')
    return {'counts': counts, 'checks': dict(sorted(checks.items())),
            'status': 'pass', 'scientific_status': 'untested',
            'discovery_executed': False,
            'interpretation': 'Finite specification fixtures corroborate the documented proofs.'}


def receipt():
    protocol_path = ROOT / 'protocols/r00.json'
    result = audit(json.loads(protocol_path.read_text()))
    result['protocol_id'] = 'R00-v1'
    paths = ['protocols/r00.json', 'scripts/audit_r00.py', 'tests/test_r00.py',
             'docs/semantics.md', 'docs/r00-audit.md']
    result['sha256'] = {p: sha256((ROOT / p).read_bytes()).hexdigest() for p in paths}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output', type=Path)
    mode.add_argument('--verify', type=Path)
    args = parser.parse_args()
    result = receipt()
    if args.verify:
        require(json.loads(args.verify.read_text()) == result, 'receipt mismatch')
        print('PASS: receipt and all bound fixture checks reproduced')
    else:
        with args.output.open('x') as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write('\n')
        print(json.dumps(result['checks'], sort_keys=True))


if __name__ == '__main__':
    main()
