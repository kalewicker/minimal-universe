"""Execute the complete registered G2 engineering matrix and retain every output."""
import argparse
from collections import Counter
import hashlib
from itertools import combinations_with_replacement, product
import json
from pathlib import Path
import subprocess
import time

from audit_r04 import require
from audit_r05 import audit as audit_r05
from g2_reference import Reference

ROOT = Path(__file__).resolve().parents[1]


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def canonical(value):
    return json.dumps(value, sort_keys=True, separators=(',', ':'))


def cases(protocol):
    matrix = protocol['matrix']
    base = dict(rng=matrix['rng_seed'], limits=matrix['limits'])
    for length in range(4):
        for rhs in combinations_with_replacement(tuple(product(range(4), repeat=2)), length):
            for seed in matrix['seeds']:
                for scheduler in matrix['schedulers']:
                    yield dict(kind='rule', seed_id=seed['id'], config=dict(
                        base, rhs=rhs, nodes=seed['nodes'], seed=seed['edges'], scheduler=scheduler))
    for seed in matrix['extra_seeds']:
        for rhs in matrix['extra_rhs']:
            for scheduler in matrix['schedulers']:
                yield dict(kind='extra', seed_id=seed['id'], config=dict(
                    base, rhs=rhs, nodes=seed['nodes'], seed=seed['edges'], scheduler=scheduler))
    for nodes in (1, 2, 3):
        for count in range(5):
            for graph in combinations_with_replacement(tuple(product(range(nodes), repeat=2)), count):
                yield dict(kind='static', config=dict(base, nodes=nodes, seed=graph, rhs=[],
                           scheduler='lex_first', limits=dict(base['limits'], events=0)))


def config_text(config):
    limit = config['limits']
    lines = ['MU_G2_CONFIG_1', f"{config['nodes']} {config['rng']} {config['scheduler']}",
             ' '.join(str(limit[k]) for k in ('events', 'nodes', 'edges', 'matches')),
             str(len(config['rhs']))]
    lines += [f'{a} {b}' for a, b in config['rhs']]
    lines += [str(len(config['seed']))]
    lines += [f'{a} {b}' for a, b in config['seed']]
    return '\n'.join(lines) + '\n'


def retained_bytes(directory):
    return sum(p.stat().st_size for p in directory.rglob('*') if p.is_file())


def native(command, output, directory, budget, deadline):
    with output.open('xb') as stdout, output.with_suffix('.stderr').open('xb') as stderr:
        start = time.monotonic()
        process = subprocess.Popen(command, stdout=stdout, stderr=stderr)
        try:
            while process.poll() is None:
                require(time.monotonic() - start <= budget['per_process_wall_seconds'], 'native process deadline')
                require(time.monotonic() <= deadline, 'global deadline')
                require(retained_bytes(directory) <= budget['retained_bytes'] - 65536, 'retained byte cap')
                time.sleep(0.1)
            require(process.returncode == 0, 'native process failed; stderr preserved')
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()


