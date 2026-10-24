from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from bounded_runner import run_batch,summary_reservation
from observe_r03 import observe


class RunnerTests(unittest.TestCase):
    def test_reserved_never_calls_factory(self):
        def forbidden(_): raise AssertionError('reserved dispatched')
        limits=dict(workers=1,per_job_wall_seconds=1,global_wall_seconds=1,
                    global_output_bytes=20000,per_job_output_bytes=4096)
        with tempfile.TemporaryDirectory() as directory:
            result=run_batch([{'reserved':True}],forbidden,limits,Path(directory)/'attempt')
            self.assertEqual(result['statuses'],['reserved'])
            self.assertEqual(result['ledger_bytes'],0)
            self.assertEqual(result['stored_bytes'],sum(p.stat().st_size for p in (Path(directory)/'attempt').iterdir()))

    def test_accounting_budget_checked_before_directory_creation(self):
        limits=dict(workers=1,per_job_wall_seconds=1,global_wall_seconds=1,
                    global_output_bytes=1,per_job_output_bytes=4096)
        with tempfile.TemporaryDirectory() as directory:
            target=Path(directory)/'attempt'
            with self.assertRaises(ValueError): run_batch([{}],None,limits,target)
            self.assertFalse(target.exists())
        self.assertGreater(summary_reservation(100),summary_reservation(1))

    def test_observer_rejects_bad_native_trace(self):
        fixture={'nodes':1,'edges':[[0,0]]}
        native={'events':[[0,99,0,0,None,None,1,0,0]],'edges':[],'nodes':1,'next_edge':1}
        with self.assertRaises(ValueError): observe(native,fixture,[],[0,1,2])


if __name__=='__main__': unittest.main()
