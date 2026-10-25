"""Registered exact G2 calibration. No native runs, sampled trajectories or selection."""
import argparse
from collections import Counter
from copy import deepcopy
from fractions import Fraction
import hashlib
from itertools import combinations, combinations_with_replacement, permutations, product
import json
from pathlib import Path
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from analysis import g2_measurements as measurement
from analysis.measurements import partition as r02_partition
from audit_r04 import require
from audit_r05 import audit as audit_r05


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def encoded(value):
    if isinstance(value, Fraction):
        return [value.numerator, value.denominator]
    if isinstance(value, dict):
        return {str(key): encoded(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [encoded(item) for item in value]
    return value


def canonical(value):
    return json.dumps(encoded(value), sort_keys=True, separators=(',', ':'))


def fixtures(edge_counts):
    for nodes in (1, 2, 3):
        for count in edge_counts:
            for arcs in combinations_with_replacement(tuple(product(range(nodes), repeat=2)), count):
                yield nodes, tuple((i, *arc) for i, arc in enumerate(arcs))


def subsets(edges):
    ids = tuple(edge[0] for edge in edges)
    for size in range(len(ids) + 1):
        yield from combinations(ids, size)


def oracle_exposure(nodes, edges, targets):
    del nodes
    choices = [(a, b) for a, b in permutations(edges, 2) if a[2] == b[1]]
    participation = {edge[0]: sum(edge == a or edge == b for a, b in choices) for edge in edges}
    avoided = sum(all(edge[0] not in targets for edge in pair) for pair in choices)
    return dict(matches=len(choices), occurrence_match_counts=participation,
                target_union_matches=len(choices) - avoided,
                probability_avoid=Fraction(avoided, len(choices)) if choices else None,
                status='defined' if choices else 'no_eligible_match')


def oracle_histories(nodes, edges, rhs, max_horizon):
    """Explicit labelled branch histories, without DP merging or shared transition code."""
    levels = [[] for _ in range(max_horizon + 1)]
    terminal = [Fraction() for _ in range(max_horizon)]

    def visit(vertices, active, next_id, depth, probability):
        levels[depth].append(((vertices, tuple(sorted(active)), next_id), probability))
        if depth == max_horizon:
            return
        choices = [pair for pair in permutations(active, 2) if pair[0][2] == pair[1][1]]
        if not choices:
            terminal[depth] += probability
            return
        for first, second in choices:
            substitutions = {0: first[1], 1: first[2], 2: second[2], 3: vertices}
            retained = [edge for edge in active if edge != first and edge != second]
            for offset, arc in enumerate(rhs):
                retained.append((next_id + offset, substitutions[arc[0]], substitutions[arc[1]]))
            creates_vertex = any(arc[0] == 3 or arc[1] == 3 for arc in rhs)
            visit(vertices + int(creates_vertex), retained, next_id + len(rhs), depth + 1,
                  probability * Fraction(1, len(choices)))

    visit(nodes, list(edges), max((edge[0] for edge in edges), default=-1) + 1, 0, Fraction(1))
    return levels, terminal


def oracle_survival(level, terminal, targets):
    reached = sum((mass for _, mass in level), Fraction())
    survivors = sum((mass for (_, edges, _), mass in level
                     if all(any(edge[0] == target for edge in edges) for target in targets)), Fraction())
    return dict(reached_mass=reached, surviving_reached_mass=survivors,
                consumed_reached_mass=reached - survivors, unavailable_mass=1 - reached,
                conditional_survival=survivors / reached if reached else None,
                terminal_mass_by_event=terminal,
                status='fully_reached' if reached == 1 else 'unavailable' if reached == 0 else 'partly_unavailable')


def paired_fixture(name='base'):
    parent = 'mu/G2-cal-v1/' + name
    branch = dict(parent=parent, partition=r02_partition(parent), scheduler='uniform_match', horizon=3,
                  status='reached', density_0=Fraction(0), density_h=Fraction(1, 4),
                  matches_0=2, matches_h=2)
    return dict(parent=parent, target=deepcopy(branch), sham=deepcopy(branch))


def paired_checks(names):
    results = {}
    for name in names:
        row = paired_fixture(name)
        rows, expected, rejection = [row], Fraction(), False
        if name == 'zero':
            pass
        elif name == 'immediate_offset':
            row['target'].update(density_0=Fraction(1, 4), density_h=Fraction(1, 2))
        elif name in ('delayed_quarter', 'eligibility_change'):
            row['target']['density_h'] = Fraction(1, 2)
            expected = Fraction(1, 4)
            if name == 'eligibility_change':
                row['sham'].update(matches_0=1, matches_h=0)
        elif name in ('terminal', 'censored', 'undefined_density', 'mixed_incomplete'):
            expected = None
            if name == 'undefined_density':
                row['target']['density_0'] = None
            else:
                branch = row['sham'] if name == 'censored' else row['target']
                branch.update(status='resource_censored' if name == 'censored' else 'terminal_before_horizon',
                              density_h=None, matches_h=None)
            if name == 'mixed_incomplete':
                rows.append(paired_fixture('other-complete'))
        else:
            rejection = True
            if name == 'parent_mismatch':
                row['target']['parent'] += '/child'
            elif name == 'split_mismatch':
                row['target']['partition'] = 'validation' if row['target']['partition'] == 'discovery' else 'discovery'
            elif name == 'horizon_mismatch':
                row['target']['horizon'] = 2
            elif name == 'scheduler_mismatch':
                row['sham']['scheduler'] = 'lex_first'
            elif name == 'duplicate_parent':
                rows.append(deepcopy(row))
            elif name == 'invalid_density':
                row['target']['density_h'] = True
            elif name == 'unknown_status':
                row['target']['status'] = 'unknown'
            elif name == 'invented_endpoint':
                row['target']['status'] = 'terminal_before_horizon'
            elif name == 'missing_match_count':
                row['target']['matches_h'] = None
            elif name == 'missing_field':
                del row['target']['horizon']
            else:
                raise ValueError('unknown paired fixture')
        try:
            actual = measurement.paired_bookkeeping(rows, 3)
        except ValueError:
            require(rejection, 'unexpected paired rejection: ' + name)
            results[name] = dict(status='rejected_as_registered')
            continue
        require(not rejection and actual['mean_effect'] == expected, 'paired arithmetic: ' + name)
        require(actual['scientific_acceptance'] is False and actual['sham_validity'] == 'not_established',
                'paired scope')
        if name == 'eligibility_change':
            require(actual['pairs'][0]['initial_eligibility_changed'] and
                    actual['pairs'][0]['endpoint_eligibility_changed'], 'eligibility hidden')
        if name == 'mixed_incomplete':
            require(actual['total_pairs'] == 2 and actual['complete_pairs'] == 1 and
                    actual['mean_effect'] is None, 'unavailable pair dropped')
        results[name] = actual
    return results


def named_controls():
    weighted = measurement.exposure(3, [(0, 0, 1), (1, 1, 2), (2, 1, 2), (3, 2, 0)], [0, 3])
    require(weighted['matches'] == 5 and weighted['occurrence_match_counts'] == {0: 3, 1: 2, 2: 2, 3: 3}
            and weighted['target_union_matches'] == 5 and weighted['probability_avoid'] == 0, 'union exposure')
    loops = measurement.exposure(1, [(0, 0, 0), (1, 0, 0)], [0])
    require(loops['probability_avoid'] == 0, 'G1 counterexample')
    graph = [(0, 0, 0), (1, 0, 1), (2, 1, 1), (3, 2, 2)]
    partial = measurement.survival(measurement.exact_horizon(3, graph, [(0, 0)], 2), [3])
    require(partial['reached_mass'] == partial['surviving_reached_mass'] == Fraction(1, 2) and
            partial['unavailable_mass'] == Fraction(1, 2) and partial['conditional_survival'] == 1,
            'partial horizon')
    later = measurement.survival(measurement.exact_horizon(3, graph, [(0, 0)], 3), [3])
    require(later['conditional_survival'] is None and later['terminal_mass_by_event'] ==
            [Fraction(), Fraction(1, 2), Fraction(1, 2)], 'partial terminal mass')
    isolated = [(0, 0, 0), (1, 0, 0), (2, 1, 2)]
    nonparticipant = measurement.exposure(3, isolated, [2])
    first = measurement.survival(measurement.exact_horizon(3, isolated, [], 1), [2])
    second = measurement.survival(measurement.exact_horizon(3, isolated, [], 2), [2])
    require(nonparticipant['probability_avoid'] == first['surviving_reached_mass'] == 1 and
            second['unavailable_mass'] == 1 and second['conditional_survival'] is None,
            'nonparticipating target endpoint')
    return dict(weighted_union_exposure=weighted,
                g1_formula_counterexample=dict(g2_avoid=loops['probability_avoid'],
                                                inapplicable_g1_value=Fraction(1, 2)),
                partial_horizon=dict(horizon_2=partial, horizon_3=later),
                nonparticipating_target_then_unavailable=dict(exposure=nonparticipant, horizon_1=first, horizon_2=second))


def preflight(protocol):
    require(protocol['protocol_id'] == 'R05c-v1' and not protocol['discovery_authorized'] and
            not protocol['holdout_authorized'] and not protocol['promotion_authorized'], 'calibration scope')
    for name, digest in protocol['prerequisite_sha256'].items():
        require(sha(ROOT / name) == digest, 'prerequisite digest: ' + name)
    prior = [json.loads((ROOT / name).read_text()) for name in ('reports/r05b-release.json', 'reports/r05b-sanitize.json')]
    require(prior[0]['audit_status'] == prior[1]['audit_status'] == 'pass' and
            prior[0]['outcome'] == prior[1]['outcome'], 'R05b prerequisite outcome')
    for receipt in prior:
        for name, digest in receipt['source_sha256'].items():
            require(sha(ROOT / name) == digest, 'R05b source: ' + name)
    require(audit_r05() == json.loads((ROOT / 'reports/r05a.json').read_text()), 'R05a prerequisite')
    require(protocol['measurement_domain'] == dict(max_nodes=measurement.MAX_NODES,
            max_edges=measurement.MAX_EDGES, max_horizon=measurement.MAX_HORIZON,
            max_frontier_states=measurement.MAX_FRONTIER, max_matches=measurement.MAX_MATCHES), 'measurement domain')
    require(protocol['exposure']['nodes'] == protocol['survival']['nodes'] == [1, 2, 3] and
            protocol['exposure']['edge_counts'] == [0, 1, 2, 3, 4] and
            protocol['survival']['edge_counts'] == [0, 1, 2, 3] and
            protocol['survival']['horizons'] == [0, 1, 2, 3] and
            protocol['survival']['scheduler'].startswith('uniform over all ordered'), 'registered fixture scope')


def calibrate(stream=None):
    start = time.monotonic()
    protocol = json.loads((ROOT / 'protocols/r05c.json').read_text())
    preflight(protocol)
    sources = ('protocols/r05c.json', 'analysis/g2_measurements.py', 'analysis/measurements.py',
               'scripts/calibrate_r05c.py', 'tests/test_g2_measurements.py', 'docs/r05c-measurements.md')
    source_hashes = {name: sha(ROOT / name) for name in sources}
    counts, statuses = Counter(), Counter()
    digest = hashlib.sha256()
    trace_bytes = 0

    def emit(row):
        nonlocal trace_bytes
        data = (canonical(row) + '\n').encode()
        digest.update(data)
        trace_bytes += len(data)
        require(trace_bytes <= protocol['budgets']['retained_bytes'] - 65536, 'trace byte budget')
        require(time.monotonic() - start <= protocol['budgets']['global_wall_seconds'], 'global deadline')
        if stream:
            stream.write(data)

    for graph_id, (nodes, edges) in enumerate(fixtures(protocol['exposure']['edge_counts'])):
        counts['exposure_graphs'] += 1
        for target in subsets(edges):
            actual = measurement.exposure(nodes, edges, target)
            require(actual == oracle_exposure(nodes, edges, target), 'exposure oracle mismatch')
            require(sum(actual['occurrence_match_counts'].values()) == 2 * actual['matches'], 'incidence conservation')
            counts['exposure_cases'] += 1
            emit(dict(kind='exposure', graph=graph_id, targets=target, result=actual))
    rules = protocol['survival']['rhs']
    for graph_id, (nodes, edges) in enumerate(fixtures(protocol['survival']['edge_counts'])):
        counts['survival_graphs'] += 1
        targets = list(subsets(edges))
        counts['survival_target_sets'] += len(targets)
        for rule_id, rhs in enumerate(rules):
            levels, terminal = oracle_histories(nodes, edges, rhs, max(protocol['survival']['horizons']))
            counts['explicit_history_nodes'] += sum(map(len, levels))
            for horizon in protocol['survival']['horizons']:
                distribution = measurement.exact_horizon(nodes, edges, rhs, horizon)
                expected = Counter()
                for state, probability in levels[horizon]:
                    expected[state] += probability
                require(distribution.states == dict(expected) and list(distribution.terminal_by_event) == terminal[:horizon],
                        'endpoint distribution or terminal oracle mismatch')
                counts['distribution_cases'] += 1
                emit(dict(kind='distribution', graph=graph_id, rule=rule_id, horizon=horizon,
                          states=[dict(state=state, mass=mass) for state, mass in sorted(distribution.states.items())],
                          terminal=distribution.terminal_by_event))
                for target in targets:
                    actual = measurement.survival(distribution, target)
                    require(actual == oracle_survival(levels[horizon], terminal[:horizon], target), 'survival oracle mismatch')
                    counts['survival_cases'] += 1
                    statuses[actual['status']] += 1
                    emit(dict(kind='survival', graph=graph_id, rule=rule_id, horizon=horizon, targets=target, result=actual))
    for key, expected in [('exposure_graphs', protocol['exposure']['expected_graphs']),
                          ('exposure_cases', protocol['exposure']['expected_cases']),
                          ('survival_graphs', protocol['survival']['expected_graphs']),
                          ('survival_target_sets', protocol['survival']['expected_target_sets']),
                          ('distribution_cases', protocol['survival']['expected_distribution_cases']),
                          ('survival_cases', protocol['survival']['expected_survival_cases'])]:
        require(counts[key] == expected, 'registered count mismatch: ' + key)
    controls = named_controls()
    require(set(controls) == set(protocol['named_controls']), 'named control matrix')
    paired = paired_checks(protocol['paired_cases'])
    require(all(sha(ROOT / name) == digest for name, digest in source_hashes.items()), 'source changed')
    require(time.monotonic() - start <= protocol['budgets']['global_wall_seconds'], 'final global deadline')
    return encoded(dict(protocol_id=protocol['protocol_id'], audit_status='pass', counts=dict(counts),
                        survival_availability=dict(statuses), named_controls=controls, paired_controls=paired,
                        trace_sha256=digest.hexdigest(), trace_bytes=trace_bytes,
                        source_sha256=source_hashes, prerequisite_sha256=protocol['prerequisite_sha256'],
                        scientific_status='untested', exact_toy_history_expansion=True,
                        native_world_runs=0, discovery_runs=0, holdout_jobs_executed=0,
                        promotion_authorized=False, preserved_intervention_horizon=50))


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument('--output-directory', type=Path)
    group.add_argument('--verify', type=Path)
    args = parser.parse_args()
    if args.verify:
        require(calibrate() == json.loads(args.verify.read_text()), 'R05c receipt mismatch')
        print('R05c exact calibration receipt verified without writing artifacts')
    else:
        args.output_directory.mkdir(parents=True, exist_ok=False)
        start = time.monotonic()
        execution = dict(protocol_id='R05c-v1', audit_status='fail')
        with (args.output_directory / 'started.json').open('x') as stream:
            json.dump(dict(protocol_sha256=sha(ROOT / 'protocols/r05c.json')), stream)
        try:
            with (args.output_directory / 'calibration.jsonl').open('xb') as stream:
                result = calibrate(stream)
            with (args.output_directory / 'calibration.json').open('x') as stream:
                json.dump(result, stream, indent=2, sort_keys=True)
                stream.write('\n')
            execution.update(audit_status='pass', calibration_sha256=sha(args.output_directory / 'calibration.json'),
                             trace_sha256=sha(args.output_directory / 'calibration.jsonl'))
        except Exception as error:
            execution['error'] = f'{type(error).__name__}: {error}'.replace(str(ROOT), '<repo>')
        execution['elapsed_seconds'] = time.monotonic() - start
        execution['retained_bytes_before_receipt'] = sum(p.stat().st_size for p in args.output_directory.iterdir() if p.is_file())
        with (args.output_directory / 'execution.json').open('x') as stream:
            json.dump(execution, stream, indent=2, sort_keys=True)
            stream.write('\n')
        print(canonical(execution))
        raise SystemExit(0 if execution['audit_status'] == 'pass' else 1)
