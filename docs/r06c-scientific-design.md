# R06c: scientific assay design and static feasibility

This registration authorizes static synthetic checks and planning arithmetic only.
It adopts no scientific primary, threshold, parent sample, campaign or world pilot.
R02 and all consumed protocols remain unchanged. Both designs below are declared
before the census; failure of deletion does not trigger a post-result sham search.

## Physical question and outcome

Does destroying reciprocal allocation in an eligible four-vertex patch change its
subsequent recovery relative to an equally extensive rewiring that preserves two
reciprocal dyads? Proposed raw score Q = 2R/E counts distinct reciprocal nonloop
pairs against all edge occurrences. At E=0 it is undefined. This is an allocation
question, not evidence of life, self-maintenance or general complexity.

The proposed per-parent outcome is X = (Qt,50 - Qt,0) - (Qs,50 - Qs,0), at 50
successful events in each branch. Time zero is after intervention. Thus X measures
differential subsequent change, excluding the instantaneous difference 4/E; it
is not the endpoint target-minus-sham contrast. Positive X can reflect recovery
or sham deterioration. Subsequent degree changes and competition are mediators
included in the total effect. Neither branch outcome is currently observed.

## Two fixed intervention proposals

1. Delete one unique reciprocal pair a->b, b->a. Require a distinct two-edge
   deletion with identical per-vertex in/out degree decrements and loop decrement.
   Enumerate all 136 two-arc multisets on four labels. The same degrees admit the
   original pair or two self-loops; the latter fails the loop control. With unique
   target occurrences, the former is not a distinct sham. This strict proposal
   should be reported infeasible, without silently relaxing matching requirements.
2. Select four distinct vertices whose induced internal edges are exactly two
   unique reciprocal dyads. Remove all four occurrences in both branches and emit
   four fresh occurrences with one incoming/outgoing arc per vertex, no loops and
   no original endpoint arcs. Enumerate all 24 target permutations: directed
   four-cycles are target orientations, alternate reciprocal pairings are shams.
   Select each of the two orientations uniformly and independently (four equally
   weighted combinations). Do not select orientations by measured effect.

Exact degrees, E, N and loop count are preserved at time zero. For ordered,
distinct occurrence matches, M = sum_v indegree(v)*outdegree(v) - loop_count.
An occurrence a->b participates in indegree(a)+outdegree(b)-2*[a=b] matches.
The checker independently enumerates ordered occurrence pairs and compares these
identities. All unchanged outside occurrences retain their participation; newly
emitted occurrences need not. These are limited nuisance controls, not proof of
universal sham validity or isolation of a local mechanism.

The fixed external-context census uses one outside vertex and all multisets of
zero through three arcs incident to it (nine arc types, 220 contexts), testing all
four target/sham combinations (880 checks). Loops and repeated occurrences remain.
The induced-patch restriction implies Qs,0-Qt,0 = 4/E, checked by an independent
adjacency scorer against the frozen R06b raw scorer. Identical degree profiles
imply identical exact target-permutation null distributions at time zero, without
running a null sampler. Finite Monte Carlo draws need not coincide.

The future native operator must allocate four fresh IDs on both sides, preserve
outside IDs and allocator continuation, and treat provenance/birth age equally.
This static review has no native intervention implementation or checkpoint replay.

## Parents, eligibility and scheduler design still requiring registration

Proposed group keys are `mu/G2-budget-design-v1/law/{digest}/initial/{digest}/replicate/{index}`;
this is a design namespace, not an allocated production registry. Exclude scheduler,
branch, orientation and event from the group identity. All descendants inherit the
R02 SHA-256 partition. The R06b calibration-only bookkeeper is not production-ready.

Proposed strata are uniform_match, lex_first and lex_last. Shared groups across
strata are not independent replicates. Deterministic duplicate initial states are
not independent parents. For uniform matching, propose independent preregistered
branch RNG streams, with a separate orientation selector, retaining the native
scheduler's marginal law. Common-noise coupling is not assumed. Native seed and
stream separation still need independent validation.

Eligibility is measured before intervention; absent patches are unavailable, not
zero effects. Retain all registered, eligible, completed, undefined and censored
counts. Never replace failed parents or top up selectively. Scientific inference
requires a frozen population and weights, an eligibility policy and handling of
all missing outcomes. A complete-case mean is not an acceptable automatic repair.
No burn-in, law subset, parent distribution or scientific test family is chosen here.

## Conservative power and work scenarios, not adopted thresholds

For independent, fully defined parent outcomes X in [-2,2], Hoeffding's bounded
independent-variable inequality gives P(mean(X)-E mean(X) >= t) <= exp(-n*t²/8),
and the analogous lower tail. Source: Wassily Hoeffding (1963),
[Probability Inequalities for Sums of Bounded Random Variables](https://doi.org/10.1080/01621459.1963.10500830).
These assumptions are not established by seed strings or observer calibration.

Planning uses alpha=1/20, beta=1/5, alternative gaps delta in {1/20,1/10,1/5},
and family slots m in {1,3,2907}. The 2907 scenario is 969 laws times three
schedulers, not an authorization to test those laws. For H0: mean <= 0 versus
mean >= delta, reject above delta/2. This is not a test that an effect exceeds
delta. Let La be the least integer with 2^La >= m/alpha and Lb with 2^Lb >= 1/beta.
Because e>2, n=ceil(32*max(La,Lb)/delta²) is a conservative sufficient sample size
per test for Bonferroni family error and per-test miss probability. It is not
optimal and does not use empirical variance. Alpha, beta, gaps and family slots
are planning inputs, not transferred R02 acceptance rules.

With all-parent completion required, q_missing <= (1/20)/n is a sufficient union
bound for <=5% probability of any missing group in one test. This is an unmeasured
requirement, not an availability prediction or power guarantee.

For each of nine power rows, evaluate optional null-query counts 0, 1 and 4 per
parent-test slot: 27 work rows. Raw Q changes require zero null queries. Parent-test
slots n*m may count shared groups; they are not unique parent counts. Two branches
at 50 events require 100*n*m conditional event targets, excluding parent generation
and censoring. Optional null quota A=q*n*m includes all planned slots, including
undefined, exact and repeated states. With B=16384 and E<=64, draw upper bound is
A*B and word allowance A*4*B*63. Recompute simultaneous Monte Carlo radius using
A, delta_MC=.01 and the frozen R05e certified bound, independently checked by its
binary-search oracle. Do not reuse R06b's calibration quota or radius. No runtime
or storage projection is made without a measured implementation.

## Stop boundary

A successful review means the fixed counts and mathematical controls agree; an
infeasible deletion proposal remains a useful design result. Scientific status
stays untested. Next is separately registered R06d: implement the atomic rewiring
operator and source-bound synthetic assay fixtures, independently replay IDs,
provenance, partitions and scheduler streams, and measure engineering costs.
No scientific primary adoption or world pilot follows automatically.
