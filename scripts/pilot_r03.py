#!/usr/bin/env python3
"""Registered R03p engineering panel and fault injection; never dispatches atlas jobs."""
import argparse
from collections import Counter
from fractions import Fraction
from hashlib import sha256
from itertools import combinations
import json
import math
from pathlib import Path
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
from bounded_runner import run_batch,summary_reservation
from verify_r01 import reference_graph
from verify_r03_plan import verify as verify_plan,inspect_row,catalog
from calibrate_r02 import orbit_table,oracle_connected


def require(value,message):
    if not value: raise ValueError(message)


def rational(value):
    return None if value is None else [value.numerator,value.denominator]


def oracle_observation(nodes,edge_records,tables):
    edges=[(e[1],e[2]) for e in edge_records]
    histogram=Counter();denominators={};eligible=0;excluded=0
    for size in range(1,min(3,nodes)+1):
        denominators[str(size)]=math.comb(nodes,size)
        for subset in combinations(range(nodes),size):
            flat=tuple(edges.count((i,j)) for i in subset for j in subset)
            if not oracle_connected(size,flat): continue
            eligible+=1
            if max(flat)>2: excluded+=1
            else: histogram[tables[size][flat]]+=1
    def score(sequence):
        if nodes<2: return None
        present=set(sequence)
        return Fraction(sum((i,j) in present and (j,i) in present for i,j in combinations(range(nodes),2)),math.comb(nodes,2))
    density=score(edges)
    distribution=Counter()
    if nodes>=2:
        sources=[u for u,_ in edges];remaining=Counter(v for _,v in edges)
        def assign(targets):
            if len(targets)==len(sources):
                distribution[score(zip(sources,targets))]+=1;return
            for vertex in sorted(remaining):
                if remaining[vertex]:
                    remaining[vertex]-=1;assign(targets+[vertex]);remaining[vertex]+=1
        assign([])
    total=sum(distribution.values())
    null={value:Fraction(count,total) for value,count in distribution.items()}
    mean=sum((value*weight for value,weight in null.items()),Fraction()) if density is not None else None
    return dict(nodes=nodes,edges=len(edges),
                motifs=dict(counts=dict(sorted(histogram.items())),denominators=denominators,
                            connected_subsets=eligible,excluded_subsets=excluded,coverage_complete=excluded==0),
                density=rational(density),null_status='undefined' if nodes<2 else 'informative' if len(null)>1 else 'degenerate',
                null_distribution=[[rational(value),rational(weight)] for value,weight in sorted(null.items())],
                null_mean=rational(mean),density_minus_null_mean=rational(density-mean) if density is not None else None)


def select_discovery(records,design,seeds,rules):
    selected=[]
    for index,row in enumerate(records):
        inspect_row(row,rules,seeds,design)
        if row['partition']=='discovery': selected.append(index)
    return selected


def faults(directory):
    limits=dict(workers=1,per_job_wall_seconds=2,global_wall_seconds=10,
                global_output_bytes=65536,per_job_output_bytes=4096)
    results={}
    def check(name,program,overrides=None,jobs=None):
        joblist=jobs or [{'id':0}]
        result=run_batch(joblist,lambda job:[sys.executable,'-c',program],limits|(overrides or {}),directory/name)
        actual_bytes=sum(p.stat().st_size for p in (directory/name).iterdir())
        require(actual_bytes==result['stored_bytes']<=result['limits']['global_output_bytes'],'storage accounting mismatch')
        results[name]={'statuses':result['statuses'],'stored_bytes':result['stored_bytes'],
                       'summary_sha256':sha256((directory/name/'summary.json').read_bytes()).hexdigest()}
        return result['statuses']
    require(check('invalid_json',"print('not json')")==['invalid_worker_json'],'invalid JSON not rejected')
    require(check('nonzero_exit','raise SystemExit(3)')==['worker_error'],'nonzero exit not recorded')
    # Child keeps inherited pipes open: group timeout must also terminate it.
    hang="import subprocess,sys,time; subprocess.Popen([sys.executable,'-c','import time; time.sleep(10)']); time.sleep(10)"
    require(check('job_deadline',hang,{'per_job_wall_seconds':.15})==['job_wall_cap'],'job deadline failed')
    statuses=check('global_deadline',hang,{'per_job_wall_seconds':10,'global_wall_seconds':.15},[{'id':i} for i in range(3)])
    require(statuses==['global_wall_cap','not_started_global_wall_cap','not_started_global_wall_cap'],'global deadline accounting failed')
    require(check('output_cap',"import sys; sys.stdout.write('x'*100000); sys.stdout.flush()",{'per_job_output_bytes':1024})==['output_cap'],'byte cap failed')
    jobs=[{'id':i} for i in range(3)]
    budget=summary_reservation(len(jobs))+4096
    statuses=check('storage_cap',"print('{}')",{'global_output_bytes':budget},jobs)
    require(statuses==['complete','not_started_global_output_cap','not_started_global_output_cap'],'storage suffix accounting failed')
    require(check('reserved',"raise SystemExit('must never run')",jobs=[{'reserved':True}])==['reserved'],'reserved job dispatched')
    try: run_batch([{}],lambda _:[sys.executable,'-c',"print('{}')"],limits,directory/'reserved')
    except FileExistsError: results['existing_directory']={'status':'rejected'}
    else: raise ValueError('existing attempt overwritten')
    return results


