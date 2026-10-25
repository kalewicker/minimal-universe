"""Registered time-zero admission gate; never evolves a graph."""
import argparse
from collections import Counter
from hashlib import sha256
from itertools import combinations_with_replacement, permutations, product
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from analysis.assay_eligibility_v1 import patches
from analysis.measurements import partition
from plan_r05d import rules,rule_id


def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()+b'\n'
def require(ok,message):
    if not ok:raise ValueError(message)


def oracle(nodes,edges):
    # Exhaust every ordered four-vertex assignment; direct arc-list comparison.
    result=set()
    for a,b,c,d in permutations(range(nodes),4):
        vertices=(a,b,c,d)
        actual=sorted(tuple(e) for e in edges if e[0] in vertices and e[1] in vertices)
        expected=sorted(((a,b),(b,a),(c,d),(d,c)))
        if actual==expected:
            dyads=sorted((tuple(sorted((a,b))),tuple(sorted((c,d)))))
            result.add(dyads[0]+dyads[1])
    return sorted(result)


def controls():
    arcs=list(product(range(4),repeat=2))
    for count in range(5):
        for edges in combinations_with_replacement(arcs,count):yield 4,edges
    external=[(v,4) for v in range(4)]+[(4,v) for v in range(4)]+[(4,4)]
    for count in range(4):
        for context in combinations_with_replacement(external,count):
            yield 5,((0,1),(1,0),(2,3),(3,2))+context


def audit(protocol):
    matrix=json.loads((ROOT/'protocols/r05b.json').read_text())['matrix']
    seeds=matrix['seeds']+matrix['extra_seeds']
    control_count=eligible_controls=0
    digest=sha256()
    for nodes,edges in controls():
        actual=patches(nodes,edges); expected=oracle(nodes,edges)
        require(actual==expected,'detector control mismatch')
        control_count+=1;eligible_controls+=bool(actual)
        digest.update(canonical(dict(nodes=nodes,edges=edges,patches=actual)))
    require(control_count==protocol['expected_control_graphs'],'control denominator')
    require(eligible_controls==protocol['expected_eligible_controls'],'control positives')
    seed_rows=[]
    for seed in seeds:
        actual=patches(seed['nodes'],seed['edges'])
        require(actual==oracle(seed['nodes'],seed['edges']),'seed oracle mismatch')
        seed_rows.append(dict(seed_id=seed['id'],nodes=seed['nodes'],edges=len(seed['edges']),
            patches=actual,status='eligible' if actual else 'unavailable_no_induced_dyads_at_time_zero'))
    rows=[];groups=set();splits=Counter();eligible=0
    for rhs in rules():
        law=rule_id(rhs)
        for seed in seed_rows:
            parent=f"mu/G2-admission-cal-v1/law/{law}/seed/{seed['seed_id']}"
            groups.add(parent);split=partition(parent)
            for scheduler in protocol['schedulers']:
                row=dict(parent=parent,partition=split,scheduler=scheduler,seed_id=seed['seed_id'],
                    law=law,status=seed['status'],patches=seed['patches'],parent_prefix=0,
                    requested_branch_horizon=50,branch_slots=4,branch_execution='not_started')
                rows.append(row);splits[split]+=1;eligible+=bool(seed['patches'])
    require(len(rows)==protocol['expected_parent_scheduler_rows'],'panel denominator')
    require(len(groups)==protocol['expected_parent_groups'],'group denominator')
    # This stage is admission only even if a future matrix has eligible states.
    return rows,dict(protocol_id=protocol['protocol_id'],engineering_status='passed',
        control_graphs=control_count,eligible_control_graphs=eligible_controls,control_sha256=digest.hexdigest(),
        seed_admission=seed_rows,parent_groups=len(groups),parent_scheduler_rows=len(rows),
        eligible_parent_scheduler_rows=eligible,unavailable_parent_scheduler_rows=len(rows)-eligible,
        planned_orientation_slots=4*len(rows),executed_orientation_slots=0,not_started_orientation_slots=4*len(rows),
        partition_parent_scheduler_counts=dict(splits),
        admission_gate='passed' if eligible==len(rows) else 'failed',
        calibration_launch='not_authorized_by_admission_review',world_transitions=0,null_draws=0,
        measured_assay_runtime=None,measured_assay_storage=None,completion_fraction=None,
        scientific_status='untested',production_adopted=False,ledger_sha256=sha256(canonical(rows)).hexdigest())


def main():
    p=argparse.ArgumentParser();g=p.add_mutually_exclusive_group(required=True)
    g.add_argument('--output',type=Path);g.add_argument('--verify',type=Path);a=p.parse_args()
    path=ROOT/'protocols/r06e.json';protocol=json.loads(path.read_text())
    for name,digest in protocol['pins_sha256'].items():
        require(sha256((ROOT/name).read_bytes()).hexdigest()==digest,'pin '+name)
    for name in ('protocols/r06d.json','protocols/r06c.json'):
        for source,digest in json.loads((ROOT/name).read_text())['pins_sha256'].items():
            require(sha256((ROOT/source).read_bytes()).hexdigest()==digest,'prior pin '+source)
    start=time.monotonic()
    if a.output:
        a.output.mkdir(parents=True,exist_ok=False)
        (a.output/'started.json').write_bytes(canonical(dict(protocol_sha256=sha256(path.read_bytes()).hexdigest())))
    try:
        rows,receipt=audit(protocol);receipt['protocol_sha256']=sha256(path.read_bytes()).hexdigest()
        if a.verify:require(json.loads(a.verify.read_text())==receipt,'receipt mismatch')
        else:
            (a.output/'ledger.json').write_bytes(canonical(rows))
            (a.output/'receipt.json').write_bytes(canonical(receipt))
            elapsed=time.monotonic()-start;size=sum(f.stat().st_size for f in a.output.iterdir())
            require(elapsed<=protocol['budgets']['wall_seconds'],'wall budget')
            require(size+4096<=protocol['budgets']['retained_bytes'],'storage budget')
            (a.output/'execution.json').write_bytes(canonical(dict(status='passed',wall_seconds=elapsed,
                retained_bytes_before_execution=size,scope='static_admission_only')))
        print(json.dumps({k:v for k,v in receipt.items() if k!='seed_admission'},sort_keys=True))
    except Exception as exc:
        if a.output:(a.output/'failure.json').write_bytes(canonical(dict(status='failed',error=str(exc))))
        raise
if __name__=='__main__':main()
