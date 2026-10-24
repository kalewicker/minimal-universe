"""Additional boundary checks after the registered pilot; no world execution."""
import json
from pathlib import Path
import sys
import tempfile
import unittest

sys.path.insert(0,str(Path(__file__).resolve().parents[1]/'scripts'))
from bounded_runner import run_batch


class OutputBoundaryTests(unittest.TestCase):
    def check_program(self,program,expected):
        limits=dict(workers=1,per_job_wall_seconds=2,global_wall_seconds=5,
                    per_job_output_bytes=1024,global_output_bytes=20000)
        with tempfile.TemporaryDirectory() as directory:
            output=Path(directory)/'attempt'
            result=run_batch([{'id':0}],lambda _:[sys.executable,'-c',program],limits,output)
            self.assertEqual(result['statuses'],[expected])
            self.assertLessEqual((output/'events.jsonl').stat().st_size,1024)
            self.assertEqual(result['stored_bytes'],sum(p.stat().st_size for p in output.iterdir()))
            self.assertLessEqual(result['stored_bytes'],limits['global_output_bytes'])

    def test_stdout_and_stderr_share_cap(self):
        self.check_program("import sys; sys.stdout.write('x'*600); sys.stdout.flush(); sys.stderr.write('y'*600); sys.stderr.flush()",'output_cap')

    def test_result_envelope_counts_against_job_budget(self):
        self.check_program("import json; print(json.dumps('x'*900))",'record_output_cap')


if __name__=='__main__': unittest.main()
