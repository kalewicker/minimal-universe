#!/usr/bin/env python3
"""Static R03 panel registry. Does not import an engine or execute world events."""
import argparse
from collections import Counter
from hashlib import sha256
from itertools import combinations_with_replacement, product
import json
from math import factorial
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def digest(value):
    return sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode('ascii')).hexdigest()


def partition(parent):
    bucket = int.from_bytes(sha256(parent.encode()).digest()[:8], 'big') % 10
    return ('discovery' if bucket < 4 else 'detector-development' if bucket < 6
            else 'validation' if bucket < 8 else 'final-test')


def projection(nodes, edges, k, fresh, horizon):
    if horizon < 0 or edges < 0 or nodes < 0 or k not in range(4):
        raise ValueError('invalid static size inputs')
    events = min(horizon, edges) if k == 0 else (horizon if edges else 0)
    return {'events': events, 'nodes': nodes + int(fresh)*events,
            'edges': edges + (k-1)*events, 'horizon_reachable': events == horizon}


def rows(design, seeds):
    arcs = tuple(product(range(3), repeat=2))
    index = 0
    for k in range(4):
        for rhs in combinations_with_replacement(arcs, k):
            rule_id = digest({'schema':'mu-rule-v1', 'rhs':rhs})
            fresh = any(2 in arc for arc in rhs)
            for seed_id, seed in seeds.items():
                states = [projection(seed['nodes'], len(seed['edges']), k, fresh, t)
                          for t in design['snapshots']]
                reachable = [s for s in states if s['horizon_reachable']]
                for replicate in range(design['uniform_replicates']):
                    parent = f"mu/{design['design_id']}/{rule_id}/{seed_id}/{replicate}"
                    for scheduler in design['schedulers']:
                        if scheduler != 'uniform' and replicate != 0:
                            continue
                        yield {'rule_index':index, 'rule_id':rule_id, 'rhs':list(rhs),
                               'seed_id':seed_id, 'seed_sha256':digest(seed),
                               'replicate':replicate, 'scheduler':scheduler,
                               'parent_key':parent, 'job_key':parent+'/'+scheduler,
                               'partition':partition(parent),
                               'rng_seed':int.from_bytes(sha256(('rng|'+parent).encode()).digest()[:8], 'big'),
                               'execution_status':'not_executed',
                               'projected_snapshots':states,
                               'raw_null_permutation_bound':sum(factorial(s['edges']) for s in reachable)}
            index += 1


def summarize(records):
    jobs, parents, rule_ids, cells = Counter(), {}, set(), set()
    endpoint = Counter()
    work = Counter()
    for row in records:
        jobs[row['partition']] += 1
        parents[row['parent_key']] = row['partition']
        rule_ids.add(row['rule_id'])
        cells.add((row['rule_id'],row['seed_id']))
        last = row['projected_snapshots'][-1]
        endpoint['reachable' if last['horizon_reachable'] else 'terminated_before_horizon'] += 1
        if last['horizon_reachable'] and last['nodes'] < 2:
            endpoint['primary_undefined_at_horizon'] += 1
        work[row['partition']] += row['raw_null_permutation_bound']
    return dict(jobs=sum(jobs.values()), rules=len(rule_ids), rule_seed_cells=len(cells),
                parent_groups=len(parents), jobs_by_partition=dict(sorted(jobs.items())),
                parents_by_partition=dict(sorted(Counter(parents.values()).items())),
                projected_endpoint_statuses=dict(endpoint),
                raw_null_permutation_bounds_by_partition=dict(sorted(work.items())),
                world_transitions=0, all_job_status='not_executed', runtime_feasibility='not_measured',
                motif_coverage='unknown_without_execution', null_informativeness='unknown_without_execution')


def source_hashes():
    files = ['protocols/r00.json','protocols/r02-measurement-contract.json','protocols/r03a.json',
             'protocols/r03b-design.json','scripts/plan_r03.py','scripts/verify_r03_plan.py',
             'tests/test_r03_plan.py']
    return {p:sha256((ROOT/p).read_bytes()).hexdigest() for p in files}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--manifest',type=Path,required=True)
    parser.add_argument('--output',type=Path,required=True)
    args=parser.parse_args()
    if args.manifest.exists() or args.output.exists():
        raise SystemExit('refusing to overwrite evidence')
    design=json.loads((ROOT/'protocols/r03b-design.json').read_text())
    seeds=json.loads((ROOT/'protocols/r00.json').read_text())['seeds']
    records=list(rows(design,seeds))
    args.manifest.parent.mkdir(parents=True,exist_ok=True)
    with args.manifest.open('x') as stream:
        for row in records:
            stream.write(json.dumps(row,sort_keys=True,separators=(',',':'))+'\n')
    result={'protocol_id':'R03a-v1','status':'generated_pending_independent_verification',
            'summary':summarize(records),'source_sha256':source_hashes(),
            'manifest_sha256':sha256(args.manifest.read_bytes()).hexdigest(),
            'scientific_status':'untested','launch_authorized':False}
    with args.output.open('x') as stream:
        json.dump(result,stream,indent=2,sort_keys=True);stream.write('\n')
    print(json.dumps(result['summary'],sort_keys=True))


if __name__=='__main__':
    main()
