# R06a analytical observable and hypothesis design

R05g identified a geometric limitation of the proposed reciprocal-density
contrast. This separately registered stage considers a different, narrower
question: **how much of a nonempty graph's edge budget supports distinct reciprocal
relations, beyond what its degree sequence predicts?** This is a proposed new
hypothesis about edge allocation, not an improved numerical estimate of the old
effect. R02 definitions, thresholds, motif exclusions and receipts stay unchanged.

Only synthetic supplied graphs are used. No G2 law/seed panel or historical
trajectory is scored. No world transitions, random draws, native execution,
holdout access, scientific statistics or metric adoption is authorized.
`scripts/design_r06a.py` contains analytical reference formulas for this review,
not a production observer or a calibrated estimator for scientific use.

## Fixed candidates

Let N retain all vertices including isolates, E count all edge occurrences
including loops and duplicates, R count unordered distinct reciprocal vertex
pairs, S count distinct directed nonloop arcs, and L count nonloop occurrences.
M counts nonloop occurrences whose reverse arc is present.

| Candidate | Formula | Undefined when | Interpretation |
| --- | --- | --- | --- |
| Historical pair density | R / choose(N,2) | N < 2 | Reciprocal relations per available vertex pair |
| Edge-budget allocation | 2R / E | E = 0 | Fraction of occurrence budget needed to represent the distinct reciprocal relations |
| Support fraction | 2R / S | S = 0 | Fraction of distinct nonloop directed support with reverse support |
| Occurrence fraction | M / L | L = 0 | Fraction of nonloop occurrences with reverse support |

All lie in [0,1] where defined. In particular each reciprocal pair requires at
least two distinct nonloop occurrences, so 2R <= E. The budget numerator does not
count redundant copies of a pair: it measures minimal reciprocal support relative
to the actual occurrence budget, not the fraction of occurrences having reverses.
Penalizing parallel redundancy and loops is an explicit hypothesis choice. These
may be meaningful structure for other questions; this score does not measure
their organization or declare them biologically irrelevant.

The preregistered design criteria require boundedness, defined scores for all
nonempty synthetic graphs including fully aliased loops, isolate invariance,
invariance under disjoint replication of reciprocal pairs, and a fully defined
exact null for each nonempty small control. Recommend only candidates passing
every criterion for a subsequent, separately registered calibration. A tie stays
a tie; no winner is selected by empirical effect size. These criteria express
the stated edge-allocation question, not a theorem that any score is the best
measure of complexity or emergence.

## Scaling and null analysis

For k disjoint reciprocal pairs, R=k and E=2k. Historical density is 1/(2k-1),
while the other three raw scores are one. Adding isolates changes only the
historical density. Duplicating every arc m times keeps R and S fixed: budget
allocation becomes 1/m, while support and occurrence fractions remain one.
Adding q loops to a single reciprocal pair leaves its support/occurrence
fractions and pair density unchanged, but budget allocation becomes 2/(2+q).
These are algebraic consequences of the definitions, not G2 trajectory claims.

The degree null fixes source stubs and permutes labelled target stubs uniformly,
retaining isolates, loops and multiplicity. N and E remain fixed; S and L may
change. A defined observed score therefore need not have a fully defined null.
Every undefined permutation retains its probability mass. No conditional mean
over only defined null outcomes is reported. Empty graphs and degenerate nulls
remain separate from informative controls. A constant finite sample would still
be unresolved; no sampled null is introduced at this stage.

All multisets of zero to four arcs on one, two and three vertices plus the
zero-vertex empty graph form the fixed 791-graph census. Named positive, negative,
aliased, empty and degenerate fixtures and fixed isolate/replication/parallel/
loop scaling families supplement it. Exact labelled-stub null enumeration is
restricted to E <= 8; larger scaling fixtures have raw algebraic checks only.
Every permutation score is compared to a separate adjacency-matrix scorer.
Null masses are also checked against a multiplicity-weighted recursive generator
of unique endpoint sequences. This is exact synthetic analysis, not Monte Carlo
calibration, a throughput pilot or evidence of parent independence.

The exclusive attempt retains every synthetic graph, labelled null permutation,
both score implementations, full null histograms, undefined mass and failures
within 120 seconds and 128 MiB. A compact public receipt binds the local ledger;
deterministic verification reconstructs it without writing bulk results.

## Draft intervention question and next boundary

For a proposed score Q, the draft parent-level contrast is
`(Q_target,50 - Q_target,0) - (Q_sham,50 - Q_sham,0)`, with the two initial scores
measured immediately after their respective interventions. This compares
subsequent changes; it intentionally does not count the instantaneous score
change and is not the treatment effect on the raw endpoint level. It does not itself establish causal
identification, a valid sham, matched eligibility or scheduler coupling. The
draft keeps the 50-successful-event horizon; it is a total effect under the
registered scheduler, including competition. Resource censoring, termination
before the horizon, unsupported states or undefined scores leave the pair
unavailable. Every registered parent remains in the denominator; a missing pair
prevents an aggregate mean. Synthetic arithmetic controls illustrate these
requirements, without simulating interventions or validating an experimental
estimator. A new production bookkeeper/parent namespace remains to be registered.

No effect threshold, parent count, significance level, test family, power target,
resampling plan, query quota or replacement production primary is frozen here.
R02's 0.05 threshold cannot acquire a new interpretation by silently changing its
score. Even a size-compatible score can have degree-degenerate nulls, low power
or no scientific effect. Static reciprocal structure does not identify
context-sensitive interaction, memory, repair, reproduction or self-reference.

If a candidate meets the declared analytical criteria, the next bounded stage is
R06b: implement its separate versioned reference observer and register a
source-bound synthetic calibration, including exact/sampled null agreement,
undefined/degenerate handling and paired denominators. That is not campaign
authorization. A scientific experiment still requires its own hypothesis,
intervention construction, parent registry, held-out design and justified power
and budgets. If no candidate meets the criteria, preserve that outcome and
register a diagnosis rather than choosing a favorable formula after the fact.
