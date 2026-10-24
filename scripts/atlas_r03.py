#!/usr/bin/env python3
"""Sealed discovery-only atlas adapter; existing attempts are never resumed."""
import argparse
from collections import Counter
from hashlib import sha256
from itertools import combinations_with_replacement,product
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
from bounded_runner import run_batch,encoded
from observe_r03 import observe
from verify_r01 import config_text
from verify_r03_plan import inspect_row,verify as verify_plan

SEAL=ROOT/'protocols/r03b-seal.json'
LAUNCH=ROOT/'protocols/r03b-launch.json'


def require(value,message):
    if not value: raise ValueError(message)


def file_hash(path):
    return sha256(Path(path).read_bytes()).hexdigest()


def rules():
    arcs=tuple(product(range(3),repeat=2))
    return [[list(a) for a in rhs] for k in range(4) for rhs in combinations_with_replacement(arcs,k)]


def validate_worker_row(row,design,seeds):
    inspect_row(row,rules(),seeds,design)
    require(row['partition']=='discovery','reserved partition cannot execute')
    return seeds[row['seed_id']]


def verify_bound_receipt(path):
    receipt=json.loads(path.read_text())
    require(receipt['status']=='pass','prerequisite did not pass: '+path.name)
    for relative,digest in receipt.get('source_sha256',receipt.get('sha256',{})).items():
        require(file_hash(ROOT/relative)==digest,'prerequisite source drift: '+relative)


def build_seal(binary):
    require(not SEAL.exists(),'source seal already exists')
    protocol=json.loads(LAUNCH.read_text())
    require(not (ROOT/'results'/protocol['attempt_id']).exists(),'attempt already consumed')
    paths=['protocols/r03b-launch.json','protocols/r03b-design.json','protocols/r00.json',
           'scripts/atlas_r03.py','scripts/analyze_r03.py','scripts/bounded_runner.py',
           'scripts/observe_r03.py','scripts/pilot_r03.py','scripts/verify_r01.py',
           'scripts/verify_r03_plan.py','scripts/calibrate_r02.py','analysis/measurements.py',
           'tests/test_atlas_r03.py','reports/r03a-plan.json','reports/r03a-verification.json',
           'reports/r03p.json','reports/r03p-custody.json','reports/r01-release-parallel.json',
           'reports/r02.json','reports/r00.json']
    for name in ['r00.json','r01-release-parallel.json','r02.json','r03a-verification.json','r03p.json']:
        verify_bound_receipt(ROOT/'reports'/name)
    require(file_hash(binary)==json.loads((ROOT/'reports/r01-release-parallel.json').read_text())['binary_sha256'],
            'binary differs from validated release')
    seal={'protocol_id':protocol['protocol_id'],'source_sha256':{p:file_hash(ROOT/p) for p in paths},
          'binary_sha256':file_hash(binary),'manifest_sha256':protocol['manifest_sha256']}
    with SEAL.open('x') as stream: stream.write(encoded(seal).decode())
    return seal


def validate_seal(binary):
    seal=json.loads(SEAL.read_text())
    for path,digest in seal['source_sha256'].items():
        require(file_hash(ROOT/path)==digest,'launch source drift: '+path)
    require(file_hash(binary)==seal['binary_sha256'],'native binary drift')
    protocol=json.loads(LAUNCH.read_text())
    require(protocol['launch_authorized'] is True and protocol['holdout_authorized'] is False,'invalid launch scope')
    return protocol,seal


def run_worker(binary,row):
    protocol,_=validate_seal(binary)
    design=json.loads((ROOT/protocol['design']).read_text())
    seeds=json.loads((ROOT/'protocols/r00.json').read_text())['seeds']
    seed=validate_worker_row(row,design,seeds)
    limit=protocol['graph_limits']
    budget=dict(rng_seed=row['rng_seed'],max_events=limit['events'],max_nodes=limit['nodes'],max_edges=limit['edges'])
    with tempfile.TemporaryDirectory(prefix='mu-atlas-') as temp:
        config=Path(temp)/'config.txt'
        config.write_text(config_text(seed,row['rhs'],row['scheduler'],budget))
        completed=subprocess.run([str(binary.resolve()),'graph',str(config)],capture_output=True,text=True,check=True)
    native=json.loads(completed.stdout)
    return {'job_key':row['job_key'],'native':native,
            'snapshots':observe(native,seed,row['rhs'],protocol['snapshots'])}


