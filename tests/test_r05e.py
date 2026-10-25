from fractions import Fraction
from itertools import product
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from audit_r05e import certified_radius, oracle_radius, density_ceiling, independent_ceiling, shuffle_choices


class ObserverDesignTests(unittest.TestCase):
    def test_certified_radius_exact_grid_boundary(self):
        level, radius = certified_radius(16384, 1)
        self.assertEqual(level, 8)
        self.assertEqual(radius, Fraction(1, 64))

    def test_larger_family_has_wider_radius_and_more_draws_narrower(self):
        self.assertLess(certified_radius(16384, 1)[1], certified_radius(16384, 1000000)[1])
        self.assertLess(certified_radius(65536, 1)[1], certified_radius(4096, 1)[1])

    def test_radius_rounds_up_and_is_smallest_certified_grid_value(self):
        for draws, quota in product((1, 4096, 16384, 65536), (1, 56, 1000, 1000000)):
            level, radius = certified_radius(draws, quota)
            square = Fraction(level, 2 * draws)
            self.assertGreaterEqual(radius * radius, square)
            self.assertLess((radius - Fraction(1, 1000000)) ** 2, square)
            self.assertEqual((level, radius), oracle_radius(draws, quota, Fraction(1, 100), 1000000))

    def test_bad_precision_parameters_rejected(self):
        for draws, quota, delta in ((0, 1, Fraction(1, 100)), (True, 1, Fraction(1, 100)),
                                    (1, 0, Fraction(1, 100)), (1, 1, Fraction()),
                                    (1, 1, Fraction(1)), (1, 1, .01)):
            with self.assertRaises(ValueError):
                certified_radius(draws, quota, delta)

    def test_reciprocal_pairs_need_two_distinct_direction_occurrences(self):
        self.assertEqual(density_ceiling(3, 1), 0)
        self.assertEqual(density_ceiling(3, 2), Fraction(1, 3))
        self.assertEqual(density_ceiling(3, 100), 1)
        self.assertIsNone(density_ceiling(1, 100))

    def test_growth_ceiling_is_below_frozen_threshold(self):
        self.assertLess(density_ceiling(51, 54), Fraction(1, 20))
        self.assertEqual(density_ceiling(56, 54), Fraction(27, 1540))

    def test_threshold_equality_is_not_classified_as_strictly_below(self):
        self.assertEqual(density_ceiling(16, 12), Fraction(1, 20))
        self.assertLess(density_ceiling(16, 11), Fraction(1, 20))

    def test_independent_pair_budget_matches_boundary_sizes(self):
        for nodes in (0, 1, 2, 3, 16, 51, 56, 64):
            for edges in (0, 1, 2, 11, 12, 54, 64):
                self.assertEqual(density_ceiling(nodes, edges), independent_ceiling(nodes, edges))

    def test_static_shuffle_control_preserves_roles_and_identity(self):
        self.assertEqual(shuffle_choices(0, ()), ())
        self.assertEqual(shuffle_choices(1, ()), (0,))
        self.assertEqual(shuffle_choices(3, (2, 1)), (0, 1, 2))
        self.assertEqual(shuffle_choices(3, (0, 0)), (1, 2, 0))
        seen = {shuffle_choices(3, choices) for choices in product(range(3), range(2))}
        self.assertEqual(len(seen), 6)

    def test_invalid_shuffle_choices_rejected(self):
        for length, choices in ((3, (3, 0)), (3, (1,)), (2, (True,)), (9, tuple(range(8)))):
            with self.assertRaises(ValueError):
                shuffle_choices(length, choices)


if __name__ == '__main__':
    unittest.main()
