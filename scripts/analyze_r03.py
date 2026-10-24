#!/usr/bin/env python3
"""Read-only independent replay and descriptive accounting of the sealed atlas."""
import argparse
from collections import Counter,defaultdict
import csv
from fractions import Fraction
from functools import lru_cache
from hashlib import sha256
import io
import json
from pathlib import Path

ROOT=Path(__file__).resolve().parents[1]
from bounded_runner import encoded
from verify_r01 import reference_graph
from pilot_r03 import oracle_observation
from calibrate_r02 import orbit_table


def require(value,message):
    if not value: raise ValueError(message)


def file_hash(path): return sha256(path.read_bytes()).hexdigest()


def analyze(directory):
    header=json.loads((directory/'launch.json').read_text())
    protocol=header['protocol'];seal=header['seal']
    for path,digest in seal['source_sha256'].items():
        require(file_hash(ROOT/path)==digest,'sealed source drift: '+path)
    require(file_hash(directory/'plan.jsonl')==protocol['manifest_sha256']==seal['manifest_sha256'],'manifest drift')
    records=[json.loads(line) for line in (directory/'plan.jsonl').read_text().splitlines()]
    summary=json.loads((directory/'batch/summary.json').read_text())
    run=json.loads((directory/'run.json').read_text())
    ledger=directory/'batch/events.jsonl'
    require(file_hash(ledger)==summary['ledger_sha256']==run['ledger_sha256'],'ledger drift')
    require(ledger.stat().st_size==summary['ledger_bytes'],'ledger byte count')
    require(sum(p.stat().st_size for p in (directory/'batch').iterdir())==summary['stored_bytes'],'stored byte count')
    require(len(summary['statuses'])==len(records)==protocol['expected_jobs'],'status denominator')
    jobs=[{'job_key':r['job_key'],'index':i,'reserved':r['partition']!='discovery'} for i,r in enumerate(records)]
    require(sha256(encoded(jobs)).hexdigest()==summary['plan_sha256'],'dispatch plan drift')
    overhead=(directory/'plan.jsonl').stat().st_size+(directory/'launch.json').stat().st_size
    expected_limits=dict(protocol['runner_limits'])
    expected_limits['global_output_bytes']-=overhead+protocol['analysis_reserve_bytes']
    require(summary['limits']==expected_limits,'execution budgets changed')
    require(Counter(summary['statuses'])==Counter(run['counts']),'run status summary mismatch')
    seeds=json.loads((ROOT/'protocols/r00.json').read_text())['seeds']
    tables={n:orbit_table(n) for n in (1,2,3)}
    @lru_cache(maxsize=10000)
    def observation(nodes,pairs):
        return oracle_observation(nodes,[[i,u,v,None] for i,(u,v) in enumerate(pairs)],tables)
    counts=Counter();groups=defaultdict(Counter);cells=defaultdict(Counter)
    rows_by_key={};seen=set()
    for i,row in enumerate(records):
        key=(row['rule_index'],row['rule_id'],row['seed_id'],row['scheduler'])
        rows_by_key[i]=key;cell=cells[key]
        cell['planned']+=1
        status=summary['statuses'][i]
        if row['partition']!='discovery':
            require(status=='reserved','held-out job executed or status changed')
            cell['reserved']+=1;counts['reserved']+=1
        else:
            require(status!='reserved','discovery job silently reserved')
            cell['discovery']+=1
            if status=='complete': cell['complete']+=1
            elif status.startswith('not_started_'): cell['not_started']+=1
            else: cell['errors']+=1
    for line in ledger.read_bytes().splitlines():
        logged=json.loads(line);index=logged['index']
        require(type(index) is int and 0<=index<len(records) and index not in seen,'invalid/duplicate ledger index')
        seen.add(index);row=records[index];cell=cells[rows_by_key[index]]
        require(row['partition']=='discovery','held-out record in ledger')
        require(logged['status']==summary['statuses'][index],'ledger/status mismatch')
        require(len(line)+1<=protocol['runner_limits']['per_job_output_bytes'],'record exceeded byte cap')
        if logged['status']!='complete':
            counts['recorded_errors']+=1;continue
        native=logged['result']['native']
        require(logged['result']['job_key']==row['job_key'],'worker identity mismatch')
        seed=seeds[row['seed_id']]
        budget=dict(rng_seed=row['rng_seed'],max_events=2,max_nodes=5,max_edges=8)
        expected=reference_graph(seed,row['rhs'],row['scheduler'],budget)
        require(native==expected,'independent native mismatch at index '+str(index))
        counts['completed_jobs']+=1;counts['native_events']+=len(native['events'])
        counts['native_stop_'+native['status']]+=1
        snapshots=[]
        for horizon in protocol['snapshots']:
            group=groups[(row['scheduler'],horizon)]
            if horizon>len(native['events']):
                status='terminated_before_horizon' if native['status']=='no_eligible_edge' else 'censored_before_horizon'
                snapshots.append(dict(event=horizon,status=status,measurement=None))
                counts[status]+=1;group[status]+=1
                if horizon==2: cell['endpoint_unavailable']+=1
                continue
            endpoint=reference_graph(seed,row['rhs'],row['scheduler'],budget|{'max_events':horizon})
            pairs=tuple(sorted((e[1],e[2]) for e in endpoint['edges']))
            measured=observation(endpoint['nodes'],pairs)
            snapshots.append(dict(event=horizon,status='observed',measurement=measured))
            counts['observed_snapshots']+=1;group['observed']+=1
            group['null_'+measured['null_status']]+=1
            group['motif_incomplete']+=not measured['motifs']['coverage_complete']
            group['motif_excluded_subsets']+=measured['motifs']['excluded_subsets']
            if horizon==2:
                cell['endpoint_observed']+=1
                cell['endpoint_null_informative']+=measured['null_status']=='informative'
                cell['endpoint_motif_incomplete']+=not measured['motifs']['coverage_complete']
            if measured['density'] is None:
                group['density_undefined']+=1
            else:
                density=Fraction(*measured['density']);difference=Fraction(*measured['density_minus_null_mean'])
                group['density_defined']+=1;group['density_sum']+=density;group['contrast_sum']+=difference
                sign='positive' if difference>0 else 'negative' if difference<0 else 'zero'
                group['contrast_'+sign]+=1
                if horizon==2:
                    cell['endpoint_density_defined']+=1
                    cell['endpoint_'+sign+'_contrast']+=1
        require(logged['result']['snapshots']==snapshots,'independent observation mismatch at index '+str(index))
        if counts['completed_jobs']%2000==0: print(f"Independently verified {counts['completed_jobs']} saved jobs",flush=True)
    for index,status in enumerate(summary['statuses']):
        expected_record=status!='reserved' and not status.startswith('not_started_')
        require((index in seen)==expected_record,'missing or spurious attempt record')
    require(counts['reserved']==protocol['expected_reserved_jobs'],'holdout denominator')
    require(len(cells)==1540*3,'full cell/scheduler denominator')
    observed_cells={key[:3] for key,value in cells.items() if value['complete']}
    group_rows=[]
    for (scheduler,horizon),stats in sorted(groups.items()):
        converted={k:([v.numerator,v.denominator] if isinstance(v,Fraction) else v) for k,v in stats.items()}
        group_rows.append(dict(scheduler=scheduler,event=horizon,counts=converted))
    fields=['rule_index','rule_id','seed_id','scheduler','planned','discovery','reserved','complete','errors','not_started',
            'endpoint_observed','endpoint_unavailable','endpoint_density_defined','endpoint_null_informative',
            'endpoint_motif_incomplete','endpoint_positive_contrast','endpoint_zero_contrast','endpoint_negative_contrast']
    output=io.StringIO();writer=csv.DictWriter(output,fieldnames=fields,lineterminator='\n');writer.writeheader()
    for key,stats in sorted(cells.items()):
        record=dict(zip(fields[:4],key))|{field:stats[field] for field in fields[4:]}
        writer.writerow(record)
    report={'protocol_id':protocol['protocol_id'],'audit_status':'pass',
            'execution_status':run['execution_status'],'counts':dict(counts),
            'completed_rule_seed_cells':len(observed_cells),'total_planned_rule_seed_cells':1540,
            'groups':group_rows,'elapsed_execution_seconds':summary['elapsed_seconds'],
            'ledger_sha256':file_hash(ledger),'manifest_sha256':file_hash(directory/'plan.jsonl'),
            'seal_sha256':header['seal_sha256'],'scientific_status':'descriptive_only',
            'candidate_promotions':0,'downstream_authorized':False,
            'interpretation':'Short-horizon descriptive observations only; no statistical or causal acceptance.'}
    complete=counts['completed_jobs']==protocol['expected_discovery_jobs']
    require((run['execution_status']=='complete')==complete,'completion claim mismatch')
    return report,output.getvalue().encode()


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--directory',type=Path,required=True)
    parser.add_argument('--output-directory',type=Path,required=True)
    args=parser.parse_args()
    args.output_directory.mkdir(parents=True,exist_ok=False)
    failure=None
    try:
        report,csv_data=analyze(args.directory)
        report['cell_csv_sha256']=sha256(csv_data).hexdigest()
        protocol=json.loads((args.directory/'launch.json').read_text())['protocol']
        existing=sum(p.stat().st_size for p in args.directory.rglob('*') if p.is_file())
        report['retained_execution_bytes']=existing
        total=len(csv_data)+len(encoded(report))
        require(total<=protocol['analysis_reserve_bytes'],'analysis reserve exceeded')
        require(existing+total<=protocol['runner_limits']['global_output_bytes'],'global retained-byte budget exceeded')
        (args.output_directory/'cells.csv').write_bytes(csv_data)
    except Exception as error:
        failure=error;report={'audit_status':'fail','failure':str(error),'downstream_authorized':False}
    with (args.output_directory/'summary.json').open('xb') as stream: stream.write(encoded(report))
    print(json.dumps(report,sort_keys=True))
    if failure: raise SystemExit(str(failure))


if __name__=='__main__': main()
