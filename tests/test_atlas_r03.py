from copy import deepcopy
import json
from pathlib import Path
import sys
import tempfile
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
from atlas_r03 import validate_worker_row,rules,verify_bound_receipt
from plan_r03 import rows


class AtlasAdapterTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.design=json.loads((ROOT/'protocols/r03b-design.json').read_text())
        cls.seeds=json.loads((ROOT/'protocols/r00.json').read_text())['seeds']
        cls.discovery=None;cls.reserved=None
        for row in rows(cls.design,cls.seeds):
            row=json.loads(json.dumps(row))
            if row['partition']=='discovery': cls.discovery=row
            else: cls.reserved=row
            if cls.discovery and cls.reserved: break

    def test_discovery_validates_without_world_execution(self):
        self.assertEqual(validate_worker_row(self.discovery,self.design,self.seeds),self.seeds[self.discovery['seed_id']])
        self.assertEqual(len(rules()),220)

    def test_reserved_and_partition_forgery_rejected(self):
        with self.assertRaises(ValueError): validate_worker_row(self.reserved,self.design,self.seeds)
        with self.assertRaises(ValueError): validate_worker_row(self.reserved|{'partition':'discovery'},self.design,self.seeds)

    def test_rng_and_rule_tampering_rejected(self):
        with self.assertRaises(ValueError): validate_worker_row(self.discovery|{'rng_seed':-1},self.design,self.seeds)
        changed=deepcopy(self.discovery);changed['rhs']=[[2,2]]*4
        with self.assertRaises(ValueError): validate_worker_row(changed,self.design,self.seeds)

    def test_failed_prerequisite_cannot_launch(self):
        with tempfile.TemporaryDirectory() as directory:
            path=Path(directory)/'receipt.json'
            path.write_text('{"status":"fail"}')
            with self.assertRaises(ValueError): verify_bound_receipt(path)


if __name__=='__main__': unittest.main()
