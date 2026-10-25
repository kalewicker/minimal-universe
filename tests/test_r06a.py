from fractions import Fraction
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from design_r06a import exact_nulls, oracle_scores, paired_change, parent_mean, scores, unique_orders


class ObservableDesignTests(unittest.TestCase):
    def test_isolates_dilute_pair_density_but_not_edge_allocation(self):
        edges = [(0, 1), (1, 0)]
        self.assertEqual(scores(2, edges), (1, 1, 1, 1))
        self.assertEqual(scores(64, edges), (Fraction(1, 2016), 1, 1, 1))

    def test_parallel_and_loop_costs_are_explicit_hypothesis_choices(self):
        self.assertEqual(scores(2, [(0, 1)] * 3 + [(1, 0)]), (1, Fraction(1, 2), 1, 1))
        self.assertEqual(scores(2, [(0, 1), (1, 0), (0, 0), (0, 0)]), (1, Fraction(1, 2), 1, 1))

    def test_empty_and_aliased_denominators_remain_distinct(self):
        self.assertEqual(scores(0, []), (None, None, None, None))
        self.assertEqual(scores(2, []), (0, None, None, None))
        self.assertEqual(scores(1, [(0, 0)] * 2), (None, 0, None, None))

    def test_dropping_undefined_null_draws_would_invent_a_mean(self):
        null = exact_nulls(2, [(0, 1), (1, 0)])
        for name in ('support_fraction', 'occurrence_fraction'):
            self.assertEqual(null[name]['undefined_mass'], Fraction(1, 2))
            self.assertIsNone(null[name]['mean'])
            self.assertIsNone(null[name]['contrast'])
            self.assertEqual(null[name]['status'], 'null_contains_undefined')
        self.assertEqual(null['edge_budget']['mean'], Fraction(1, 2))
        self.assertEqual(null['edge_budget']['contrast'], Fraction(1, 2))

    def test_signed_negative_and_degenerate_controls(self):
        negative = exact_nulls(2, [(0, 0), (1, 1)])['edge_budget']
        self.assertEqual(negative['contrast'], Fraction(-1, 2))
        self.assertEqual(negative['status'], 'informative')
        degenerate = exact_nulls(1, [(0, 0)] * 2)['edge_budget']
        self.assertEqual(degenerate['mean'], 0)
        self.assertEqual(degenerate['status'], 'degenerate')

    def test_duplicate_stub_mass_is_not_uniform_over_distinct_graphs(self):
        null = exact_nulls(2, [(0, 1)] * 3 + [(1, 0)])['edge_budget']
        self.assertEqual(null['mean'], Fraction(1, 8))
        self.assertEqual(null['contrast'], Fraction(3, 8))
        self.assertEqual({r['score']: r['probability'] for r in null['distribution']},
                         {Fraction(): Fraction(3, 4), Fraction(1, 2): Fraction(1, 4)})
        self.assertEqual(len(list(unique_orders([0, 0, 1]))), 3)

    def test_independent_matrix_oracle_handles_asymmetric_multiplicity(self):
        edges = [(0, 1)] * 3 + [(1, 0), (1, 2), (2, 2)]
        actual = scores(4, edges)
        self.assertEqual(actual, oracle_scores(4, edges))
        self.assertEqual(actual[3], Fraction(4, 5))
        self.assertEqual(actual, scores(4, [(3 - a, 3 - b) for a, b in edges]))

    def test_immediate_offset_and_missing_parents_are_not_effects(self):
        self.assertEqual(paired_change([0, 0, 1, 1]), 0)
        self.assertEqual(paired_change([0, Fraction(1, 2), Fraction(1, 2), 1]), 0)
        self.assertEqual(paired_change([0, 1, 0, 0]), 1)
        self.assertIsNone(paired_change([0, None, 0, 0]))
        self.assertIsNone(parent_mean([Fraction(1), None]))
        self.assertEqual(parent_mean([Fraction(1), Fraction(-1)]), 0)

    def test_invalid_inputs_cannot_turn_into_zero_controls(self):
        for nodes, edges in [(True, []), (65, []), (1, [(0, 1)]), (2, [(True, 0)]), (2, [(0, 1)] * 65)]:
            with self.assertRaises(ValueError):
                scores(nodes, edges)
        for values in ([True, 0, 0, 0], [0, 2, 0, 0], [0, 0]):
            with self.assertRaises(ValueError):
                paired_change(values)
        with self.assertRaises(ValueError):
            exact_nulls(2, [(0, 1)] * 9)


if __name__ == '__main__':
    unittest.main()
