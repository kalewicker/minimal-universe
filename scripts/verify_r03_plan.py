#!/usr/bin/env python3
"""Independent static manifest audit; no imports from the planner or simulator."""
import argparse
from collections import Counter, defaultdict
from hashlib import sha256
from itertools import product
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]


def require(value,message):
    if not value:
        raise ValueError(message)


def canonical_digest(value):
    encoded=json.dumps(value,sort_keys=True,separators=(',',':')).encode('ascii')
    return sha256(encoded).hexdigest()


def catalog():
    # Independent count-vector grammar, not combinations-with-replacement.
    arcs=[(i,j) for i in range(3) for j in range(3)]
    result=[]
    for counts in product(range(4),repeat=9):
        if sum(counts)<=3:
            result.append([list(arc) for arc,count in zip(arcs,counts) for _ in range(count)])
    return sorted(result,key=lambda rhs:(len(rhs),rhs))


def factorial(value):
    result=1
    for number in range(2,value+1):
        result*=number
    return result


def inspect_row(row,rules,seeds,design):
    index=row['rule_index']
    require(type(index) is int and 0<=index<len(rules),'invalid rule index')
    rhs=rules[index]
    require(row['rhs']==rhs,'rule definition/order mismatch')
    rule_id=canonical_digest({'schema':'mu-rule-v1','rhs':rhs})
    require(row['rule_id']==rule_id,'rule hash mismatch')
    require(row['seed_id'] in seeds,'unknown seed')
    seed=seeds[row['seed_id']]
    require(row['seed_sha256']==canonical_digest(seed),'seed hash mismatch')
    rep=row['replicate']
    require(type(rep) is int and 0<=rep<design['uniform_replicates'],'invalid replicate')
    require(row['scheduler'] in design['schedulers'],'invalid scheduler')
    require(rep==0 or row['scheduler']=='uniform','duplicated deterministic schedule')
    parent=f"mu/{design['design_id']}/{rule_id}/{row['seed_id']}/{rep}"
    require(row['parent_key']==parent and row['job_key']==parent+'/'+row['scheduler'],'identity mismatch')
    bucket=int(sha256(parent.encode()).hexdigest()[:16],16)%10
    label=(['discovery']*4+['detector-development']*2+['validation']*2+['final-test']*2)[bucket]
    require(row['partition']==label,'parent partition mismatch')
    require(row['rng_seed']==int(sha256(('rng|'+parent).encode()).hexdigest()[:16],16),'RNG seed mismatch')
    require(row['execution_status']=='not_executed','unexpected execution status')
    # Independently accumulate counts, never apply a rewrite to a graph.
    node_count,edge_count=seed['nodes'],len(seed['edges'])
    time=0
    expected=[]
    fresh=any(a==2 or b==2 for a,b in rhs)
    work=0
    for requested in design['snapshots']:
        while time<requested and edge_count:
            edge_count-=1
            edge_count+=len(rhs)
            node_count+=fresh
            time+=1
        reached=time==requested
        expected.append(dict(events=time,nodes=node_count,edges=edge_count,horizon_reachable=reached))
        if reached:
            require(node_count<=design['limits']['nodes'] and edge_count<=design['limits']['edges'],
                    'reachable snapshot exceeds caps')
            work+=factorial(edge_count)
    require(row['projected_snapshots']==expected,'snapshot prediction mismatch')
    require(row['raw_null_permutation_bound']==work,'null cost mismatch')


