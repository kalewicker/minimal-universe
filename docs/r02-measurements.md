# R02 bounded measurement contract

This module observes supplied graphs and synthetic paired endpoints. It neither
evolves a world nor selects rules. The fixed fixture matrix is `protocols/r02.json`;
the operational thresholds and partitions are in
`protocols/r02-measurement-contract.json`.

## Structural observations

`analysis/measurements.py` accepts 0–64 vertices, numbered 0 through V−1, and
directed endpoint pairs. Parallel pairs are distinct edge occurrences in the
input. For each subset of one to three vertices, include all edges whose endpoints
lie in that subset. Count the induced motif once, regardless of automorphisms.
Keep loops, isolates, and direction. Connectivity is weak connectivity; a singleton
is connected even without a loop. Canonical types use the lexicographically least
adjacency matrix over vertex permutations, prefixed by vertex count.

The bounded motif grammar admits at most two edges for each ordered vertex pair,
including loops. A connected subset exceeding this limit is explicitly excluded;
the response includes its count and marks coverage incomplete. No count is clipped,
no subset is silently dropped, and unsupported types are not called absent. The
returned denominators count **all** vertex subsets of each size, including
disconnected and excluded subsets; type density divides by its size denominator.

The primary structural scalar is reciprocal-pair density: the fraction of unordered
distinct vertex pairs with an edge in both directions. It is undefined for fewer
than two vertices. Loops and multiplicity do not contribute directly to its
numerator. This is intentionally narrow; a zero value cannot exclude other forms
of organization.

## Exact degree-conditioned null

Hold the list of source stubs fixed and uniformly permute target stubs. This
preserves both directed degree sequences and edge count, and permits loops and
parallel edges. Deduplicating identical target sequences preserves probabilities
because every distinct sequence has the same factorial multiplicity. Evaluate
the primary scalar on every sequence and return its exact rational distribution.
This describes a random **stub matching** measure, not a uniform distribution over
unlabeled graphs.

The current implementation supports at most eight edges. Larger inputs raise an
explicit domain error. A distribution with one distinct score is `degenerate`,
not evidence of structural advantage; V<2 is `undefined`. Do not replace this null
with an unmatched one to rescue a candidate. The future R03 matrix must fit this
domain or wait for a separately calibrated sampled null. The number eight is a
computational bound, not a scientific threshold.

## Persistence and causal bookkeeping

`untouched` checks whether the same edge-occurrence IDs remain present. Recreating
an isomorphic motif with new IDs does not satisfy this test. The analytical
baseline for m target occurrences at successful-event horizon h is

`product[j=0..h−1] (1−m/(E0+j*(k−1)))`.

Once a target set cannot survive its probability stays zero. If the requested
event horizon extends beyond edge exhaustion, return unavailable (`None`) even
if extinction already establishes the targets' fate. This avoids inventing later
event-indexed observations. The baseline assumes uniform selection of current
edge occurrences and the fixed-k graph grammar. It does not apply to oldest/newest
scheduling or context-dependent eligibility.

The paired intervention scalar is
`(target_h−target_0)−(sham_h−sham_0)`, averaged over distinct independent parents.
Each endpoint must be a defined reciprocal density in [0,1]; missing endpoints,
duplicate parent IDs, and empty samples raise errors. This removes a static
immediate offset but does not remove all perturbation-induced scheduler effects.
Its future interpretation is a total effect under the registered scheduler, not
proof of local context-sensitive causal influence. R02 checks synthetic endpoint
arithmetic only; it does not implement intervention targeting or a causal assay.

## Frozen operational gates and remaining statistical work

The gate requires structural and intervention effects of at least 0.05, positive
95% lower confidence bounds, Holm-adjusted p-values at most 0.05, at least 30
independent parents, two schedulers, complete coverage, and all custody/validation
flags. Missing/unknown fields, nonfinite numbers, inconsistent intervals, and
incomplete families fail closed. It consumes supplied statistics and flags; it
does **not** independently establish their provenance or compute their intervals.
The synthetic positive gate fixture demonstrates code behavior, not an actual
qualifying candidate. These thresholds are fixed operational choices, not claims
of adequate statistical power.

`holm` adjusts a complete declared family; the caller must supply that family.
The contract freezes parent-level bootstrap resampling at 10,000 draws and 95%
intervals. Bootstrap estimation, the specific valid hypothesis test, power/design
analysis, family identifiers, and resampling RNG remain work for the later
registered validation design. No scientific inference is licensed until those
pieces and the matched intervention implementation are validated.

Partitions use SHA-256 of the canonical parent key: interpret its first eight
bytes as an unsigned big-endian integer and take modulo ten. Buckets 0–3 are
discovery, 4–5 detector development, 6–7 validation, and 8–9 final testing. Every
branch and intervention inherits its original parent key. Do not hash child IDs
to obtain independent splits. A later registry must freeze parent-key formatting
and check actual stratum coverage before any data are generated.

## Independent calibration

The structural oracle builds all labeled templates and their isomorphism orbits
using explicit bijections and union-find-style connectivity, independently of
the measurement module's canonicalizer and connectivity traversal. The actual
measurement comparisons cover 614 binary/ternary graph fixtures; construction of
larger template tables does not imply exhaustive comparison of all ternary
three-vertex graphs.

Survival validation enumerates every labelled edge-choice history with exact
Fraction weights. The null oracle enumerates all ordered endpoint sequences on
three vertices up to three edges, groups them by their two degree sequences, and
compares their score distributions to target-stub permutations. Neither oracle
calls the formula or null generator being tested.
