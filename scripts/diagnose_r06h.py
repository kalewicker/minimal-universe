"""Audit saved R06g histories and costs without applying any graph rewrites."""
import argparse
from collections import Counter, defaultdict
from decimal import Decimal
from hashlib import sha256
import json
from pathlib import Path
import sys
from time import monotonic

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from scripts.calibrate_r06g import canonical, cases, config_text, require, rules


def read_json(path):
    return json.loads(path.read_bytes())


def endpoint_matches(edges):
    incoming = Counter(edge[2] for edge in edges)
    outgoing = Counter(edge[1] for edge in edges)
    count = sum(incoming[v] * outgoing[v] for v in incoming)
    count -= sum(source == target for _, source, target, _ in edges)
    has_distinct_pair = any(
        first[0] != second[0] and first[2] == second[1]
        for first in edges for second in edges
    )
    require((count > 0) == has_distinct_pair, 'endpoint match checks disagree')
    return count


def verify_endpoint(case, result, row):
    rhs = case['config']['rhs']
    count = len(result['events'])
    edges = result['edges']
    require(0 <= count <= 50, 'event count outside registered horizon')
    require(len(edges) == 4 + (len(rhs) - 2) * count, 'edge balance')
    require(result['nodes'] == 4 + count * any(3 in arc for arc in rhs), 'node balance')
    require(len({edge[0] for edge in edges}) == len(edges), 'duplicate endpoint ID')
    require(result['scheduler'] == case['config']['scheduler'], 'native scheduler')
    patch = result['intervention']
    require((patch['patch'], patch['orientation'], patch['branch_seed']) ==
            (list(case['patch']), case['orientation'], case['branch_seed']), 'intervention identity')
    matches = endpoint_matches(edges)
    status = 'no_eligible_match' if matches == 0 else 'event_cap'
    require(result['status'] == status and (matches == 0 or count == 50),
            'unexpected endpoint stopping condition')
    expected = {key: case[key] for key in
                ('law_index', 'parent', 'partition', 'pairing', 'orientation')}
    expected.update(scheduler=result['scheduler'], status=status, events=count,
                    reached_50=count == 50, endpoint_empty=not edges,
                    endpoint_nodes=result['nodes'], endpoint_edges=len(edges),
                    known_shrinking=len(rhs) < 2, execution='completed')
    require(expected == row, 'native endpoint and ledger row differ')


def aggregate(rows, rule_sizes):
    strata = {name: defaultdict(Counter) for name in
              ('rhs_size', 'scheduler', 'pairing', 'orientation', 'partition')}
    stops = defaultdict(Counter)
    stop_shapes = Counter()
    groups = defaultdict(dict)
    for row in rows:
        rule_size = str(rule_sizes[row['law_index']])
        reached = row['reached_50']
        outcome = 'reached' if reached else 'early'
        for name, value in [('rhs_size', rule_size)] + [
                (name, str(row[name])) for name in strata if name != 'rhs_size']:
            counters = strata[name][value]
            counters['slots'] += 1
            counters[outcome] += 1
            counters['events'] += row['events']
            counters['empty'] += row['endpoint_empty']
        if not reached:
            stops[rule_size][str(row['events'])] += 1
            stop_shapes[f"{rule_size}/{row['endpoint_edges']}"] += 1
        group = groups[row['parent'], row['scheduler']]
        require(row['orientation'] not in group, 'duplicate orientation')
        group[row['orientation']] = reached

    completion = Counter()
    for orientations in groups.values():
        require(set(orientations) == {0, 1, 2, 3}, 'orientation denominator')
        target = orientations[0] + orientations[1]
        sham = orientations[2] + orientations[3]
        completion[f'{target}/{sham}'] += 1
    return dict(strata=strata, early_stop_event_histograms=stops,
                early_stop_rhs_size_endpoint_edges=stop_shapes,
                parent_scheduler_completion=dict(completion), parent_scheduler_rows=len(groups))


