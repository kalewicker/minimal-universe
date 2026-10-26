"""Full supplied-state engineering panel, bounded batches and independent replay."""
import argparse
from collections import Counter
from hashlib import sha256
import json
from pathlib import Path
import subprocess
import sys
import time
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT));sys.path.insert(0,str(ROOT/'scripts'))
from scripts.design_r06f import supplied
from scripts.plan_r05d import rules,rule_id
from scripts.verify_r05b import config_text
from scripts.g2_reference import Reference
from analysis.assay_eligibility_v1 import patches
from analysis.measurements import partition


def canonical(x):return json.dumps(x,sort_keys=True,separators=(',',':')).encode()+b'\n'
def require(ok,message):
    if not ok:raise ValueError(message)


def cases(rhs,index):
    law=rule_id(rhs)
    for seed in supplied():
        patch=patches(4,seed['edges'])[0]
        parent=f"mu/G2-supplied-cal-v1/law/{law}/seed/{seed['id']}"
        for scheduler in ('lex_first','lex_last','uniform_match'):
            for orientation in range(4):
                branch='target' if orientation<2 else 'sham'
                rng=int.from_bytes(sha256(f'mu-r06g-stream-v1\n{parent}\n{scheduler}\n{branch}'.encode()).digest()[:8],'big')
                yield dict(law_index=index,parent=parent,partition=partition(parent),pairing=seed['id'],
                    patch=patch,orientation=orientation,branch_seed=rng,
                    config=dict(nodes=4,rng=104729,seed=seed['edges'],rhs=rhs,scheduler=scheduler,
                    limits=dict(events=50,nodes=64,edges=64,matches=4032)))


def oracle(case):
    graph=Reference(case['config']);removed=[graph.edges[i] for i in sorted(graph.edges)]
    # Explicit directed cycles or reciprocal pairs mapped through canonical patch order.
    patterns=(((0,2),(2,1),(1,3),(3,0)),((0,3),(3,1),(1,2),(2,0)),
              ((0,2),(2,0),(1,3),(3,1)),((0,3),(3,0),(1,2),(2,1)))
    abstract=sorted(patterns[case['orientation']]);p=case['patch']
    graph.edges={4+i:[4+i,p[a],p[b],None] for i,(a,b) in enumerate(abstract)}
    graph.next_edge=8;graph.rng=case['branch_seed'];result=graph.run()
    result['intervention']=dict(prefix=0,orientation=case['orientation'],branch_seed=case['branch_seed'],
        first_output=4,consumed=removed,patch=list(p))
    return result


def compact(case,result):
    count=len(result['events'])
    return dict(law_index=case['law_index'],parent=case['parent'],partition=case['partition'],
        pairing=case['pairing'],scheduler=case['config']['scheduler'],orientation=case['orientation'],
        status=result['status'],events=count,reached_50=count==50,
        endpoint_empty=not result['edges'],endpoint_nodes=result['nodes'],endpoint_edges=len(result['edges']),
        known_shrinking=len(case['config']['rhs'])<2,execution='completed')


def summary(rows,total):
    complete=[r for r in rows if r.get('execution')=='completed']
    groups={}
    for row in complete:
        groups.setdefault((row['parent'],row['scheduler']),[]).append(row)
    return dict(planned_slots=total,executed_slots=len(complete),not_started_slots=total-len(rows),
        censored_slots=len(rows)-len(complete),statuses=dict(Counter(r['status'] for r in complete)),
        reached_50=sum(r['reached_50'] for r in complete),early_stop=sum(not r['reached_50'] for r in complete),
        empty_endpoints=sum(r['endpoint_empty'] for r in complete),successful_events=sum(r['events'] for r in complete),
        known_shrinking_executed=sum(r['known_shrinking'] for r in complete),
        all_four_complete_parent_scheduler_rows=sum(len(rs)==4 and all(r['reached_50'] for r in rs) for rs in groups.values()),
        complete_pair_inference_admitted=False,scientific_status='untested',null_draws=0)


def run_batch(binary,batch,folder,deadline,budget):
    payload=str(len(batch))+'\n'+''.join(config_text(c['config'])+' '.join(map(str,(*c['patch'],c['orientation'],c['branch_seed'])))+'\n' for c in batch)
    (folder/'input.txt').write_text(payload)
    start=time.monotonic()
    with (folder/'native.jsonl').open('xb') as out,(folder/'timing.json').open('xb') as err:
        process=subprocess.Popen([str(binary.resolve())],stdin=subprocess.PIPE,stdout=out,stderr=err)
        try:
            process.stdin.write(payload.encode());process.stdin.close()
            while process.poll() is None:
                require(time.monotonic()-start<budget['batch_seconds'] and time.monotonic()<deadline,'native deadline')
                require(sum(p.stat().st_size for p in folder.iterdir())<=budget['batch_bytes'],'native output cap')
                time.sleep(.01)
            require(process.returncode==0,'native failure')
        finally:
            if process.poll() is None:process.kill();process.wait()
    native_wall=time.monotonic()-start
    output=(folder/'native.jsonl').read_bytes();lines=output.splitlines()
    require(len(lines)==len(batch),'native denominator')
    begin=time.monotonic();rows=[]
    for case,line in zip(batch,lines):
        require(time.monotonic()<deadline,'oracle deadline')
        case_start=time.monotonic();result=json.loads(line);require(result==oracle(case),'independent replay mismatch')
        require(time.monotonic()-case_start<=budget['oracle_case_seconds'],'oracle case deadline')
        rows.append(compact(case,result))
    timing=json.loads((folder/'timing.json').read_text())
    timing.update(native_process_seconds=native_wall,python_replay_seconds=time.monotonic()-begin)
    return rows,sha256(output).hexdigest(),timing


