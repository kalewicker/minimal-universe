#!/usr/bin/env python3
"""Pilot worker: native trace, checked event replay, exact bounded observations."""
import argparse
from fractions import Fraction
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'analysis'))
import measurements as m
from verify_r01 import config_text


def fraction(value):
    return None if value is None else [value.numerator,value.denominator]


def observation(nodes,active):
    edges=[(u,v) for _,u,v,_ in active]
    density=m.reciprocal_density(nodes,edges)
    null=m.degree_null(nodes,edges)
    mean=sum((score*weight for score,weight in null['distribution'].items()),Fraction()) if density is not None else None
    return {'nodes':nodes,'edges':len(edges),'motifs':m.motifs(nodes,edges),
            'density':fraction(density),'null_status':null['status'],
            'null_distribution':[[fraction(score),fraction(weight)] for score,weight in sorted(null['distribution'].items())],
            'null_mean':fraction(mean),'density_minus_null_mean':fraction(density-mean) if density is not None else None}


def observe(native,fixture,rhs,horizons):
    active=[[i,u,v,None] for i,(u,v) in enumerate(fixture['edges'])]
    nodes=fixture['nodes'];next_id=len(active)
    snapshots=[{'event':0,'status':'observed','measurement':observation(nodes,active)}]
    for time,event in enumerate(native['events']):
        index,consumed,u,v,parent,fresh,first,count,_=event
        found=[edge for edge in active if edge[0]==consumed]
        if index!=time or len(found)!=1 or found[0][1:]!=[u,v,parent] or first!=next_id or count!=len(rhs):
            raise ValueError('invalid event provenance')
        uses_fresh=any(2 in arc for arc in rhs)
        if fresh!=(nodes if uses_fresh else None): raise ValueError('invalid fresh node')
        bindings=(u,v,nodes)
        active=[edge for edge in active if edge[0]!=consumed]
        active.extend([next_id+j,bindings[a],bindings[b],time] for j,(a,b) in enumerate(rhs))
        next_id+=len(rhs);nodes+=uses_fresh
        if time+1 in horizons:
            snapshots.append({'event':time+1,'status':'observed','measurement':observation(nodes,active)})
    if native['edges']!=active or native['nodes']!=nodes or native['next_edge']!=next_id:
        raise ValueError('replayed endpoint mismatch')
    for horizon in horizons:
        if horizon>len(native['events']):
            status='terminated_before_horizon' if native['status']=='no_eligible_edge' else 'censored_before_horizon'
            snapshots.append({'event':horizon,'status':status,'measurement':None})
    return snapshots


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary',type=Path,required=True)
    parser.add_argument('--fixture',required=True)
    parser.add_argument('--scheduler',required=True)
    args=parser.parse_args()
    protocol=json.loads((ROOT/'protocols/r03p.json').read_text())
    fixture=next((f for f in protocol['fixtures'] if f['id']==args.fixture),None)
    if fixture is None or args.scheduler not in protocol['schedulers']:
        raise SystemExit('unregistered engineering fixture')
    limits=protocol['graph_limits']
    budget=dict(rng_seed=protocol['rng_seed'],max_events=limits['events'],
                max_nodes=limits['nodes'],max_edges=limits['edges'])
    with tempfile.TemporaryDirectory(prefix='mu-pilot-') as directory:
        path=Path(directory)/'config.txt'
        path.write_text(config_text(fixture,fixture['rhs'],args.scheduler,budget))
        # The outer supervisor bounds this entire worker plus its native child.
        completed=subprocess.run([str(args.binary.resolve()),'graph',str(path)],capture_output=True,text=True,check=True)
    native=json.loads(completed.stdout)
    print(json.dumps({'native':native,'snapshots':observe(native,fixture,fixture['rhs'],protocol['snapshots'])},sort_keys=True))


if __name__=='__main__': main()
