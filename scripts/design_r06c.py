#!/usr/bin/env python3
"""Registered static intervention census and conservative planning arithmetic."""
import argparse
from collections import Counter
from fractions import Fraction as F
from hashlib import sha256
from itertools import combinations_with_replacement, permutations, product
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT/'scripts'))
from analysis.edge_budget_v1 import score
from scripts.audit_r05e import certified_radius, oracle_radius


def encoded(x):
    if isinstance(x, F):
        return [x.numerator, x.denominator]
    if isinstance(x, dict):
        return {k: encoded(v) for k, v in x.items()}
    if isinstance(x, (list, tuple)):
        return [encoded(v) for v in x]
    return x


def canonical(x):
    return json.dumps(encoded(x), sort_keys=True, separators=(',', ':')).encode() + b'\n'


def check(condition, message):
    if not condition:
        raise ValueError(message)


def signature(edges):
    return ([sum(b == v for a, b in edges) for v in range(5)],
            [sum(a == v for a, b in edges) for v in range(5)],
            sum(a == b for a, b in edges))


def matches(edges):
    pairs = [(i, j) for i, e in enumerate(edges) for j, f in enumerate(edges)
             if i != j and e[1] == f[0]]
    incoming, outgoing, loops = signature(edges)
    check(len(pairs) == sum(a*b for a, b in zip(incoming, outgoing))-loops,
          'match formula')
    counts = [sum(i == k or j == k for i, j in pairs) for k in range(len(edges))]
    check(counts == [incoming[a]+outgoing[b]-2*(a == b) for a, b in edges],
          'participation formula')
    return len(pairs), counts


def oracle_score(edges):
    return F(2*sum(any(a == u and b == v for a, b in edges) and
                   any(a == v and b == u for a, b in edges)
                   for u in range(5) for v in range(u+1, 5)), len(edges))


def level(ratio):
    n = 0
    while 2**n < ratio:
        n += 1
    return n


def planning(delta, family, queries):
    la, lb = level(20*family), level(5)
    required = 32*max(la, lb)/delta**2
    n = (required.numerator+required.denominator-1)//required.denominator
    check(F(n)*delta**2/32 >= max(la, lb), 'power sufficiency')
    check(F(n-1)*delta**2/32 < max(la, lb), 'power minimal integer')
    slots = n*family
    quota = queries*slots
    radius = None
    if quota:
        _, radius = certified_radius(16384, quota)
        check((_, radius) == oracle_radius(16384, quota, F(1,100), 1000000), 'radius oracle')
    return dict(gap=delta, family_slots=family, parents_per_test=n,
                parent_test_slots=slots, cutoff=delta/2,
                log2_upper_bounds=[la, lb], missing_probability_union_bound=F(1,20*n),
                queries_per_parent_test=queries, query_quota=quota,
                draw_upper_bound=quota*16384, word_upper_bound=quota*4*16384*63,
                conditional_branch_event_targets=100*slots, mc_radius=radius)