def execute(binary, directory, build_kind, compare=None):
    directory.mkdir(parents=True, exist_ok=False)
    start = time.monotonic()
    result = dict(protocol_id='R05b-v1', audit_status='fail', scientific_status='untested',
                  build_kind=build_kind, campaign_executed=False, holdout_jobs_executed=0)
    try:
        protocol = json.loads((ROOT / 'protocols/r05b.json').read_text())
        budget = protocol['budgets']
        deadline = start + budget['global_wall_seconds']
        require(sha(ROOT / 'docs/r05-two-edge.md') == protocol['design_sha256'], 'design digest')
        require(sha(ROOT / 'reports/r05a.json') == protocol['prerequisite_sha256'], 'prerequisite digest')
        require(audit_r05() == json.loads((ROOT / 'reports/r05a.json').read_text()), 'R05a audit')
        sources = sorted([str(p.relative_to(ROOT)) for p in (ROOT / 'g2').glob('*') if p.is_file()] +
                         ['protocols/r05b.json', 'scripts/verify_r05b.py', 'scripts/g2_reference.py',
                          'tests/test_g2_reference.py', 'reports/r05a.json'])
        source_hashes = {name: sha(ROOT / name) for name in sources}
        result.update(source_sha256=source_hashes, binary_sha256=sha(binary))
        (directory / 'started.json').write_text(canonical(result) + '\n')
        rows = list(cases(protocol))
        counts = Counter(row['kind'] for row in rows)
        matrix = protocol['matrix']
        require(counts == {'rule': matrix['expected_rule_cases'], 'extra': matrix['expected_extra_cases'],
                           'static': matrix['expected_static_cases']} and
                len(rows) == matrix['expected_total_cases'], 'registered case counts')
        manifest = directory / 'manifest.jsonl'
        with manifest.open('x') as stream:
            for row in rows:
                stream.write(canonical(row) + '\n')
        batch = directory / 'input.txt'
        with batch.open('x') as stream:
            stream.write(f'MU_G2_BATCH_1 {len(rows)}\n')
            for row in rows:
                stream.write(config_text(row['config']))
        binary = binary.resolve()
        output = directory / 'native.jsonl'
        native([str(binary), 'batch', str(batch.resolve()), str((directory / 'checkpoints').resolve()),
                str(matrix['checkpoint_prefix'])], output, directory, budget, deadline)
        statuses, ancestry = Counter(), Counter()
        event_count = 0
        final_digest = hashlib.sha256()
        with output.open() as stream:
            for index, row in enumerate(rows):
                observed = json.loads(next(stream))
                require(observed['index'] == index, 'native case index')
                ref = Reference(row['config'])
                require(observed['initial_matches'] == ref.matches(), f'initial matches at {index}')
                mid = ref.prefix(matrix['checkpoint_prefix'])
                require(observed['mid'] == mid, f'prefix replay at {index}')
                final = ref.run()
                require(observed['final'] == final, f'final replay at {index}')
                statuses[final['status']] += 1
                event_count += len(final['events'])
                for event in final['events']:
                    ancestry[str(len(event['parents']))] += 1
                final_digest.update((canonical(final) + '\n').encode())
                require(time.monotonic() <= deadline, 'global replay deadline')
            require(not stream.read(), 'extra native rows')
        require(ancestry['2'] > 0, 'two-parent event coverage absent')
        restore_list = directory / 'restore.txt'
        with restore_list.open('x') as stream:
            stream.write(str(len(rows)) + '\n')
            for index in range(len(rows)):
                stream.write(str((directory / 'checkpoints' / f'{index}.g2').resolve()) + '\n')
        resumed = directory / 'restored.jsonl'
        native([str(binary), 'resume-batch', str(restore_list.resolve())], resumed,
               directory, budget, deadline)
        with output.open() as original, resumed.open() as restored:
            for index in range(len(rows)):
                full, restarted = json.loads(next(original)), json.loads(next(restored))
                require(restarted == {'index': index, 'final': full['final']}, f'restored replay at {index}')
                require(time.monotonic() <= deadline, 'global restore audit deadline')
            require(not restored.read(), 'extra restored rows')
        outcome = dict(cases=len(rows), case_kinds=dict(counts), events=event_count,
                       final_statuses=dict(statuses), event_parent_counts=dict(ancestry),
                       restored_cases=len(rows), final_state_sha256=final_digest.hexdigest())
        if compare:
            prior = json.loads(compare.read_text())
            require(prior['audit_status'] == 'pass' and prior['outcome'] == outcome and
                    prior['source_sha256'] == source_hashes, 'comparison receipt mismatch')
        require(all(sha(ROOT / name) == value for name, value in source_hashes.items()), 'source changed during execution')
        require(sha(binary) == result['binary_sha256'], 'binary changed during execution')
        # Bind every checkpoint in index order without publishing 15,433 individual hashes.
        checkpoint_digest = hashlib.sha256()
        for index in range(len(rows)):
            checkpoint_digest.update(f'{index}:{sha(directory / "checkpoints" / f"{index}.g2")}\n'.encode())
        result.update(audit_status='pass', outcome=outcome,
                      checkpoint_collection_sha256=checkpoint_digest.hexdigest(),
                      files={name: sha(directory / name) for name in
                             ('manifest.jsonl', 'input.txt', 'native.jsonl', 'restored.jsonl')})
        require(time.monotonic() <= deadline, 'global finalization deadline')
        require(retained_bytes(directory) <= budget['retained_bytes'] - 65536, 'final retained byte cap')
    except Exception as error:
        result['error'] = f'{type(error).__name__}: {error}'.replace(str(ROOT), '<repo>')
    result['elapsed_seconds'] = time.monotonic() - start
    result['retained_bytes_before_receipt'] = retained_bytes(directory)
    with (directory / 'receipt.json').open('x') as stream:
        json.dump(result, stream, indent=2, sort_keys=True)
        stream.write('\n')
    return result


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--binary', type=Path, required=True)
    parser.add_argument('--directory', type=Path, required=True)
    parser.add_argument('--build-kind', choices=('release', 'asan-ubsan'), required=True)
    parser.add_argument('--compare', type=Path)
    args = parser.parse_args()
    result = execute(args.binary, args.directory, args.build_kind, args.compare)
    print(canonical(result))
    raise SystemExit(0 if result['audit_status'] == 'pass' else 1)
