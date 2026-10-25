# R05e long-horizon observer design

Status: **design audited; implementation and calibration not executed**.
The machine-readable design is `protocols/r05e-observer-design.json`; the static
audit protocol is `protocols/r05e.json`. Previous G1/G2 measurements and consumed
receipts remain unchanged. This milestone creates no sampler, campaign, target/sham
assay or scientific acceptance route.

## Proposed state domain and what it would cover

The proposed observer accepts up to 64 retained nodes, 64 active occurrences and
4,032 ordered distinct pairs. These cover the conditional event-50 size envelopes
from R05d (at most 56 nodes and 54 edges). It would report the existing reciprocal
density and R02 motif counts with exclusions, larger-state local exposure, and
observed target-occurrence identity through a reached 50-event endpoint.
Static size coverage is not implemented support, measured throughput or proof
that any cell reaches that endpoint.

The exact R05c full-history DP remains a three-event control. It is not extended
to event 50 by this proposal. Local avoidance probabilities and observed identity
indicators answer different questions from exact unconditional horizon survival.

## Degree-conditioned null and deterministic dispatch

The target measure stays uniform labelled target-stub permutations conditional on
both directed degree sequences. Loops and parallel occurrences remain legal.
This is not uniform over unlabelled graphs or an edge-swap chain. Use exact
enumeration for at most eight edges and a sampled estimator above eight, up to
64. Dispatch depends only on size and is fixed before scoring. Forced sampling
below the threshold is restricted to synthetic calibration controls.

Canonical graph identity includes retained node count and the sorted endpoint
multiset, preserving isolates and multiplicity. Occurrence IDs are excluded only
from this structural null identity. Each draw starts from a fresh target list in
canonical edge order and uses descending Fisher–Yates swaps. Duplicate endpoints
do not remove labelled permutations or alter their weights. Sources stay fixed.

The proposed counter stream hashes a canonical header containing method tag,
fixed root seed, registered query ID, graph digest and draw index, followed by a
newline and attempted-word counter. Interpret the first eight SHA-256 bytes as
unsigned big-endian. For bound b, reject words below `2^64 mod b`, otherwise use
`word mod b`. Rejected attempts also advance the counter. The design fixes root
keys and exact encoding; no world RNG is shared or advanced by an observation.
Reusing a key is deterministic replay, not an independent replicate.

There are 16,384 score draws per sampled query, with no optional stopping,
precision-based extension or seed replacement. A word budget of
`4*B*max(E-1,1)` rejects an incomplete query entirely; retain diagnostics but no
mean/interval from a partial sample. The success distribution is modelled using
independent ideal uniform words. A fixed hash implementation is a reproducibility
mechanism, not a proof of mathematical independence.

## Mean uncertainty and frozen query quota

