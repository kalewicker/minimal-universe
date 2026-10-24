"""Finite static G2 design checks; no production transition runner."""
import argparse
from collections import Counter
import hashlib
from itertools import combinations, combinations_with_replacement, permutations, product
import json
from math import comb
from pathlib import Path

from audit_r04 import audit as audit_r04, require

ROOT = Path(__file__).resolve().parents[1]


def matches(nodes, edges):
    """Direct occurrence-pair specification, independent of degree counting."""
    require(type(nodes) is int and nodes >= 0, 'invalid node count')
    for edge_id, arc in edges.items():
        require(type(edge_id) is int and edge_id >= 0, 'invalid edge ID')
        require(len(arc) == 2 and all(type(v) is int and 0 <= v < nodes for v in arc),
                'invalid endpoint')
    return tuple((a, b) for a in sorted(edges) for b in sorted(edges)
                 if a != b and edges[a][1] == edges[b][0])


def degree_count(nodes, edges):
    incoming, outgoing = [0] * nodes, [0] * nodes
    loops = 0
    for source, target in edges.values():
        outgoing[source] += 1
        incoming[target] += 1
        loops += source == target
    return sum(a * b for a, b in zip(incoming, outgoing)) - loops


def alias_class(vertices):
    names = {}
    return tuple(names.setdefault(v, len(names)) for v in vertices)


NAMED = {
    'empty_vertices': (0, [], ()),
    'single_loop': (1, [(0, 0)], ()),
    'parallel_loops': (1, [(0, 0), (0, 0)], ((0, 1), (1, 0))),
    'parallel_nonloops': (2, [(0, 1), (0, 1)], ()),
    'reciprocal_cycle': (2, [(0, 1), (1, 0)], ((0, 1), (1, 0))),
    'open_path': (3, [(0, 1), (1, 2)], ((0, 1),)),
    'out_fork': (3, [(0, 1), (0, 2)], ()),
    'overlap_counterexample': (3, [(0, 0), (0, 1), (1, 2)], ((0, 1), (1, 2))),
}


