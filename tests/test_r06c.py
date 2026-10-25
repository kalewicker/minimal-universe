import unittest
from fractions import Fraction as F
from scripts.design_r06c import matches, planning, signature


class DesignTests(unittest.TestCase):
    def test_loop_occurrence_correction(self):
        self.assertEqual(matches([(0,0),(0,0),(0,1)]), (4,[3,3,2]))

    def test_degree_matched_loops_fail_sham(self):
        a, b = signature([(0,1),(1,0)]), signature([(0,0),(1,1)])
        self.assertEqual(a[:2], b[:2])
        self.assertNotEqual(a, b)

    def test_raw_primary_has_no_null_bill(self):
        row = planning(F(1,20),1,0)
        self.assertEqual(row['parents_per_test'],64000)
        self.assertEqual(row['conditional_branch_event_targets'],6400000)
        self.assertEqual(row['draw_upper_bound'],0)
        self.assertIsNone(row['mc_radius'])

    def test_full_family_work(self):
        row = planning(F(1,20),2907,4)
        self.assertEqual(row['parents_per_test'],204800)
        self.assertEqual(row['query_quota'],4*204800*2907)
        self.assertGreater(row['mc_radius'],F(11719,500000))
