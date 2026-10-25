from copy import deepcopy
import json
from pathlib import Path
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'scripts'))
from plan_r05d import project, seed_facts
from verify_r05d import arithmetic_profiles, preflight


class G2FeasibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.protocol = json.loads((ROOT / 'protocols/r05d.json').read_text())
        engineering = json.loads((ROOT / 'protocols/r05b.json').read_text())['matrix']
        cls.seeds = {s['id']: s for s in engineering['seeds'] + engineering['extra_seeds']}

    def test_horizon_zero_is_an_initial_observation(self):
        row = project([], self.seeds['empty'], 0, self.protocol)
        self.assertEqual(row['availability'], 'initial_state')
        self.assertEqual(row['projection']['endpoint_edges'], 0)
        self.assertFalse(row['projection']['endpoint_density_defined'])

    def test_nonempty_seed_can_have_no_first_match(self):
        row = project([(0, 3)] * 3, self.seeds['parallel_nonloops'], 1, self.protocol)
        self.assertEqual(row['availability'], 'provably_unavailable_no_initial_match')
        self.assertIsNone(row['projection'])

    def test_deletion_event_ceiling_has_no_negative_state_projection(self):
        seed = self.seeds['four_loops']
        endpoint = project([], seed, 2, self.protocol)
        self.assertEqual(endpoint['successful_event_upper_bound'], 2)
        self.assertEqual(endpoint['projection']['endpoint_edges'], 0)
        self.assertEqual(endpoint['availability'], 'not_established_by_static_sizes')
        unavailable = project([], seed, 3, self.protocol)
        self.assertEqual(unavailable['availability'], 'provably_unavailable_edge_budget')
        self.assertIsNone(unavailable['projection'])

    def test_single_output_requires_two_edges_before_last_event(self):
        seed = self.seeds['four_loops']
        self.assertEqual(project([(0, 0)], seed, 3, self.protocol)['projection']['endpoint_edges'], 1)
        self.assertIsNone(project([(0, 0)], seed, 4, self.protocol)['projection'])

    def test_constant_size_does_not_establish_horizon_reachability(self):
        row = project([(0, 1), (1, 2)], self.seeds['distinct'], 50, self.protocol)
        self.assertEqual(row['availability'], 'not_established_by_static_sizes')
        self.assertEqual(row['projection']['endpoint_edges'], 2)
        self.assertTrue(row['projection']['local_exposure_domain'])
        self.assertEqual(row['projection']['exact_survival_domain'], 'outside_size_or_horizon_domain')

    def test_kernel_support_is_separate_from_measurement_support(self):
        row = project([(0, 3), (2, 3), (3, 1)], self.seeds['disjoint'], 50, self.protocol)['projection']
        self.assertEqual((row['endpoint_nodes'], row['endpoint_edges']), (56, 54))
        self.assertTrue(row['kernel_count_caps_fit'])
        self.assertTrue(row['kernel_match_cap_guaranteed'])
        self.assertTrue(row['observer_node_domain'])
        self.assertFalse(row['degree_null_edge_domain'])
        self.assertFalse(row['local_exposure_domain'])

    def test_exact_frontier_uses_sufficient_labelled_history_bound(self):
        row = project([(0, 0)] * 3, self.seeds['four_loops'], 3, self.protocol)['projection']
        self.assertEqual(row['frontier_history_upper_bound'], 12 * 20 * 30)
        self.assertEqual(row['exact_survival_domain'], 'guaranteed_by_count_bound')

    def test_initial_motif_exclusion_is_preserved(self):
        self.assertFalse(seed_facts(self.seeds['four_loops'])['motif_coverage_complete'])
        row = project([(0, 0), (0, 0)], self.seeds['four_loops'], 50, self.protocol)['projection']
        self.assertEqual(row['motif_coverage'], 'known_incomplete_at_initial_state')

    def test_incremental_oracle_matches_boundaries_for_all_reviewed_horizons(self):
        for rhs in ([], [(0, 3)], [(0, 0), (0, 0)], [(0, 3), (2, 3), (3, 1)]):
            for name in ('empty', 'parallel_nonloops', 'four_loops', 'disjoint'):
                seed = self.seeds[name]
                for horizon, expected in enumerate(arithmetic_profiles(rhs, seed, self.protocol)):
                    self.assertEqual(project(rhs, seed, horizon, self.protocol), expected)

    def test_changed_domain_rejected_against_frozen_prerequisite(self):
        protocol = deepcopy(self.protocol)
        protocol['g2_measurement_domain']['exact_horizon'] = 50
        with self.assertRaisesRegex(ValueError, 'G2 measurement domain'):
            preflight(protocol)


if __name__ == '__main__':
    unittest.main()
