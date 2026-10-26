import unittest
from scripts.design_r06f import projection,supplied


class PopulationDesignTests(unittest.TestCase):
    def test_all_pairings(self):
        panel=supplied()
        self.assertEqual(len(panel),3)
        self.assertEqual(len({s['edges'] for s in panel}),3)

    def test_shrinking_laws_cannot_complete(self):
        seed=supplied()[0]
        self.assertEqual(projection([],seed,50)['status'],'provably_unavailable')
        self.assertEqual(projection([(0,1)],seed,50)['status'],'provably_unavailable')

    def test_count_possible_is_not_reachability(self):
        result=projection([(0,0),(0,0)],supplied()[0],50)
        self.assertEqual(result['status'],'count_conditional')

    def test_long_generation_exceeds_observer(self):
        rhs=[(0,3),(1,3),(3,2)]
        self.assertTrue(projection(rhs,supplied()[0],50)['projection']['domain_guaranteed'])
        self.assertFalse(projection(rhs,supplied()[0],100)['projection']['domain_guaranteed'])
