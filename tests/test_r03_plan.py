from copy import deepcopy
from itertools import islice
import json
from pathlib import Path
import sys
import unittest

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
import plan_r03 as p
import verify_r03_plan as v


class StaticPlanTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.design=json.loads((ROOT/'protocols/r03b-design.json').read_text())
        cls.seeds=json.loads((ROOT/'protocols/r00.json').read_text())['seeds']
        cls.rules=v.catalog()

    def test_independent_grammar_and_horizon(self):
        self.assertEqual(len(self.rules),220)
        self.assertEqual([sum(len(r)==k for r in self.rules) for k in range(4)],[1,9,45,165])
        self.assertEqual(p.projection(3,4,3,True,2)['edges'],8)
        self.assertEqual(p.projection(3,4,3,True,3)['edges'],10)
        self.assertEqual(p.projection(1,1,0,False,2),
                         dict(events=1,nodes=1,edges=0,horizon_reachable=False))

    def test_scheduler_siblings_share_parent_and_split(self):
        children=list(islice(p.rows(self.design,self.seeds),3))
        self.assertEqual({row['scheduler'] for row in children},{'oldest','newest','uniform'})
        self.assertEqual(len({row['parent_key'] for row in children}),1)
        self.assertEqual(len({row['partition'] for row in children}),1)
        for row in children:
            # Round trip to the on-disk JSON representation.
            v.inspect_row(json.loads(json.dumps(row)),self.rules,self.seeds,self.design)

    def test_tampering_rejected(self):
        row=json.loads(json.dumps(next(p.rows(self.design,self.seeds))))
        mutations=[('execution_status','complete'),('partition','invalid'),('rng_seed',0),
                   ('rule_id','0'*64),('raw_null_permutation_bound',999),('replicate',-1)]
        for field,value in mutations:
            changed=deepcopy(row);changed[field]=value
            with self.assertRaises(ValueError,msg=field):
                v.inspect_row(changed,self.rules,self.seeds,self.design)
        changed=deepcopy(row);changed['projected_snapshots'][-1]['edges']=99
        with self.assertRaises(ValueError):
            v.inspect_row(changed,self.rules,self.seeds,self.design)


if __name__=='__main__':
    unittest.main()
