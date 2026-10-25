# R06b versioned edge-budget reference observer

`analysis/edge_budget_v1.py` implements the R06a candidate as a separate metric,
`mu-g2-edge-budget-v1`. For all supplied graphs with at most 64 retained nodes and
64 edge occurrences, it returns Q=2R/E, where R counts unordered distinct
reciprocal nonloop vertex pairs and E includes all loops and duplicate
occurrences. Empty E=0 graphs remain undefined. Nonempty aliased-loop states
have score zero. Invalid or unsupported inputs raise an error rather than become
empty graphs or zero scores. This reference implementation adopts no scientific
primary and changes no R02/R05 code, criteria or evidence.

## Exact and sampled nulls

The null fixes source stubs and uniformly permutes labelled target stubs,
preserving degrees, loops and multiplicities. E<=8 requests use exact
enumeration; larger requests use exactly 16,384 permutations. Small forced-sample
queries are restricted to `mu/R06b-cal-v1/`. Undefined empty requests return no
mean or interval and use no RNG words, while retaining their quota slots.

The sampler reuses immutable R05f validation, graph identity, Fisher–Yates,
attempted-word accounting, rejection and certified-radius primitives. Its SHA256
header has the separate schema `mu-g2-budget-null-word-v1`, so the new metric
cannot share a word stream with the historical metric through the same root,
query and graph identity. Root/query/graph/draw/counter identities, attempted-word
budgets and output metric IDs remain explicit. The per-query word budget is
`4*16384*max(E-1,1)`. Exhaustion preserves partial diagnostics but returns no mean,
interval or contrast. No retry, seed replacement or adaptive precision is allowed.

Sample means, clipped intervals and reversed contrast intervals use rational
arithmetic. The radius uses the same certified millionth-grid rule, delta=1/100,
and a preregistered family quota covering every planned query slot, including
exact, undefined, duplicate and skipped slots. A sampled constant remains
`sampled_constant_unresolved`. Only complete exact nulls can be labelled
`degenerate`. Intervals concern Monte Carlo error under ideal iid uniform
permutations; deterministic SHA reproducibility does not prove that model or
provide parent-level confidence, p-values, power or scientific effects.

## Synthetic paired bookkeeping

The separate `mu/G2-budget-cal-v1/` parent namespace identifies synthetic records
only. Partition inheritance uses the frozen SHA256 parent split. Rows preserve
both branches' parent, split, scheduler, horizon, immediate post-intervention
score, endpoint score, status and eligibility counts. Duplicate parents,
inconsistent metadata and invented unavailable endpoints are rejected. Reached
empty graphs have an undefined score rather than an observed zero. Zero-match
reached endpoints remain observable.

The effect is paired subsequent change over the requested successful-event
horizon, up to 50. It excludes instantaneous score change. Any unavailable or
undefined endpoint leaves a null pair and prevents an aggregate effect; all
parent denominators and eligibility changes stay visible. Equal match counts
do not establish a valid sham. This module checks supplied arithmetic/metadata,
not independent graph-history provenance, causal identification or scientific
inference. Production parent namespaces and statistics remain unregistered.
Existing R05f exposure and observed-identity functions remain separate; this
stage does not extend exact unconditional survival to 50 events.

## Registered calibration

The R06b protocol binds source, tests, this document and a fixed calibration
design before launch. The quota is **892**: all 816 exact/undefined control
requests from the R06a fixture bank plus 76 matrix slots. The matrix has 19
graphs with four fresh roots derived by the declared fixed SHA256 rule. Eight
empty-graph slots stay undefined; 68 slots each use 16,384 draws, for 1,114,112
draws. Forty-four small means have independent exact truth. Four rare-support
large slots have analytic truth; the remaining 20 large slots have invariant
checks only. Every one of the 48 known-mean intervals must cover its truth. Any
miss consumes the attempt and requires a separately registered diagnosis.

The rare balanced 64-edge fixture has Q=0 only for the all-loop target assignment
and Q=1/32 otherwise. Its zero probability is `1/choose(64,32)` and its mean is
`(1-1/choose(64,32))/32`. An analytic nonconstant-support witness does not let the
sampler relabel a finite constant sample as degenerate or automatically eligible.

The checker independently replays every sampled permutation using direct SHA
concatenation, verifies degrees and every score with separate adjacency logic,
and reconstructs means/intervals independently. Exact distributions are checked
against the R06a matrix oracle with multiplicity-weighted unique endpoint
sequences. It also checks all 46,234 shuffle-choice vectors through size eight,
all 819 raw control graphs, exact default dispatch and the full synthetic paired
matrix. Unit tests cover RNG namespace/rejection/budget boundaries, unsupported
and empty inputs, immediate offsets, unavailable parents and inherited metadata.

Each exclusive attempt retains full query/draw permutation records and digests,
scores, roots, counters, exact-control outcomes and failures within 600 seconds
and 512 MiB. Compact public receipts bind the ignored local bulk ledger. Verify
the receipt from public source with:

```sh
python3 -B scripts/calibrate_r06b.py --verify reports/r06b.json
```

Calibration does not authorize world runs, G2 law/seed scoring, trajectory or
holdout access, a production metric change, a scientific threshold or promotion.
The next boundary is a separately registered scientific design/feasibility
review: physical hypothesis, intervention/sham validity, production parents and
inherited splits, justified effect units/power, estimators/families and campaign
budgets. R02's 0.05 threshold and prior failed readiness results remain historical
evidence; they cannot silently acquire a new metric interpretation.
