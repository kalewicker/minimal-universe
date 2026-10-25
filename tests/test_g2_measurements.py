from copy import deepcopy
from fractions import Fraction
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / 'scripts'))
from analysis import g2_measurements as measurement
from calibrate_r05c import paired_fixture


class G2MeasurementTests(unittest.TestCase):
    def test_exposure_is_union_over_matches(self):
        result = measurement.exposure(3, [(0, 0, 1), (1, 1, 2), (2, 1, 2), (3, 2, 0)], [0, 3])
        self.assertEqual(result['matches'], 5)
        self.assertEqual(result['occurrence_match_counts'], {0: 3, 1: 2, 2: 2, 3: 3})
        self.assertEqual(result['target_union_matches'], 5)
        self.assertEqual(result['probability_avoid'], 0)

    def test_empty_eligibility_has_no_one_event_probability(self):
        self.assertIsNone(measurement.exposure(1, [(7, 0, 0)], [])['probability_avoid'])
        self.assertEqual(measurement.exposure(1, [(7, 0, 0), (9, 0, 0)], [7])['probability_avoid'], 0)

    def test_partial_horizon_keeps_joint_and_conditional_denominators(self):
        edges = [(0, 0, 0), (1, 0, 1), (2, 1, 1), (3, 2, 2)]
        result = measurement.survival(measurement.exact_horizon(3, edges, [(0, 0)], 2), [3])
        self.assertEqual(result['reached_mass'], Fraction(1, 2))
        self.assertEqual(result['surviving_reached_mass'], Fraction(1, 2))
        self.assertEqual(result['unavailable_mass'], Fraction(1, 2))
        self.assertEqual(result['conditional_survival'], 1)
        later = measurement.survival(measurement.exact_horizon(3, edges, [(0, 0)], 3), [3])
        self.assertIsNone(later['conditional_survival'])
        self.assertEqual(later['terminal_mass_by_event'], [0, Fraction(1, 2), Fraction(1, 2)])

    def test_isomorphic_regeneration_does_not_preserve_identity(self):
        dist = measurement.exact_horizon(1, [(0, 0, 0), (1, 0, 0)], [(0, 0), (0, 0)], 1)
        result = measurement.survival(dist, [0])
        self.assertEqual(result['reached_mass'], 1)
        self.assertEqual(result['surviving_reached_mass'], 0)

    def test_sparse_occurrence_ids_never_reused(self):
        dist = measurement.exact_horizon(1, [(7, 0, 0), (99, 0, 0)], [(0, 0)] * 3, 1)
        self.assertEqual(len(dist.states), 1)
        (_, edges, next_id), = dist.states
        self.assertEqual([edge[0] for edge in edges], [100, 101, 102])
        self.assertEqual(next_id, 103)

    def test_consumption_before_termination_does_not_invent_later_endpoint(self):
        edges = [(0, 0, 0), (1, 0, 0)]
        first = measurement.survival(measurement.exact_horizon(1, edges, [], 1), [0])
        later = measurement.survival(measurement.exact_horizon(1, edges, [], 2), [0])
        self.assertEqual(first['conditional_survival'], 0)
        self.assertEqual(later['unavailable_mass'], 1)
        self.assertIsNone(later['conditional_survival'])

    def test_horizon_zero_is_reached_even_for_empty_state(self):
        self.assertEqual(measurement.survival(measurement.exact_horizon(0, [], [], 0), [])['reached_mass'], 1)
        self.assertEqual(measurement.survival(measurement.exact_horizon(0, [], [], 1), [])['unavailable_mass'], 1)

    def test_invalid_occurrences_targets_and_domains_rejected(self):
        for nodes, edges, target in ((1, [(0, 0, 0), (0, 0, 0)], []),
                                     (1, [(True, 0, 0)], []), (1, [(0, 0, 1)], []),
                                     (1, [(7, 0, 0)], [7, 7]), (1, [(7, 0, 0)], [8])):
            with self.subTest(edges=edges, targets=target):
                with self.assertRaises(ValueError):
                    measurement.exposure(nodes, edges, target)
        with self.assertRaises(ValueError):
            measurement.exact_horizon(8, [(0, 0, 0), (1, 0, 0)], [(0, 3)], 1)
        with self.assertRaises(ValueError):
            measurement.exact_horizon(1, [], [], 4)
        with self.assertRaises(ValueError):
            measurement.exact_horizon(1, [], [(3, 0), (0, 0)], 1)
        with patch.object(measurement, 'MAX_FRONTIER', 0):
            with self.assertRaisesRegex(ValueError, 'frontier domain'):
                measurement.exact_horizon(1, [(0, 0, 0), (1, 0, 0)], [], 1)

    def test_unavailable_pair_is_preserved_and_prevents_mean(self):
        complete, unavailable = paired_fixture('complete'), paired_fixture('unavailable')
        unavailable['target'].update(status='resource_censored', density_h=None, matches_h=None)
        result = measurement.paired_bookkeeping([complete, unavailable], 3)
        self.assertEqual((result['total_pairs'], result['complete_pairs'], result['unavailable_pairs']), (2, 1, 1))
        self.assertIsNone(result['mean_effect'])
        self.assertEqual(result['pairs'][1]['unavailable_reasons'], ['target:resource_censored'])

    def test_eligibility_changes_do_not_certify_sham(self):
        row = paired_fixture()
        row['target'].update(density_h=Fraction(1, 2), matches_0=7, matches_h=0)
        saved = deepcopy(row)
        result = measurement.paired_bookkeeping([row], 3)
        self.assertEqual(result['mean_effect'], Fraction(1, 4))
        self.assertTrue(result['pairs'][0]['initial_eligibility_changed'])
        self.assertTrue(result['pairs'][0]['endpoint_eligibility_changed'])
        self.assertEqual(result['sham_validity'], 'not_established')
        self.assertFalse(result['scientific_acceptance'])
        self.assertEqual(row, saved)

    def test_malformed_paired_records_fail_closed(self):
        for key, value in (('density_h', True), ('density_h', .25), ('matches_h', None),
                           ('horizon', True), ('scheduler', 'uniform'), ('partition', 'forged'),
                           ('parent', 'mu/G2-cal-v1/other'), ('status', 'unknown')):
            row = paired_fixture()
            row['target'][key] = value
            with self.subTest(key=key, value=value):
                with self.assertRaises(ValueError):
                    measurement.paired_bookkeeping([row], 3)
        row = paired_fixture()
        with self.assertRaises(ValueError):
            measurement.paired_bookkeeping([row, deepcopy(row)], 3)


if __name__ == '__main__':
    unittest.main()