def audit(evidence, protocol, deadline):
    prior = read_json(ROOT / 'reports/r06g.json')
    execution = read_json(ROOT / 'reports/r06g-execution.json')
    for local, published in [('receipt.json', 'r06g.json'),
                             ('execution.json', 'r06g-execution.json')]:
        require((evidence / local).read_bytes() == (ROOT / 'reports' / published).read_bytes(),
                f'saved {local} differs from published receipt')
    started = read_json(evidence / 'started.json')
    require(started == dict(mode='panel', protocol_sha256=prior['protocol_sha256']),
            'saved panel start binding')
    ledger = (evidence / 'ledger.json').read_bytes()
    require(sha256(ledger).hexdigest() == prior['ledger_sha256'], 'saved ledger hash')
    rows = json.loads(ledger)
    grammar = list(rules())
    hashes = prior['batch_output_sha256']
    require(len(grammar) == len(hashes) == protocol['expected_batches'], 'batch denominator')
    require(len(rows) == protocol['expected_branches'], 'branch denominator')
    files = Counter(ledger=len(ledger), start=(evidence / 'started.json').stat().st_size,
                    receipt=(evidence / 'receipt.json').stat().st_size)
    totals = Counter()
    storage_by_rhs = Counter()
    history_events = 0
    for index, (rhs, digest) in enumerate(zip(grammar, hashes)):
        require(monotonic() < deadline, 'diagnosis deadline')
        folder = evidence / f'batch-{index:04d}'
        batch = list(cases(rhs, index))
        payload = str(len(batch)) + '\n'
        for case in batch:
            fields = (*case['patch'], case['orientation'], case['branch_seed'])
            payload += config_text(case['config']) + ' '.join(map(str, fields)) + '\n'
        input_data = (folder / 'input.txt').read_bytes()
        require(input_data == payload.encode(), f'batch {index} input differs from registered panel')
        data = (folder / 'native.jsonl').read_bytes()
        require(sha256(data).hexdigest() == digest, f'batch {index} native hash')
        lines = data.splitlines()
        saved_rows = rows[index * 36:(index + 1) * 36]
        require(len(lines) == len(batch) == len(saved_rows) == 36, 'batch branch denominator')
        for case, line, row in zip(batch, lines, saved_rows):
            result = json.loads(line)
            verify_endpoint(case, result, row)
            history_events += len(result['events'])
        timing = (folder / 'timing.json').read_bytes()
        measured = json.loads(timing, parse_float=Decimal)
        require(set(measured) == {'native_evolution_seconds', 'native_checkpoint_seconds'}
                and all(value >= 0 for value in measured.values()), 'batch phase timing')
        totals.update(measured)
        files.update(native_histories=len(data), configs=len(input_data), batch_timing=len(timing))
        storage_by_rhs[str(len(rhs))] += len(data)

    breakdown = aggregate(rows, [len(rhs) for rhs in grammar])
    rhs_rows = breakdown['strata']['rhs_size']
    early = sum(row['early'] for row in rhs_rows.values())
    reached = len(rows) - early
    empty = sum(row['empty'] for row in rhs_rows.values())
    require((reached, early, empty, history_events) ==
            tuple(prior[key] for key in ('reached_50', 'early_stop', 'empty_endpoints',
                                         'successful_events')), 'published outcome totals')
    require(dict(Counter(row['status'] for row in rows)) == prior['statuses'], 'published status totals')
    require(breakdown['parent_scheduler_completion'].get('2/2') ==
            prior['all_four_complete_parent_scheduler_rows']
            and breakdown['parent_scheduler_rows'] == 8721, 'all-orientation completion totals')
    require(sum(files.values()) == execution['retained_bytes_before_execution'], 'storage reconciliation')
    for key, value in totals.items():
        require(abs(value - Decimal(str(execution[key]))) < Decimal('0.000000001'),
                f'phase total differs for {key}')
    return dict(
        **breakdown, verified_batches=len(hashes), verified_branches=len(rows),
        reached_50=reached, early_stop=early, empty_endpoints=empty,
        successful_events_in_saved_histories=history_events,
        early_stops_beyond_shrinking=rhs_rows['2']['early'] + rhs_rows['3']['early'],
        retained_bytes_by_file_type=dict(files), native_history_bytes_by_rhs_size=dict(storage_by_rhs),
        seconds={key: execution[key] for key in ('native_process_seconds', 'python_replay_seconds',
                                                 'wall_seconds')} |
                {key: float(value) for key, value in totals.items()},
        new_graph_transitions=0, scientific_status='untested', full_panel_completion='failed',
    )


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--evidence', type=Path, required=True)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument('--output', type=Path)
    mode.add_argument('--verify', type=Path)
    args = parser.parse_args()
    protocol_data = (ROOT / 'protocols/r06h.json').read_bytes()
    protocol = json.loads(protocol_data)
    for name, expected in protocol['pins_sha256'].items():
        require(sha256((ROOT / name).read_bytes()).hexdigest() == expected, f'source pin {name}')
    binding = dict(protocol_id=protocol['protocol_id'],
                   protocol_sha256=sha256(protocol_data).hexdigest())
    if args.output:
        require(not args.output.resolve().is_relative_to(args.evidence.resolve()),
                'output must be outside the saved evidence directory')
        args.output.mkdir(parents=True)
        (args.output / 'started.json').write_bytes(canonical(binding))

    start = monotonic()
    try:
        report = audit(args.evidence, protocol, start + protocol['wall_seconds']) | binding
        require(monotonic() - start <= protocol['wall_seconds'], 'diagnosis deadline')
        data = canonical(report)
        if args.verify:
            require(args.verify.read_bytes() == data, 'diagnosis receipt mismatch')
        else:
            with (args.output / 'receipt.json').open('xb') as file:
                file.write(data)
        print(f"Verified {report['verified_branches']:,} saved branches across "
              f"{report['verified_batches']} batches.")
    except Exception as exc:
        if args.output:
            (args.output / 'failure.json').write_bytes(canonical(binding | dict(error=str(exc))))
        raise


if __name__ == '__main__':
    main()
