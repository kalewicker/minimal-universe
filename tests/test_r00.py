"""Hand-derived adversarial fixtures for the R00 oracle itself."""
import sys
from pathlib import Path
import unittest

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'scripts'))
from audit_r00 import canonical, expand, leaves, rules, seed_graph, step, terms


class AuditTests(unittest.TestCase):
    def test_loop_alias_and_fresh_node(self):
        graph = seed_graph({'nodes': 1, 'edges': [[0, 0]]})
        after, parent = step(graph, ((0, 2), (2, 1), (1, 0)), 0)
        self.assertEqual(after.nodes, 2)
        self.assertEqual([(e.source, e.target) for e in after.edges],
                         [(0, 1), (1, 0), (0, 0)])
        self.assertIsNone(parent)
        child, parent = step(after, (), 1)
        self.assertEqual(parent, 0)
        self.assertEqual(child.nodes, 2)

    def test_parallel_occurrence_and_retained_isolates(self):
        graph = seed_graph({'nodes': 3, 'edges': [[0, 1], [0, 1]]})
        after, _ = step(graph, (), 0)
        self.assertEqual([e.identity for e in after.edges], [1])
        self.assertEqual(after.nodes, 3)
        with self.assertRaises(StopIteration):
            step(after, (), 0)
        self.assertEqual(len(after.edges), 1)

    def test_canonical_preserves_direction_multiplicity_isolates(self):
        def key(n, edges):
            return canonical(seed_graph({'nodes': n, 'edges': edges}))
        outward = key(3, [[0, 1], [0, 2]])
        self.assertEqual(outward, key(3, [[2, 0], [2, 1]]))
        self.assertNotEqual(outward, key(3, [[1, 0], [2, 0]]))
        self.assertNotEqual(key(2, [[0, 1]]), key(2, [[0, 1], [0, 1]]))
        self.assertNotEqual(key(2, [[0, 1]]), key(3, [[0, 1]]))
        self.assertNotEqual(key(2, [[0, 1]]), key(2, [[0, 0]]))

    def test_deleted_graph_canonical(self):
        self.assertEqual(canonical(seed_graph({'nodes': 2, 'edges': []})), (2, ()))

    def test_rule_and_catalan_counts(self):
        self.assertEqual([sum(len(r) == k for r in rules(3)) for k in range(4)],
                         [1, 9, 45, 165])
        self.assertEqual([len(terms(n)) for n in range(1, 9)],
                         [1, 1, 2, 5, 14, 42, 132, 429])

    def test_expansion_does_not_act_as_identity(self):
        self.assertEqual(leaves(expand(('i', 'i'), ())), 10)
        term = (('i', 'i'), 'i')
        self.assertEqual(leaves(expand(term, (0,))), 11)
        self.assertEqual(term, (('i', 'i'), 'i'))
        with self.assertRaises(ValueError):
            expand('i', ())


if __name__ == '__main__':
    unittest.main()
