# Minimal Universe

Bounded experiments in recursive rewriting, with explicit mathematical limits,
reproducible checks, and a separation between structure and causal organization.

The project has an **R00 mathematical audit**, **R01 reference kernels**,
**R02 bounded measurement calibration**, and an independently audited
**R03b descriptive discovery atlas**. This is not evidence of emergence,
learning, life, or open-ended evolution. Holdout and downstream experiments
remain unlaunched.

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

## Measurement calibration

```sh
python3 -B scripts/calibrate_r02.py --output /tmp/minimal-universe-r02.json
```

The [R02 contract](docs/r02-measurements.md) defines induced multigraph motifs,
exact degree-conditioned nulls, exposure-adjusted persistence, synthetic paired
effects, and promotion gates. [Results and limits](reports/r02.md) include all
registered calibration counts. Calibration did not run discovery or a real causal
assay; the subsequent descriptive discovery milestone is recorded below.

## Descriptive discovery atlas

[R03a design and feasibility](docs/r03-design.md) freezes a complete planned panel
of 27,720 jobs at a two-event budget, with discovery and holdout partitions fixed
in advance. The [static audit](reports/r03a.md) verified every job without running
world dynamics. The [observer/runner pilot](reports/r03p.md) has passed on its fixed
engineering panel; its [execution contract](docs/r03-runner.md) describes timeouts,
storage accounting, and holdout protection.

The [R03b execution contract](docs/r03-atlas.md) and source seal governed one
completed discovery attempt: 10,946 jobs, 21,876 native events, and 32,822 observed
snapshots independently verified. All 16,774 holdout jobs remain reserved.
[R03b results](reports/r03b.md) preserve early terminations, undefined measurements,
degenerate nulls, and motif exclusions. No candidates were promoted. The 50-event
intervention gate is unchanged.

The [R04a eligibility closeout](reports/r04a.md) verified the public receipts and
closed conditional validation without launching it: this descriptive registration
supplies no eligible candidates, and intervention effects remain unmeasured.
Verify it from a public clone with
`python3 -B scripts/audit_r04.py --verify reports/r04a.json`.
The [R05a two-edge proposal](docs/r05-two-edge.md) now defines directed path
replacement, ordered occurrence matching, aliases, atomic events, ancestry,
scheduling, and required controls. Its [static audit](reports/r05a.md) passed on
790 multigraph fixtures and the 969-rule census; an overlapping-match example
demonstrates a nonconfluent rule. Verify it with
`python3 -B scripts/audit_r05.py --verify reports/r05a.json`.
The [R05b G2 reference kernel](docs/r05b-kernel.md) is now implemented in a separate
C++20 project. [Release and sanitizer validation](reports/r05b.md) matched the
independent Python oracle on 15,433 cases, 73,709 primary events and all checkpoint
restorations per build.

```sh
cmake -S g2 -B build-g2 -DCMAKE_BUILD_TYPE=Release
cmake --build build-g2 -j 4
ctest --test-dir build-g2 --output-on-failure
./build-g2/mu-g2 run examples/g2-path.txt
```

G2 scientific status remains untested. The next milestone is R05c measurement
calibration for match-weighted exposure and survival, before a discovery campaign.

Public repository: https://github.com/kalewicker/minimal-universe
