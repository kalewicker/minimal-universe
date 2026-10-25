import sys
from pathlib import Path
import unittest
sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from verify_r06d import branch_seed, cases, oracle


class AssayTests(unittest.TestCase):
    def test_branch_domain(self):
        parent='mu/G2-assay-cal-v1/test'
        self.assertNotEqual(branch_seed(parent,'uniform_match','target'),branch_seed(parent,'uniform_match','sham'))
        self.assertNotEqual(branch_seed(parent,'lex_first','target'),branch_seed(parent,'lex_last','target'))
        self.assertEqual(branch_seed(parent,'uniform_match','target'),branch_seed(parent,'uniform_match','target'))

    def test_allocator_not_reset(self):
        case=next(c for c in cases() if c['pre']==1)
        result=oracle(case)
        self.assertEqual(result['intervention']['first_output'],6)
        self.assertEqual(result['next_edge'],16)
        self.assertEqual(result['intervention']['prefix'],1)

    def test_prefix_descendants_inherit_group(self):
        matrix=list(cases())
        a=next(c for c in matrix if c['pre']==0)
        b=next(c for c in matrix if c['pre']==1)
        self.assertEqual(a['parent'],b['parent'])
        self.assertEqual(a['partition'],b['partition'])

    def test_terminal_retained(self):
        case=list(cases())[-1]
        result=oracle(case)
        self.assertEqual(result['status'],'no_eligible_match')
        self.assertEqual(result['edges'],[])
        self.assertEqual(len(result['events']),2)