def preflight(p):
    for name,digest in p['pins_sha256'].items():require(sha256((ROOT/name).read_bytes()).hexdigest()==digest,'source pin '+name)
    for name in ('protocols/r06f.json','protocols/r06e.json','protocols/r06d.json','protocols/r06c.json'):
        for source,digest in json.loads((ROOT/name).read_text())['pins_sha256'].items():
            require(sha256((ROOT/source).read_bytes()).hexdigest()==digest,'prior source pin '+source)


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--binary',type=Path)
    parser.add_argument('--mode',choices=['controls','panel'],default='panel')
    parser.add_argument('--output',type=Path);parser.add_argument('--verify-ledger',type=Path)
    a=parser.parse_args();path=ROOT/'protocols/r06g.json';p=json.loads(path.read_text());preflight(p)
    if a.verify_ledger:
        rows=json.loads((a.verify_ledger/'ledger.json').read_text());receipt=json.loads((a.verify_ledger/'receipt.json').read_text())
        require(receipt['protocol_sha256']==sha256(path.read_bytes()).hexdigest(),'protocol binding')
        require(sha256(canonical(rows)).hexdigest()==receipt['ledger_sha256'],'ledger hash')
        require(summary(rows,receipt['planned_slots'])=={k:receipt[k] for k in summary(rows,receipt['planned_slots'])},'summary replay')
        print('Saved ledger summary verified; no dynamics rerun.');return
    require(a.output is not None and a.binary is not None,'output and binary required')
    a.output.mkdir(parents=True,exist_ok=False)
    (a.output/'started.json').write_bytes(canonical(dict(protocol_sha256=sha256(path.read_bytes()).hexdigest(),mode=a.mode)))
    grammar=list(rules()) if a.mode=='panel' else [(),((0,1),(1,2)),((0,3),(1,3),(3,2))]
    total=len(grammar)*36
    require(total==p['expected_slots'][a.mode],'registered denominator')
    rows=[];hashes=[];timing=Counter();start=time.monotonic();deadline=start+p['budgets']['global_seconds'];retained=0
    try:
        for index,rhs in enumerate(grammar):
            require(time.monotonic()<deadline,'global deadline')
            require(retained+p['budgets']['batch_bytes']+32*1024*1024<p['budgets']['retained_bytes'],'global storage cap')
            batch=list(cases(rhs,index));folder=a.output/f'batch-{index:04d}';folder.mkdir()
            try: new,digest,cost=run_batch(a.binary,batch,folder,deadline,p['budgets'])
            except Exception:
                rows.extend(dict(parent=c['parent'],scheduler=c['config']['scheduler'],orientation=c['orientation'],execution='censored_batch_failure') for c in batch)
                raise
            rows.extend(new);hashes.append(digest);timing.update(cost)
            retained+=sum(f.stat().st_size for f in folder.iterdir())
            if (index+1)%100==0:print(f'{index+1}/{len(grammar)} batches independently replayed',flush=True)
        require(len({(r['parent'],r['scheduler'],r['orientation']) for r in rows})==total,'unique full accounting')
        if a.mode=='panel':require(sum(r['known_shrinking'] for r in rows)==612,'shrinking denominator')
        receipt=summary(rows,total)
        receipt.update(protocol_id=p['protocol_id'],protocol_sha256=sha256(path.read_bytes()).hexdigest(),mode=a.mode,
            engineering_status='passed',ledger_sha256=sha256(canonical(rows)).hexdigest(),batch_output_sha256=hashes)
        (a.output/'ledger.json').write_bytes(canonical(rows));(a.output/'receipt.json').write_bytes(canonical(receipt))
        retained+=sum(f.stat().st_size for f in a.output.iterdir() if f.is_file())
        require(retained+4096<=p['budgets']['retained_bytes'],'final storage cap')
        require(time.monotonic()<deadline,'final global deadline')
        timing.update(wall_seconds=time.monotonic()-start,retained_bytes_before_execution=retained)
        (a.output/'execution.json').write_bytes(canonical(dict(timing,binary_sha256=sha256(a.binary.read_bytes()).hexdigest())))
        print(json.dumps({k:v for k,v in receipt.items() if k!='batch_output_sha256'},sort_keys=True))
    except Exception as exc:
        (a.output/'partial-ledger.json').write_bytes(canonical(rows))
        (a.output/'failure.json').write_bytes(canonical(dict(error=str(exc),**summary(rows,total))))
        raise
if __name__=='__main__':main()