def run(binary,manifest,receipt,directory):
    protocol=json.loads((ROOT/'protocols/r03p.json').read_text())
    # This validates the production registry without executing any of its jobs.
    verified=verify_plan(manifest,json.loads(receipt.read_text()))
    records=[json.loads(line) for line in manifest.read_text().splitlines()]
    design=json.loads((ROOT/'protocols/r03b-design.json').read_text())
    seeds=json.loads((ROOT/'protocols/r00.json').read_text())['seeds']
    rules=catalog()
    selected=select_discovery(records,design,seeds,rules)
    require(len(selected)==10946,'discovery denominator changed')
    reserved=next(row for row in records if row['partition']!='discovery')
    try: select_discovery([reserved|{'partition':'discovery'}],design,seeds,rules)
    except ValueError: pass
    else: raise ValueError('partition forgery accepted')
    jobs=[{'fixture_id':f['id'],'scheduler':s,'kind':'engineering'} for f in protocol['fixtures'] for s in protocol['schedulers']]
    require(len(jobs)==protocol['expected_jobs'],'pilot panel changed')
    def command(job):
        return [sys.executable,'-B',str(ROOT/'scripts/observe_r03.py'),'--binary',str(binary.resolve()),
                '--fixture',job['fixture_id'],'--scheduler',job['scheduler']]
    batch=run_batch(jobs,command,protocol['runner_limits'],directory/'panel')
    require(all(status=='complete' for status in batch['statuses']),'pilot job did not complete')
    tables={n:orbit_table(n) for n in (1,2,3)}
    counts=Counter();timings=[];sizes=[]
    for line in (directory/'panel/events.jsonl').read_bytes().splitlines():
        record=json.loads(line);job=jobs[record['index']]
        fixture=next(f for f in protocol['fixtures'] if f['id']==job['fixture_id'])
        budget=dict(rng_seed=protocol['rng_seed'],max_events=2,max_nodes=5,max_edges=8)
        expected=reference_graph(fixture,fixture['rhs'],job['scheduler'],budget)
        require(record['result']['native']==expected,'independent native trace mismatch')
        observations=[]
        for horizon in protocol['snapshots']:
            if horizon>len(expected['events']):
                observations.append(dict(event=horizon,status='terminated_before_horizon',measurement=None))
                counts['unavailable_snapshots']+=1
            else:
                endpoint=reference_graph(fixture,fixture['rhs'],job['scheduler'],budget|{'max_events':horizon})
                measured=oracle_observation(endpoint['nodes'],endpoint['edges'],tables)
                observations.append(dict(event=horizon,status='observed',measurement=measured))
                counts['observed_snapshots']+=1
                counts['incomplete_motif_snapshots']+=not measured['motifs']['coverage_complete']
                counts['undefined_density_snapshots']+=measured['density'] is None
                counts['degenerate_null_snapshots']+=measured['null_status']=='degenerate'
        require(record['result']['snapshots']==observations,'independent observation mismatch')
        counts['jobs']+=1;counts['native_events']+=len(expected['events'])
        timings.append(record['elapsed_seconds']);sizes.append(len(line)+1)
    actual_bytes=sum(p.stat().st_size for p in (directory/'panel').iterdir())
    require(actual_bytes==batch['stored_bytes']<=protocol['runner_limits']['global_output_bytes'],'panel byte accounting mismatch')
    fault_results=faults(directory/'faults')
    return dict(status='pass',checks=dict(counts),fault_cases=fault_results,
                static_atlas_jobs_checked=verified['checked_jobs'],discovery_admissible=len(selected),
                reserved_atlas_jobs=len(records)-len(selected),atlas_jobs_executed=0,
                pilot_elapsed_seconds=batch['elapsed_seconds'],pilot_stored_bytes=batch['stored_bytes'],
                maximum_job_seconds=max(timings),maximum_record_bytes=max(sizes),
                panel_ledger_sha256=batch['ledger_sha256'],scientific_status='untested',
                atlas_launch_authorized=False)


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary',type=Path,required=True)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--plan-receipt',type=Path,required=True)
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    require(not args.output.exists(),'refusing to overwrite receipt')
    args.directory.mkdir(parents=True,exist_ok=False)
    paths=['protocols/r03p.json','scripts/bounded_runner.py','scripts/observe_r03.py',
           'scripts/pilot_r03.py','tests/test_r03_runner.py','analysis/measurements.py',
           'scripts/verify_r01.py','scripts/verify_r03_plan.py','scripts/calibrate_r02.py']
    result={'protocol_id':'R03p-v1','source_sha256':{p:sha256((ROOT/p).read_bytes()).hexdigest() for p in paths},
            'binary_sha256':sha256(args.binary.read_bytes()).hexdigest()}
    failure=None
    try: result.update(run(args.binary,args.manifest,args.plan_receipt,args.directory))
    except Exception as error:
        failure=error;result.update(status='fail',failure=str(error),atlas_launch_authorized=False)
    with args.output.open('x') as stream:
        json.dump(result,stream,sort_keys=True,indent=2);stream.write('\n')
    print(json.dumps(result,sort_keys=True))
    if failure: raise SystemExit(str(failure))


if __name__=='__main__': main()
