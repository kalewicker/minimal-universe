import unittest
from scripts.calibrate_r06g import cases,oracle,compact,summary


class CompletionTests(unittest.TestCase):
    def test_all_pairings_have_mapped_patch(self):
        batch=list(cases([],0))
        self.assertEqual(len(batch),36)
        self.assertEqual({tuple(c['patch']) for c in batch},{(0,1,2,3),(0,2,1,3),(0,3,1,2)})
        for case in batch:
            row=compact(case,oracle(case))
            self.assertEqual(row['events'],2)
            self.assertTrue(row['endpoint_empty'])
            self.assertFalse(row['reached_50'])

    def test_censoring_keeps_denominator(self):
        case=next(cases([],0));row=compact(case,oracle(case))
        result=summary([row,{'execution':'censored_batch_failure'}],36)
        self.assertEqual((result['executed_slots'],result['censored_slots'],result['not_started_slots']),(1,1,34))

    def test_terminal_at_horizon_counts_as_reached(self):
        case=next(cases([],0));result=oracle(case);result['events']=[{}]*50
        self.assertTrue(compact(case,result)['reached_50'])

    def test_branch_and_partition_identity(self):
        batch=list(cases([],0));first=batch[:4]
        self.assertEqual(len({c['parent'] for c in first}),1)
        self.assertEqual(len({c['partition'] for c in first}),1)
        self.assertEqual(len({c['branch_seed'] for c in first}),2)