def static_checks(protocol):
    require(protocol['lhs'] == [[0, 1], [1, 2]] and
            protocol['rhs_symbols'] == [0, 1, 2, 3] and
            protocol['rhs_lengths'] == [0, 1, 2, 3] and
            protocol['fresh_symbol'] == 3, 'unregistered grammar')
    require(protocol['fixture_nodes'] == [1, 2, 3] and
            protocol['fixture_edge_counts'] == [0, 1, 2, 3, 4], 'unregistered fixtures')
    rules_by_length = Counter()
    without_fresh = 0
    arcs = tuple(product(protocol['rhs_symbols'], repeat=2))
    for k in protocol['rhs_lengths']:
        for rhs in combinations_with_replacement(arcs, k):
            rules_by_length[k] += 1
            without_fresh += all(3 not in arc for arc in rhs)
        require(rules_by_length[k] == comb(15 + k, k), 'rule census mismatch')
    require(sum(rules_by_length.values()) == protocol['expected_rules'] == 969 and
            without_fresh == protocol['expected_without_fresh'] == 220,
            'registered rule census mismatch')

    totals = Counter()
    alias_classes = set()
    overlap = Counter(disjoint=0, shared_one=0, shared_two=0)
    graphs_by_nodes = Counter()
    for nodes in protocol['fixture_nodes']:
        arc_types = tuple(product(range(nodes), repeat=2))
        for count in protocol['fixture_edge_counts']:
            for graph in combinations_with_replacement(arc_types, count):
                edges = dict(enumerate(graph))
                found = matches(nodes, edges)
                require(len(found) == degree_count(nodes, edges), 'degree oracle mismatch')
                totals['graphs'] += 1
                graphs_by_nodes[nodes] += 1
                totals['ordered_matches'] += len(found)
                for a, b in found:
                    alias_classes.add(alias_class((edges[a][0], edges[a][1], edges[b][1])))
                for first, second in combinations(found, 2):
                    shared = len(set(first) & set(second))
                    overlap[('disjoint', 'shared_one', 'shared_two')[shared]] += 1
                for perm in permutations(range(nodes)):
                    renamed = {i: (perm[a], perm[b]) for i, (a, b) in edges.items()}
                    require(matches(nodes, renamed) == found, 'vertex equivariance failed')
                    totals['vertex_permutations'] += 1
                for perm in permutations(range(count)):
                    renamed = {perm[i]: arc for i, arc in edges.items()}
                    expected = tuple(sorted((perm[a], perm[b]) for a, b in found))
                    require(matches(nodes, renamed) == expected, 'occurrence equivariance failed')
                    totals['occurrence_permutations'] += 1
        require(graphs_by_nodes[nodes] == sum(comb(nodes * nodes + m - 1, m)
                                             for m in protocol['fixture_edge_counts']),
                'graph census mismatch')
    require(totals['graphs'] == protocol['expected_graphs'] == 790, 'fixture count mismatch')
    expected_aliases = {(0, 0, 0), (0, 0, 1), (0, 1, 0), (0, 1, 1), (0, 1, 2)}
    require(alias_classes == expected_aliases and
            len(alias_classes) == protocol['expected_alias_classes'], 'alias coverage mismatch')
    require(set(protocol['named_cases']) == set(NAMED), 'named fixture matrix mismatch')
    for name in protocol['named_cases']:
        nodes, graph, expected = NAMED[name]
        require(matches(nodes, dict(enumerate(graph))) == expected, 'named fixture: ' + name)

    witness = protocol['counterexample']
    require(witness == {'nodes': 3, 'edges': [[0, 0], [0, 1], [1, 2]], 'rhs': []},
            'counterexample changed')
    edges = {i: tuple(arc) for i, arc in enumerate(witness['edges'])}
    residuals = []
    for pair in matches(3, edges):
        remaining = {i: arc for i, arc in edges.items() if i not in pair}
        require(not matches(3, remaining), 'counterexample is not terminal')
        residuals.append({'consumed': list(pair), 'retained_vertices': 3,
                          'remaining_edges': [list(arc) for arc in remaining.values()],
                          'loops': sum(a == b for a, b in remaining.values())})
    require(len(residuals) == 2 and {r['loops'] for r in residuals} == {0, 1},
            'counterexample does not distinguish terminal structures')
    return {
        'counts': dict(totals),
        'graphs_by_nodes': {str(k): v for k, v in graphs_by_nodes.items()},
        'rules_by_length': {str(k): v for k, v in rules_by_length.items()},
        'rules_without_fresh': without_fresh,
        'rules_with_fresh': 969 - without_fresh,
        'alias_classes': [list(a) for a in sorted(alias_classes)],
        'unordered_match_pair_overlap_counts': dict(overlap),
        'named_cases_passed': len(NAMED), 'nonconfluence_witness': residuals,
    }


def audit(root=ROOT):
    prior = json.loads((root / 'reports/r04a.json').read_text())
    require(audit_r04(root) == prior, 'R04a prerequisite verification failed')
    protocol = json.loads((root / 'protocols/r05a.json').read_text())
    require(protocol['protocol_id'] == 'R05a-v1' and
            protocol['campaign_authorized'] is False and
            protocol['holdout_authorized'] is False, 'unexpected scope')
    result = static_checks(protocol)
    sources = ('protocols/r05a.json', 'docs/r05-two-edge.md', 'scripts/audit_r05.py',
               'tests/test_audit_r05.py', 'reports/r04a.json')
    result.update(protocol_id=protocol['protocol_id'], audit_status='pass',
                  scientific_status=protocol['scientific_status'],
                  production_trajectories_executed=0, holdout_jobs_executed=0,
                  evidence_scope='Finite static fixtures and an explicit local residual witness; no G2 production kernel or scientific assay.',
                  source_sha256={name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                                 for name in sources})
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output', type=Path)
    group.add_argument('--verify', type=Path)
    args = parser.parse_args()
    result = audit()
    if args.verify:
        require(json.loads(args.verify.read_text()) == result, 'R05a receipt mismatch')
        print('R05a receipt verified')
    else:
        with args.output.open('x') as stream:
            json.dump(result, stream, indent=2, sort_keys=True)
            stream.write('\n')
        print('R05a static design audit passed')