def review():
    arcs = list(product(range(4), repeat=2))
    deletion = []
    reference = signature([(0,1),(1,0)])
    for bag in combinations_with_replacement(arcs, 2):
        s = signature(bag)
        deletion.append(dict(edges=bag, degrees_match=s[:2] == reference[:2],
                             full_match=s == reference))
    old = [(0,1),(1,0),(2,3),(3,2)]
    rewires, targets, shams = [], [], []
    for perm in permutations(range(4)):
        edges = list(enumerate(perm))
        loops = any(a == b for a,b in edges)
        retained = bool(set(edges) & set(old))
        kind = 'looped' if loops else 'retains_old_arc' if retained else (
            'sham' if oracle_score(edges) == 1 else 'target')
        rewires.append(dict(edges=edges, kind=kind))
        if kind == 'target': targets.append(edges)
        if kind == 'sham': shams.append(edges)
    external = [(i,4) for i in range(4)] + [(4,i) for i in range(4)] + [(4,4)]
    controls = []
    contexts = 0
    for size in range(4):
        for context in combinations_with_replacement(external, size):
            contexts += 1
            base = old + list(context)
            mb, cb = matches(base)
            for ti, target in enumerate(targets):
                for si, sham in enumerate(shams):
                    t, s = target+list(context), sham+list(context)
                    mt, ct = matches(t)
                    ms, cs = matches(s)
                    check(signature(base) == signature(t) == signature(s), 'degree/loop control')
                    check(mb == mt == ms and cb[4:] == ct[4:] == cs[4:], 'exposure control')
                    qt, qs = oracle_score(t), oracle_score(s)
                    check(qt == score(5,t) and qs == score(5,s), 'score oracle')
                    check(qs-qt == F(4,len(base)), 'initial contrast')
                    controls.append(dict(context=context, target=ti, sham=si,
                                         matches=mt, score_target=qt, score_sham=qs,
                                         new_participation_target=ct[:4], new_participation_sham=cs[:4]))
    counts = dict(deletion_bags=len(deletion), degree_matching_deletions=sum(x['degrees_match'] for x in deletion),
                  fully_matching_deletions=sum(x['full_match'] for x in deletion),
                  rewire_permutations=len(rewires), rewire_classes=dict(Counter(x['kind'] for x in rewires)),
                  contexts=contexts, paired_static_controls=len(controls), power_rows=9, work_rows=27)
    work = [planning(F(1,d), m, q) for d in (20,10,5) for m in (1,3,2907) for q in (0,1,4)]
    ledger = dict(deletions=deletion, rewires=rewires, controls=controls, work=work)
    return counts, ledger


def main():
    parser = argparse.ArgumentParser()
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output', type=Path)
    group.add_argument('--verify', type=Path)
    args = parser.parse_args()
    protocol_path = ROOT/'protocols/r06c.json'
    protocol = json.loads(protocol_path.read_text())
    for name, digest in protocol['pins_sha256'].items():
        check(sha256((ROOT/name).read_bytes()).hexdigest() == digest, 'pin: '+name)
    # Preserve every prior bound source; no prior experiments are re-executed.
    for name in protocol['receipt_chain']:
        receipt = json.loads((ROOT/name).read_text())
        for field in ('pins_sha256','source_sha256','inputs_sha256','prerequisite_sha256'):
            for path, digest in receipt.get(field, {}).items():
                check(sha256((ROOT/path).read_bytes()).hexdigest() == digest, 'prior pin: '+path)
    start = time.monotonic()
    if args.output:
        args.output.mkdir(parents=True, exist_ok=False)
        (args.output/'started.json').write_bytes(canonical(dict(protocol_sha256=sha256(protocol_path.read_bytes()).hexdigest())))
    try:
        counts, ledger = review()
        check(counts == protocol['expected'], 'registered counts')
        receipt = dict(protocol_id=protocol['protocol_id'], protocol_sha256=sha256(protocol_path.read_bytes()).hexdigest(),
                       counts=counts, ledger_sha256=sha256(canonical(ledger)).hexdigest(),
                       work_scenarios=ledger['work'], engineering_status='passed', scientific_status='untested',
                       strict_deletion_sham='infeasible', rewiring='static_controls_passed_only',
                       world_transitions=0, null_draws=0, production_metric_adopted=False, campaign_authorized=False)
        if args.verify:
            check(json.loads(args.verify.read_text()) == encoded(receipt), 'receipt replay')
        else:
            (args.output/'ledger.json').write_bytes(canonical(ledger))
            (args.output/'receipt.json').write_bytes(canonical(receipt))
            elapsed = time.monotonic()-start
            retained = sum(p.stat().st_size for p in args.output.iterdir())
            check(elapsed <= protocol['budgets']['wall_seconds'], 'wall budget')
            check(retained+4096 <= protocol['budgets']['retained_bytes'], 'storage budget')
            (args.output/'execution.json').write_bytes(canonical(dict(status='passed', wall_seconds=elapsed,
                retained_bytes_before_execution=retained, world_transitions=0, null_draws=0)))
        print(json.dumps(counts, sort_keys=True))
    except Exception as exc:
        if args.output:
            (args.output/'failure.json').write_bytes(canonical(dict(error=str(exc), status='failed')))
        raise


if __name__ == '__main__':
    main()
