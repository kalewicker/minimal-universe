"""Registered parent-population design arithmetic; no graph evolution."""
import argparse
from collections import Counter
from hashlib import sha256
from itertools import permutations
import json
from pathlib import Path
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from analysis.assay_eligibility_v1 import patches
from scripts.plan_r05d import rules,rule_id,seed_facts
from analysis.measurements import partition


def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()+b'\n'
def require(ok,message):
    if not ok:raise ValueError(message)


def supplied():
    result=set()
    for perm in permutations(range(4)):
        edges=tuple(sorted(((perm[0],perm[1]),(perm[1],perm[0]),(perm[2],perm[3]),(perm[3],perm[2]))))
        result.add(edges)
    return [dict(id=f'pairing-{i}',nodes=4,edges=edges) for i,edges in enumerate(sorted(result))]


def projection(rhs,seed,events):
    n,e,k=seed['nodes'],len(seed['edges']),len(rhs)
    fresh=int(any(3 in arc for arc in rhs))
    initial_matches=seed_facts(seed)['matches']
    unavailable=not initial_matches or (k<2 and events>(e-2)//(2-k)+1)
    # Independent stepwise count-only oracle: count viability is necessary, not sufficient.
    ni,ei=n,e;count_possible=bool(initial_matches)
    for _ in range(events):
        if ei<2:count_possible=False;break
        ni+=fresh;ei+=k-2
    require(unavailable== (not count_possible),'count availability oracle')
    if unavailable:return dict(status='provably_unavailable',projection=None)
    nn=n+fresh*events;ee=e+(k-2)*events
    require((nn,ee)==(ni,ei),'count projection oracle')
    peak=max(e,ee);upper=peak*(peak-1)
    return dict(status='count_conditional',projection=dict(nodes=nn,edges=ee,
        match_upper=upper,domain_guaranteed=nn<=64 and peak<=64 and upper<=4032))


def review(p):
    engineered=supplied();require(len(engineered)==3,'three complete pairings')
    for seed in engineered:
        require(len(patches(seed['nodes'],seed['edges']))==1,'supplied admission')
    m=json.loads((ROOT/'protocols/r05b.json').read_text())['matrix']
    original=m['seeds']+m['extra_seeds'];ledger=[];counts=Counter();bounds={};splits=Counter()
    grammar=list(rules());require(len(grammar)==969,'grammar denominator')
    for mode,seeds,windows in [('supplied',engineered,[0]),('endogenous',original,p['generation_windows'])]:
        for window in windows:
            key=f'{mode}/prefix-{window}';subtotal=Counter();maxima=dict(nodes=0,edges=0,match_upper=0)
            for rhs in grammar:
                law=rule_id(rhs)
                for seed in seeds:
                    outcome=projection(rhs,seed,window+50)
                    status=outcome['status']
                    if status=='count_conditional':
                        status += '_domain_guaranteed' if outcome['projection']['domain_guaranteed'] else '_domain_not_guaranteed'
                        for field in maxima:maxima[field]=max(maxima[field],outcome['projection'][field])
                    subtotal[status]+=1
                    parent=f"mu/G2-parent-design-v1/{mode}/law/{law}/seed/{seed['id']}"
                    split=partition(parent);splits[f'{key}/{split}']+=1
                    ledger.append(dict(population=mode,generation_window=window,law=law,seed=seed['id'],
                        parent=parent,partition=split,status=status,counts=outcome['projection'],
                        patch_admission='guaranteed_by_construction' if mode=='supplied' else 'unmeasured_after_generation',
                        executed=False))
            counts[key]=dict(subtotal);bounds[key]=maxima
    require(len(ledger)==p['expected_design_rows'],'design denominator')
    supplied_counts=counts['supplied/prefix-0']
    require(supplied_counts==p['expected_supplied_counts'],'supplied arithmetic')
    return ledger,dict(protocol_id=p['protocol_id'],engineered_seeds=engineered,design_rows=len(ledger),
        counts=dict(counts),conditional_maxima=bounds,partition_group_counts=dict(splits),
        supplied_parent_groups=2907,supplied_parent_scheduler_rows=8721,supplied_orientation_slots=34884,
        supplied_conditional_event_targets=1744200,supplied_edge_budget_unavailable_orientation_slots=612,
        supplied_complete_panel_gate='provably_impossible_at_50_events',
        recommendation='separately_register_supplied_state_engineering_completion_calibration',
        parent_population_adopted=False,scientific_status='untested',world_transitions=0,null_draws=0,
        engineering_status='passed',ledger_sha256=sha256(canonical(ledger)).hexdigest())


def main():
    parser=argparse.ArgumentParser();g=parser.add_mutually_exclusive_group(required=True)
    g.add_argument('--output',type=Path);g.add_argument('--verify',type=Path);a=parser.parse_args()
    path=ROOT/'protocols/r06f.json';p=json.loads(path.read_text())
    for name,digest in p['pins_sha256'].items():
        require(sha256((ROOT/name).read_bytes()).hexdigest()==digest,'source pin '+name)
    for name in ('protocols/r06e.json','protocols/r06d.json','protocols/r06c.json'):
        for source,digest in json.loads((ROOT/name).read_text())['pins_sha256'].items():
            require(sha256((ROOT/source).read_bytes()).hexdigest()==digest,'prior pin '+source)
    start=time.monotonic()
    if a.output:
        a.output.mkdir(parents=True,exist_ok=False)
        (a.output/'started.json').write_bytes(canonical(dict(protocol_sha256=sha256(path.read_bytes()).hexdigest())))
    try:
        ledger,receipt=review(p);receipt['protocol_sha256']=sha256(path.read_bytes()).hexdigest()
        if a.verify:require(json.loads(a.verify.read_text())==json.loads(canonical(receipt)),'receipt replay')
        else:
            (a.output/'ledger.json').write_bytes(canonical(ledger));(a.output/'receipt.json').write_bytes(canonical(receipt))
            elapsed=time.monotonic()-start;size=sum(f.stat().st_size for f in a.output.iterdir())
            require(elapsed<=p['budgets']['wall_seconds'],'wall budget')
            require(size+4096<=p['budgets']['retained_bytes'],'storage budget')
            (a.output/'execution.json').write_bytes(canonical(dict(status='passed',wall_seconds=elapsed,retained_bytes_before_execution=size)))
        print(json.dumps(receipt,sort_keys=True))
    except Exception as exc:
        if a.output:(a.output/'failure.json').write_bytes(canonical(dict(status='failed',error=str(exc))))
        raise
if __name__=='__main__':main()
