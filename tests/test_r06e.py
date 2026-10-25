import unittest
from analysis.assay_eligibility_v1 import patches


class AdmissionTests(unittest.TestCase):
    def test_external_context_allowed(self):
        edges=[(0,1),(1,0),(2,3),(3,2),(0,4),(4,0),(4,4)]
        self.assertEqual(patches(5,edges),[(0,1,2,3)])

    def test_internal_nuisance_rejected(self):
        base=[(0,1),(1,0),(2,3),(3,2)]
        for nuisance in ((0,1),(0,0),(0,2)):
            self.assertEqual(patches(4,base+[nuisance]),[])

    def test_alternate_pairing_and_multiple_patches(self):
        self.assertEqual(patches(4,[(0,2),(2,0),(1,3),(3,1)]),[(0,2,1,3)])
        edges=[(0,1),(1,0),(2,3),(3,2),(4,5),(5,4)]
        self.assertEqual(len(patches(6,edges)),3)

    def test_invalid_inputs(self):
        for nodes,edges in [(True,[]),(65,[]),(2,[(0,2)]),(2,[(False,1)]),(2,[(0,1,1)])]:
            with self.assertRaises(ValueError):patches(nodes,edges)

    def test_unavailable_is_not_observed_zero(self):
        self.assertEqual(patches(0,[]),[])
        self.assertEqual(patches(4,[(0,1),(1,0)]),[])
