# R05f versioned supplied-state observer

`analysis/g2_observer_v1.py` implements the R05e design without changing R02 or
R05c. It accepts at most 64 retained vertices and 64 active edge occurrences,
including isolates, loops and parallel edges. Exposure counts ordered distinct
occurrence pairs joined at the middle vertex, with at most 4,032 matches.

The reciprocal-density null keeps source stubs fixed and permutes labelled
target stubs. Queries with at most eight edges use exact enumeration. Larger
queries use exactly 16,384 descending Fisher–Yates permutations from the specified
SHA256 counter stream and rejection sampler. The root and registered query ID,
canonical graph digest, per-draw counters and attempted-word budget are explicit.
Sampling small graphs is reserved for the R05f synthetic calibration namespace.

Each caller must preregister the positive family quota, counting exact, skipped,
censored and duplicate slots as well as sampled slots. A sampled constant is
`sampled_constant_unresolved`; even the rare-support control cannot be declared
degenerate from its finite sample. RNG exhaustion rejects the complete query,
with partial diagnostics and no mean or interval. There are no retries or
precision increases. The mean and clipped interval use exact rational arithmetic
and a certified radius on the frozen millionth grid. The family bound assumes
ideal independent uniform permutations. Deterministic SHA reproducibility does
not establish iid randomness. This interval concerns Monte Carlo error only.

Observed identity uses occurrence IDs frozen at a declared parent event in an
independently validated history. Isomorphic recreation with new IDs is false;
terminal-before-horizon, resource-censored, undefined and unsupported endpoints
remain unavailable with null values. Local next-match avoidance is exposed only
for an intact target and uniform-match scheduler with nonempty eligibility.
Local hazards are never multiplied into an unconditional survival estimate.
Synthetic paired accounting reuses the frozen R05c bookkeeper, including at the
50-event horizon; any unavailable pair prevents an aggregate effect and retains
the full parent denominator and eligibility changes.

## Source-bound synthetic calibration

`protocols/r05f.json` binds this implementation, its tests, calibration checker,
documentation and the prior design/receipts before launch. The untouched R05e
matrix has eight small and six large fixtures, each with four fixed roots:
56 queries and 917,504 draws. All 32 small-graph intervals must contain their
exact R02 null means; large graphs have invariant checks only. Any failure
consumes the attempt and stops work for a separately registered diagnosis.

The checker independently replays every sampled permutation using direct SHA
concatenation, checks both degree sequences and every adjacency-set score, and
verifies rational mean/interval accounting. It also checks all 46,234 shuffle
choice vectors through size eight, all 820 ordered graphs through three edges on
three vertices against the R02 oracle, all 10,239 R05c exposure cases, large
exposure controls, endpoint statuses, and paired denominator handling. Unit
tests fix literal RNG words, rejection and budget boundaries. Bulk ledgers retain
each labelled permutation, its digest, score and attempted-word count, with query
headers containing roots and graph identities. A compact public receipt binds
the ledger; deterministic read-only replay reconstructs it without saving bulk
data:

```sh
python3 -B scripts/calibrate_r05f.py --verify reports/r05f.json
```

The exclusive launch directory has a 600-second wall budget and 512 MiB retention
budget. This is metrology calibration, with no native world runs, trajectories,
discovery, holdout access, campaign benchmarking or promotion. R05d's failed
readiness gate and R05e's geometric ceiling remain in force. In particular, all
7,420 fresh-node conditional event-50 cells cannot reach the frozen 0.05
density-minus-null-mean threshold. Calibration does not resolve that limitation
or authorize selection of a favorable subgrammar. A changed metric or scientific
hypothesis requires its own explicit, separately registered decision.
