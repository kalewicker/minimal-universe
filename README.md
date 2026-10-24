# Minimal Universe

Bounded experiments in recursive rewriting, with explicit mathematical limits,
reproducible checks, and a separation between structure and causal organization.

The initial milestone is **R00: mathematical and semantic audit**. This is not
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

The planned production implementation is C++20/CMake. The Python R00 checker is
a small specification oracle, not a production simulator. R01 will introduce
the C++ kernels and independently compare them against reference implementations.

Public repository: https://github.com/kalewicker/minimal-universe
