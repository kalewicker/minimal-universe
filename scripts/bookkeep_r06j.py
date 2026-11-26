"""Validate synthetic terminal outcome records and summarize exact bounds."""
import argparse
from collections import Counter
from fractions import Fraction
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from analysis.assay_eligibility_v1 import patches
from analysis.edge_budget_v1 import score
from analysis.g2_observer_v1 import graph
from analysis.measurements import partition
from scripts.design_r06i import HORIZON, THRESHOLDS, bounds, canonical, require

PREFIX = 'mu/G2-terminal-fixture-v1/'
SCHEDULERS = ('lex_first', 'lex_last', 'uniform_match')
COMPONENTS = ('restricted_progress', 'reach_50', 'joint_q_ge_0',
              'joint_q_ge_half', 'joint_q_ge_1')


def fields(record, expected, label):
    require(isinstance(record, dict) and set(record) == set(expected.split()),
            f'invalid {label} fields')


def snapshot(state):
    fields(state, 'nodes edges', 'snapshot')
    require(isinstance(state['edges'], list)
            and all(isinstance(edge, list) and len(edge) == 2 for edge in state['edges']),
            'edges must be an array of endpoint pairs')
    return graph(state['nodes'], state['edges'])


def positive_weight(value):
    require(isinstance(value, list) and len(value) == 2
            and all(type(part) is int and part > 0 for part in value),
            'weight must contain two positive integers')
    return Fraction(*value)


def outcome(row):
    status, events, endpoint = (row[key] for key in ('status', 'events', 'endpoint'))
    require(isinstance(status, str), 'invalid status')
    if status in ('terminal', 'reached'):
        edges = snapshot(endpoint)
        if status == 'terminal':
            require(not any(first != second and edge[1] == other[0]
                            for first, edge in enumerate(edges)
                            for second, other in enumerate(edges)),
                    'terminal snapshot still has an eligible path')
        value = score(endpoint['nodes'], edges)
        category = f"{status}_{'empty' if value is None else 'nonempty'}"
        return bounds(status, events, value), category

    require(endpoint is None, 'unresolved record has an endpoint')
    if status == 'reached_snapshot_missing':
        require(type(events) is int and events == HORIZON, 'missing snapshot requires known reach')
        return ((1, 1), (1, 1), *(((0, 1),) * len(THRESHOLDS))), status
    return bounds(status, events, None), status


def summarize(payload):
    fields(payload, 'parents branches', 'input')
    require(all(isinstance(payload[key], list) for key in payload), 'expected roster arrays')
    roster = {}
    for parent in payload['parents']:
        fields(parent, 'key weight initial', 'parent')
        key = parent['key']
        require(isinstance(key, str) and key.startswith(PREFIX) and len(key) > len(PREFIX)
                and key not in roster, 'invalid or duplicate fixture parent')
        initial = parent['initial']
        arcs = snapshot(initial)
        candidates = patches(initial['nodes'], arcs)
        status = {0: 'ineligible', 1: 'eligible'}.get(len(candidates), 'ambiguous_patch')
        roster[key] = dict(partition=partition(key), weight=positive_weight(parent['weight']),
                           admission=status, patches=candidates)

    planned = {(key, scheduler, orientation)
               for key, parent in roster.items() if parent['admission'] == 'eligible'
               for scheduler in SCHEDULERS for orientation in range(4)}
    observed = {}
    for row in payload['branches']:
        fields(row, 'parent partition scheduler orientation patch status events endpoint', 'branch')
        key, scheduler, orientation = (row[k] for k in ('parent', 'scheduler', 'orientation'))
        require(isinstance(key, str) and isinstance(scheduler, str) and type(orientation) is int,
                'invalid slot identity')
        slot = (key, scheduler, orientation)
        require(slot in planned and slot not in observed, 'unexpected or duplicate branch slot')
        parent = roster[key]
        require(row['partition'] == parent['partition'], 'partition inheritance mismatch')
        patch = row['patch']
        require(isinstance(patch, list) and all(type(vertex) is int for vertex in patch)
                and tuple(patch) == parent['patches'][0], 'patch mismatch')
        observed[slot] = outcome(row)
    require(set(observed) == planned, 'missing branch record; use explicit not_started')

    groups = {key: roster[key] for key in sorted(roster) if roster[key]['admission'] == 'eligible'}
    total_weight = sum((parent['weight'] for parent in groups.values()), Fraction(0))
    results = {}
    for scheduler in SCHEDULERS:
        rows = []
        statuses = Counter()
        for key in groups:
            orientations = [observed[key, scheduler, index] for index in range(4)]
            statuses.update(category for _, category in orientations)
            values = [intervals for intervals, _ in orientations]
            paired = []
            for t0, t1, s0, s1 in zip(*values):
                lower = Fraction(t0[0] + t1[0] - s0[1] - s1[1], 2)
                upper = Fraction(t0[1] + t1[1] - s0[0] - s1[0], 2)
                paired.append((lower, upper))
            rows.append(dict(parent=key, bounds=dict(zip(COMPONENTS, paired))))
        mean = None
        if total_weight:
            mean = {
                component: tuple(sum(groups[row['parent']]['weight'] * row['bounds'][component][side]
                                     for row in rows) / total_weight for side in (0, 1))
                for component in COMPONENTS
            }
        results[scheduler] = dict(parent_count=len(rows), branch_count=4 * len(rows),
                                  outcome_counts=dict(statuses), weighted_bounds=mean, rows=rows)
    return dict(
        roster_count=len(roster), planned_branch_count=len(planned),
        admission_counts=dict(Counter(parent['admission'] for parent in roster.values())),
        admitted_weight=total_weight,
        roster={key: roster[key] for key in sorted(roster)},
        by_scheduler=results, scientific_status='untested',
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('fixture', type=Path)
    args = parser.parse_args()

    def unique_object(items):
        result = dict(items)
        require(len(result) == len(items), 'duplicate JSON object key')
        return result

    result = summarize(json.loads(args.fixture.read_bytes(), object_pairs_hook=unique_object))
    sys.stdout.buffer.write(canonical(result))


if __name__ == '__main__':
    main()
