"""Registered native synthetic assay matrix; independent dictionary replay."""
import argparse
from copy import deepcopy
from hashlib import sha256
from itertools import combinations_with_replacement
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'scripts'))
sys.path.insert(0,str(ROOT))
from g2_reference import Reference
from verify_r05b import config_text
from analysis.measurements import partition


def canonical(x):
    return json.dumps(x,sort_keys=True,separators=(',',':')).encode()+b'\n'


def require(ok,message):
    if not ok: raise ValueError(message)


def branch_seed(parent,scheduler,branch):
    return int.from_bytes(sha256(('mu-r06d-branch-v1\n'+parent+'\n'+scheduler+'\n'+branch).encode()).digest()[:8],'big')


def cases():
    external=[(v,4) for v in range(4)]+[(4,v) for v in range(4)]+[(4,4)]
    contexts=[list(c) for n in range(4) for c in combinations_with_replacement(external,n)]
    for ci,context in enumerate(contexts):
        for pre in (0,1):
            for scheduler in ('lex_first','lex_last','uniform_match'):
                for orientation in range(4):
                    parent=f'mu/G2-assay-cal-v1/context/{ci}'
                    kind='target' if orientation<2 else 'sham'
                    yield dict(parent=parent,partition=partition(parent),orientation=orientation,pre=pre,
                        seed=branch_seed(parent,scheduler,kind),config=dict(nodes=5,rng=104729,
                        seed=[[0,1],[1,0],[2,3],[3,2]]+[list(a) for a in context],
                        rhs=[[0,1],[1,2]],scheduler=scheduler,
                        limits=dict(events=pre+3,nodes=64,edges=64,matches=4032)))
    for scheduler in ('lex_first','lex_last','uniform_match'):
        for orientation in range(4):
            parent='mu/G2-assay-cal-v1/terminal'
            yield dict(parent=parent,partition=partition(parent),orientation=orientation,pre=0,
                seed=branch_seed(parent,scheduler,'target' if orientation<2 else 'sham'),
                config=dict(nodes=5,rng=104729,seed=[[0,1],[1,0],[2,3],[3,2]],rhs=[],
                    scheduler=scheduler,limits=dict(events=3,nodes=64,edges=64,matches=4032)))


def oracle(case):
    graph=Reference(case['config']);graph.prefix(case['pre'])
    removed=[graph.edges[i] for i in sorted(graph.edges)
             if graph.edges[i][1]<4 and graph.edges[i][2]<4]
    # Independent endpoint lists, not the native permutation construction.
    arcs=(((0,2),(2,1),(1,3),(3,0)),((0,3),(3,1),(1,2),(2,0)),
          ((0,2),(2,0),(1,3),(3,1)),((0,3),(3,0),(1,2),(2,1)))[case['orientation']]
    first=graph.next_edge
    for e in removed: del graph.edges[e[0]]
    for index,(a,b) in enumerate(sorted(arcs)):
        graph.edges[first+index]=[first+index,a,b,None]
    graph.next_edge+=4;graph.rng=case['seed']
    intervention=dict(prefix=case['pre'],orientation=case['orientation'],branch_seed=case['seed'],
        first_output=first,consumed=deepcopy(removed),patch=[0,1,2,3])
    result=graph.run();result['intervention']=intervention
    return result


def main():
    p=argparse.ArgumentParser();p.add_argument('--binary',type=Path,required=True)
    g=p.add_mutually_exclusive_group(required=True);g.add_argument('--output',type=Path);g.add_argument('--verify',type=Path)
    a=p.parse_args(); protocol_path=ROOT/'protocols/r06d.json';protocol=json.loads(protocol_path.read_text())
    for path,digest in protocol['pins_sha256'].items():
        require(sha256((ROOT/path).read_bytes()).hexdigest()==digest,'source pin '+path)
    for path in ('protocols/r06c.json','protocols/r06b.json'):
        for name,digest in json.loads((ROOT/path).read_text())['pins_sha256'].items():
            require(sha256((ROOT/name).read_bytes()).hexdigest()==digest,'prior pin '+name)
    start=time.monotonic()
    if a.output:
        a.output.mkdir(parents=True,exist_ok=False)
        (a.output/'started.json').write_bytes(canonical(dict(protocol_sha256=sha256(protocol_path.read_bytes()).hexdigest())))
    try:
        matrix=list(cases());require(len(matrix)==protocol['expected_cases'],'case count')
        payload=str(len(matrix))+'\n'+''.join(config_text(c['config'])+f"{c['pre']} {c['orientation']} {c['seed']}\n" for c in matrix)
        result=subprocess.run([str(a.binary.resolve())],input=payload.encode(),stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,timeout=protocol['budgets']['native_seconds'])
        if a.output:
            (a.output/'input.txt').write_text(payload)
            (a.output/'native.jsonl').write_bytes(result.stdout)
            (a.output/'native.stderr').write_bytes(result.stderr)
        require(result.returncode==0,'native failure: '+result.stderr.decode())
        lines=result.stdout.splitlines();require(len(lines)==len(matrix),'output count')
        outcomes={}; events=0; seeds={}; groups={}
        for case,line in zip(matrix,lines):
            actual=json.loads(line);expected=oracle(case)
            require(actual==expected,'native/oracle mismatch '+str(case))
            outcomes[actual['status']]=outcomes.get(actual['status'],0)+1
            events+=len(actual['events'])
            key=(case['parent'],case['config']['scheduler'])
            seeds.setdefault(key,set()).add(case['seed'])
            groups.setdefault(case['parent'],set()).add(case['partition'])
        require(all(len(s)==2 for s in seeds.values()),'branch stream collision')
        require(all(len(s)==1 for s in groups.values()),'partition inheritance')
        require(outcomes==protocol['expected_statuses'],'terminal accounting')
        receipt=dict(protocol_id=protocol['protocol_id'],protocol_sha256=sha256(protocol_path.read_bytes()).hexdigest(),
            cases=len(matrix),parent_groups=len(groups),branch_stream_pairs=len(seeds),statuses=outcomes,
            native_output_sha256=sha256(result.stdout).hexdigest(),input_sha256=sha256(payload.encode()).hexdigest(),
            synthetic_events_in_reported_histories=events,scientific_world_transitions=0,
            engineering_status='passed',scientific_status='untested',production_adopted=False)
        if a.verify: require(json.loads(a.verify.read_text())==receipt,'receipt replay')
        else:
            (a.output/'receipt.json').write_bytes(canonical(receipt))
            elapsed=time.monotonic()-start
            retained=sum(f.stat().st_size for f in a.output.iterdir())
            require(elapsed<=protocol['budgets']['wall_seconds'],'wall budget')
            require(retained+4096<=protocol['budgets']['retained_bytes'],'storage budget')
            (a.output/'execution.json').write_bytes(canonical(dict(status='passed',wall_seconds=elapsed,
                retained_bytes_before_execution=retained,binary_sha256=sha256(a.binary.read_bytes()).hexdigest())))
        print(json.dumps(receipt,sort_keys=True))
    except Exception as exc:
        if a.output:(a.output/'failure.json').write_bytes(canonical(dict(status='failed',error=str(exc))))
        raise


if __name__=='__main__':main()