def launch(binary):
    protocol,seal=validate_seal(binary)
    design=json.loads((ROOT/protocol['design']).read_text())
    require(protocol['runner_limits']==design['future_runner_limits'],'changed execution limits')
    require(protocol['graph_limits']==design['limits'] and protocol['snapshots']==design['snapshots'],'changed observation budget')
    manifest=ROOT/protocol['manifest']
    require(file_hash(manifest)==protocol['manifest_sha256']==seal['manifest_sha256'],'manifest mismatch')
    plan_receipt=json.loads((ROOT/'reports/r03a-plan.json').read_text())
    verify_plan(manifest,plan_receipt)
    records=[json.loads(line) for line in manifest.read_text().splitlines()]
    require(len(records)==protocol['expected_jobs'],'job denominator')
    require(sum(row['partition']=='discovery' for row in records)==protocol['expected_discovery_jobs'],'discovery denominator')
    jobs=[{'job_key':r['job_key'],'index':i,'reserved':r['partition']!='discovery'} for i,r in enumerate(records)]
    directory=ROOT/'results'/protocol['attempt_id']
    directory.mkdir(exist_ok=False)
    shutil.copyfile(manifest,directory/'plan.jsonl')
    header={'protocol':protocol,'seal':seal,'seal_sha256':file_hash(SEAL),'input_plan_sha256':file_hash(manifest)}
    (directory/'launch.json').write_bytes(encoded(header))
    overhead=sum(p.stat().st_size for p in directory.iterdir())
    limits=dict(protocol['runner_limits'])
    limits['global_output_bytes']-=overhead+protocol['analysis_reserve_bytes']
    def command(job):
        row=records[job['index']]
        require(row['partition']=='discovery' and not job['reserved'],'dispatch attempted reserved job')
        return [sys.executable,'-B',str(ROOT/'scripts/atlas_r03.py'),'worker','--binary',str(binary.resolve()),
                '--row',json.dumps(row,separators=(',',':'))]
    summary=run_batch(jobs,command,limits,directory/'batch')
    counts=dict(Counter(summary['statuses']))
    require(counts.get('reserved',0)==protocol['expected_reserved_jobs'],'holdout accounting changed')
    receipt={'protocol_id':protocol['protocol_id'],'attempt_id':protocol['attempt_id'],
             'execution_status':'complete' if counts.get('complete',0)==protocol['expected_discovery_jobs'] else 'partial',
             'validation_status':'pending_independent_saved_result_audit','counts':counts,
             'elapsed_seconds':summary['elapsed_seconds'],'batch_stored_bytes':summary['stored_bytes'],
             'manifest_sha256':file_hash(directory/'plan.jsonl'),'ledger_sha256':summary['ledger_sha256'],
             'seal_sha256':file_hash(SEAL),'binary_sha256':seal['binary_sha256'],
             'scientific_status':'descriptive_only','downstream_authorized':False}
    require(overhead+summary['stored_bytes']+len(encoded(receipt))<=protocol['runner_limits']['global_output_bytes'],'retained budget overflow')
    with (directory/'run.json').open('xb') as stream: stream.write(encoded(receipt))
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('mode',choices=['seal','worker','launch'])
    parser.add_argument('--binary',type=Path,required=True)
    parser.add_argument('--row')
    args=parser.parse_args()
    if args.mode=='seal': result=build_seal(args.binary)
    elif args.mode=='worker':
        require(args.row is not None,'worker row missing')
        result=run_worker(args.binary,json.loads(args.row))
    else:
        require(args.row is None,'launch cannot override rows')
        result=launch(args.binary)
    print(json.dumps(result,sort_keys=True))


if __name__=='__main__': main()