def verify(manifest,receipt):
    protocol=json.loads((ROOT/'protocols/r03a.json').read_text())
    design=json.loads((ROOT/'protocols/r03b-design.json').read_text())
    seeds=json.loads((ROOT/'protocols/r00.json').read_text())['seeds']
    contract=json.loads((ROOT/'protocols/r02-measurement-contract.json').read_text())
    require(design['launch_authorized'] is False,'unexpected launch authorization')
    require(design['preserved_intervention_horizon']==contract['intervention_horizon']==50,'changed intervention horizon')
    require(sha256(manifest.read_bytes()).hexdigest()==receipt['manifest_sha256'],'manifest digest mismatch')
    for path,digest in receipt['source_sha256'].items():
        require(sha256((ROOT/path).read_bytes()).hexdigest()==digest,'source drift: '+path)
    rules=catalog()
    require(len(rules)==protocol['expected_rules'],'rule count mismatch')
    seen=set();parents=defaultdict(set);cells=defaultdict(set);splits=Counter();costs=Counter()
    statuses=Counter();parent_splits={}
    with manifest.open() as stream:
        for line in stream:
            row=json.loads(line)
            inspect_row(row,rules,seeds,design)
            require(row['job_key'] not in seen,'duplicate job')
            seen.add(row['job_key'])
            parents[row['parent_key']].add(row['scheduler'])
            parent_splits[row['parent_key']]=row['partition']
            cells[(row['rule_id'],row['seed_id'])].add((row['replicate'],row['scheduler']))
            splits[row['partition']]+=1
            costs[row['partition']]+=row['raw_null_permutation_bound']
            last=row['projected_snapshots'][-1]
            statuses['reachable' if last['horizon_reachable'] else 'terminated_before_horizon']+=1
            if last['horizon_reachable'] and last['nodes']<2:
                statuses['primary_undefined_at_horizon']+=1
    require(len(seen)==protocol['expected_jobs'],'job count mismatch')
    require(len(parents)==protocol['expected_parent_groups'],'parent count mismatch')
    require(len(cells)==protocol['expected_rule_seed_cells'],'cell count mismatch')
    expected={(r,s) for r in range(design['uniform_replicates']) for s in design['schedulers'] if r==0 or s=='uniform'}
    require(all(cell==expected for cell in cells.values()),'missing scheduler/replicate cell')
    summary=receipt['summary']
    independent=dict(jobs=len(seen),rules=len(rules),rule_seed_cells=len(cells),parent_groups=len(parents),
                     jobs_by_partition=dict(splits),parents_by_partition=dict(Counter(parent_splits.values())),
                     projected_endpoint_statuses=dict(statuses),raw_null_permutation_bounds_by_partition=dict(costs))
    for key,value in independent.items():
        require(summary[key]==value,'summary mismatch: '+key)
    require(summary['world_transitions']==0 and summary['all_job_status']=='not_executed','unexpected world execution claim')
    # Universal successful-event horizon: the largest seed has four edges and k<=3.
    largest_seed=max(len(seed['edges']) for seed in seeds.values())
    common=(8-largest_seed)//(max(map(len,rules))-1)
    require(common==design['limits']['events']==max(design['snapshots'])==2,'common horizon is not maximal')
    h50=Counter()
    for rhs in rules:
        for seed in seeds.values():
            count=len(seed['edges'])
            if not rhs:
                h50['terminates_before_50']+=1
            elif count+50*(len(rhs)-1)>8:
                h50['exceeds_exact_null_edge_limit']+=1
            else:
                h50['edge_domain_supports_50']+=1
    # Historical receipts remain bound; no kernel or measurement revision.
    for name in ['r00.json','r01-release-parallel.json','r01-sanitize-parallel.json','r02.json']:
        prior=json.loads((ROOT/'reports'/name).read_text())
        for path,digest in prior.get('source_sha256',prior.get('sha256')).items():
            require(sha256((ROOT/path).read_bytes()).hexdigest()==digest,'prior source drift: '+path)
    return dict(status='pass',protocol_id='R03a-v1',manifest_sha256=receipt['manifest_sha256'],
                checked_jobs=len(seen),checked_parent_groups=len(parents),checked_cells=len(cells),
                common_horizon=common,horizon_50_cell_classification=dict(h50),
                source_sha256=receipt['source_sha256'],world_transitions=0,
                scientific_status='untested',launch_authorized=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--receipt',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    require(not args.output.exists(),'refusing to overwrite evidence')
    failure=None
    try:
        result=verify(args.manifest,json.loads(args.receipt.read_text()))
    except Exception as error:
        failure=error
        result={'protocol_id':'R03a-v1','status':'fail','failure':str(error),'world_transitions':0}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,sort_keys=True);stream.write('\n')
    print(json.dumps(result,sort_keys=True))
    if failure:
        raise SystemExit(str(failure))


if __name__=='__main__':
    main()