For ideal independent scores X in [0,1], the two-tail deviation bound is
`P(|sample_mean-null_mean| >= r) <= 2*exp(-2*B*r*r)`.
The bounded-variable result is from
[Hoeffding, Probability Inequalities for Sums of Bounded Random Variables (1963)](https://doi.org/10.1080/01621459.1963.10500830).
We apply it to null-score draws, not world parents. The family extension below
is a union-bound derivation; it needs no independence between queries.

For completeness, a bounded variable under exponential tilting still has
variance at most 1/4. Thus the centred log moment-generating function has second
derivative at most 1/4 and value/first derivative zero at the origin. Integrating
gives `log E exp(s*(X-EX)) <= s*s/8`. Multiplying independent moment-generating
functions and applying exponential Markov bounds at s=4r yields each one-tail
bound `exp(-2*B*r*r)`; sum the two tails and then A query events.

Freeze a positive quota A of **every planned query slot**, including exact,
duplicate, skipped, terminal and censored slots. Graph queries must not be chosen
by prior null results. Take family Monte Carlo failure budget delta=1/100.
No campaign quota or parent registry is chosen in R05e. Calibration proposes A=56.

To avoid relying on floating-point logarithms for an outward interval, let L be
the least integer with `2^L >= 2*A/delta`. Choose the least multiple r of 10^-6
whose square is at least `L/(2*B)`. Since `ln(2*A/delta) <= L*ln(2) <= L`, this is
a conservative radius. Exact integer/rational arithmetic certifies rounding.
The extra conservatism and its cost are reported, not tuned after samples.

Output the rational sample mean, clipped mean interval, empirical score histogram,
sample count, quota, delta, graph/query keys and RNG counters/digests. A contrast
`density-null_mean` uses interval `[density-mean_upper, density-mean_lower]`.
Negative contrasts are retained. This is Monte Carlo mean uncertainty only: it
is not a world-parent confidence interval, a p-value or a scientific test.
The 0.01 engineering budget does not change scientific alpha=0.05. Future inference
must explicitly allocate and combine error budgets before claiming overall
coverage; separate intervals do not automatically produce a 95% joint claim.

## Sampled constants and rare support

A constant finite sample is `sampled_constant_unresolved`, never a proved
degenerate null or structural advantage. Two distinct valid score witnesses
establish nonconstant support, but do not automatically satisfy promotion flags.
Undefined density, incomplete RNG budget and unsupported domain remain separate
statuses. Exact small-null informative/degenerate results retain their meaning.

A fixed two-node control has 32 edges in each direction. A valid target permutation
can turn them into 32 loops at each node while preserving both degree sequences.
The reciprocal score is then zero instead of one. Under the labelled-stub null,
that all-loop endpoint arrangement has probability `1/choose(64,32)`. Thus a finite
sample can easily be constant even though the null is provably nonconstant. The
static audit checks these support witnesses without drawing any random sample.

## Observed identities and eligibility bookkeeping

Freeze targets at a declared parent event and use an independently validated
snapshot/history. At each reached event index report whether every target ID is
still active. Isomorphic recreation with new IDs is not untouched survival.
If a target was consumed, later **reached** indicators remain false; a later
unavailable endpoint remains missing, not false or a padded terminal snapshot.

Report exact local match counts and target-union avoidance while the target set
is intact and another event exists. After loss, label the hazard
`target_already_consumed`; with no matches, there is no next-event probability.
A product of probabilities along one realised path is not unconditional horizon
survival. Uniform-match probabilities do not transfer to deterministic schedulers.
Preserve terminal, resource-censored, undefined and unsupported states, all parent
denominators and branch eligibility changes. No aggregate paired effect is supplied
when registered endpoints are missing. Equal degrees or counts do not establish
sham validity, and this design introduces no causal intervention implementation.

## Geometric effect ceiling under the proposed contrast

With V>=2 and E edge occurrences, reciprocal-pair density cannot exceed
`min(floor(E/2), choose(V,2))/choose(V,2)`: each reciprocal pair needs two opposite
directed occurrences. Loops and extra parallel arcs cannot improve that bound.
A degree-null mean is nonnegative, so the proposed density-minus-null-mean
contrast is bounded above by the same expression. This is a geometric bound,
not an observed effect estimate or a definition retroactively imposed on
previous supplied-statistic gates.

The audit checks this bound for every event-50 conditional rule/seed cell against
the frozen 0.05 structural threshold. Fresh-node growth may make that contrast
incapable of reaching the threshold even with perfect measurements. The bound
does not constrain every possible organization measure or paired intervention
contrast. A different primary scalar, normalization, threshold or hypothesis
would require a separate registered decision; none changes here. Cells not
excluded by the bound are not candidates and receive no effect claim.

## Concrete future calibration design, not launch authorization

The JSON plan freezes eight small known-null graphs, six larger boundary/control
graphs, four root keys and 56 query slots: 917,504 planned score evaluations at
B=16,384. It also requires exact labelled shuffle controls of lengths zero through
eight, all 820 three-node endpoint sequences of lengths zero through three, old
exposure compatibility, large analytic exposure fixtures, deterministic word and
rejection tests, degree preservation and independent score checks. A single-query
upper work bound is 1,032,192 swaps and 4,128,768 attempted hash words; these are
operation allowances, not seconds or benchmark evidence.

All 32 small forced-sample query intervals must cover their exact means using
the full A=56 quota. A miss consumes that calibration gate and requires separately
registered read-only diagnosis; no new seed, longer sample or favorable input
replacement is permitted. The gate can fail by chance under its model, and a pass
would not prove iid hash output or coverage on arbitrary future queries. All
structural/integrity checks must also pass. Large unknown-mean cases check
invariants and unresolved statuses, not unearned exact coverage claims.

R05f must implement the new versioned observer and pin source and this design
before executing that calibration. Its provisional allowance is 600 seconds and
512 MiB, with exclusive attempts and retained query/draw digests and failures.
It is not a native campaign pilot or a fix to R05d's scientific readiness gate.

## Static audit reproduction

R05e checks all 46,234 labelled shuffle-choice vectors, nine rational precision
scenarios and all 13,566 rule/seed cells, retaining unavailable and undefined
cases. Its 120-second/256-MiB static attempt writes an exclusive ledger and
source-bound receipt. Read-only verification needs no local ledger or binaries:

```sh
python3 -B scripts/audit_r05e.py --verify reports/r05e.json
```

No null samples or native trajectories are executed by that command. The 50-event
requirement, 0.05 effect thresholds, motif exclusions and held-out validation
requirements remain unchanged; all G1 holdouts remain unopened.
