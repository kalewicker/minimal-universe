# Minimal Universe

Bounded experiments in recursive rewriting, with explicit mathematical limits,
reproducible checks, and a separation between structure and causal organization.

The project has an **R00 mathematical audit** and **R01 reference kernels**. This is not
evidence of emergence, learning, life, or open-ended evolution. No discovery
campaign is included or authorized by the audit protocol.

## Run the audit

Requires Python 3.10+; no third-party dependencies.

```sh
python3 -B -m unittest discover -s tests -v
python3 -B scripts/audit_r00.py --output /tmp/minimal-universe-r00.json
python3 -B scripts/audit_r00.py --verify reports/r00.json
```

The checker refuses to overwrite an output. The checked-in compact receipt binds
the protocol and checker by SHA-256. It contains no machine-local paths or settings.

## Scope and next steps

- [Formal audit](docs/r00-audit.md): proofs and their limits.
- [Corrected semantics](docs/semantics.md): graph baseline and iota evaluator contract.
- [Milestones](docs/roadmap.md): staged implementation boundaries.
- [R00 protocol](protocols/r00.json): fixed fixture matrix and acceptance criteria.

## Build and use the C++20 kernels

```sh
cmake -S . -B build -DCMAKE_BUILD_TYPE=Release
cmake --build build -j 4
ctest --test-dir build --output-on-failure
./build/msru graph examples/feedback.txt
./build/msru iota '(i i)' 10000 100000 x
./build/msru graph examples/feedback.txt 5 /tmp/mu-checkpoint.txt
./build/msru resume /tmp/mu-checkpoint.txt
```

The iota identity example returns normal form `x`. Checkpoint output refuses to
overwrite an existing file. [Kernel contracts](docs/r01-kernels.md) explain the
formats, RNG, resource bounds, and remaining limitations.

Run the independent graph and lambda comparison matrix (several minutes):

```sh
python3 -B scripts/verify_r01.py --binary build/msru \
  --output results/r01-recheck.json --trace results/r01-recheck.jsonl \
  --compare reports/r01-release-parallel.json
```

Use new output names for each run. [R01 results](reports/r01.md) distinguish the
verified kernel behavior from the unimplemented measurement and discovery stages.
The Python checkers remain specification oracles, not production simulators.

Public repository: https://github.com/kalewicker/minimal-universe
