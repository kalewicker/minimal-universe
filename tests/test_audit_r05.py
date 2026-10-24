import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audit_r05 import alias_class, degree_count, matches, static_checks


class TwoEdgeDesignTests(unittest.TestCase):
    def test_one_loop_cannot_consume_itself(self):
        self.assertEqual(matches(1, {7: (0, 0)}), ())
        self.assertEqual(degree_count(1, {7: (0, 0)}), 0)

    def test_parallel_occurrences_and_roles_are_preserved(self):
        edges = {8: (0, 0), 3: (0, 0)}
        self.assertEqual(matches(1, edges), ((3, 8), (8, 3)))
        self.assertEqual(matches(2, {8: (0, 1), 3: (0, 1)}), ())

    def test_match_weighting_differs_from_first_edge_weighting(self):
        edges = {0: (0, 1), 1: (1, 2), 2: (1, 2), 3: (2, 0)}
        self.assertEqual(matches(3, edges), ((0, 1), (0, 2), (1, 3), (2, 3), (3, 0)))
        # Uniform-match probability that the first role is edge 0 is 2/5.
        # Uniform first-role selection among four eligible edges would give 1/4.
        self.assertEqual(degree_count(3, edges), 5)

    def test_retained_isolates_do_not_add_matches(self):
        edges = {2: (0, 1), 6: (1, 2)}
        self.assertEqual(matches(3, edges), matches(9, edges))
        self.assertEqual(alias_class((9, 4, 9)), (0, 1, 0))

    def test_invalid_endpoints_and_ids_rejected(self):
        for nodes, edges in ((-1, {}), (0, {0: (0, 0)}),
                             (2, {0: (0, 2)}), (1, {-1: (0, 0)}),
                             (1, {True: (0, 0)}), (1, {0: (False, 0)})):
            with self.subTest(nodes=nodes, edges=edges):
                with self.assertRaises(ValueError):
                    matches(nodes, edges)

    def test_overlapping_matches_have_distinct_terminal_residuals(self):
        edges = {0: (0, 0), 1: (0, 1), 2: (1, 2)}
        pairs = matches(3, edges)
        self.assertEqual(pairs, ((0, 1), (1, 2)))
        left = {2: edges[2]}
        right = {0: edges[0]}
        self.assertFalse(matches(3, left))
        self.assertFalse(matches(3, right))
        self.assertNotEqual(sum(a == b for a, b in left.values()),
                            sum(a == b for a, b in right.values()))

    def test_changed_registered_counts_fail_closed(self):
        protocol = json.loads((ROOT / 'protocols/r05a.json').read_text())
        protocol['expected_rules'] -= 1
        with self.assertRaisesRegex(ValueError, 'registered rule census'):
            static_checks(protocol)


if __name__ == '__main__':
    unittest.main()
