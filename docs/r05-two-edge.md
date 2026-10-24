# R05a proposal: directed two-edge path replacement

This defines a new substrate, **G2-path-v1**. The implemented G one-edge kernel,
its receipts, and its consumed discovery registration remain historical baselines.
R05a authorizes a finite static design audit, not a production kernel or campaign.

## Rule and match

A rule has the fixed left-hand side `u→v, v→x` and a right-hand-side multiset of
zero to three directed arcs over `u,v,x,w`. The symbols have indices 0,1,2,3.
`w` denotes one fresh vertex, allocated exactly when it appears on the RHS.
There is one fixed rule per future run, with no labels, guards, negative conditions,
node deletion, or rule competition in this version.

A match is an **ordered pair of distinct active edge-occurrence IDs** `(a,b)`
such that `target(a) = source(b)`. Bind `u=source(a)`, `v=target(a)`, and
`x=target(b)`. Endpoint binding is not injective: all five equality partitions of
u,v,x are legal. A single loop cannot match itself; two distinct parallel loops
give two ordered matches. Two parallel nonloop edges in the same direction give
no match. A reciprocal two-cycle gives two matches. Forks alone do not match.

The same consumed set may appear in two role assignments. Retain both as distinct
matches, even if a particular RHS makes their successors equivalent. Uniform
selection is over these ordered embeddings, not over vertex paths or unordered
consumed sets. Formal rules are not identified after endpoint aliasing, reversal,
or semantic equivalence on a seed.

Sort RHS arcs lexicographically in symbol indices, before binding. Enumerate
multisets in increasing length then lexicographic order. There are
`sum[k=0..3] choose(15+k,k) = 969` formal rules. Of these,
`sum[k=0..3] choose(8+k,k) = 220` avoid w; 749 use w. This counts a rule space;
it does not select a campaign panel. A future rule identifier is the SHA-256 of
ASCII canonical JSON `{"rhs": [...], "schema": "mu-g2-path-rule-v1"}` with sorted
keys, comma/colon separators, and no spaces or newline.

## Atomic transition and identity

Retain all allocated vertices, including isolates. Consume both matched
occurrences simultaneously. Emit each bound RHS arc as a new edge occurrence,
including duplicate arcs created by aliasing. Allocate new edge IDs consecutively
in formal RHS order; never reuse IDs. Fresh vertex IDs are monotonically allocated
and distinct from every retained vertex. Both consumed edges remain available in
the immutable event record, including their endpoints and producer IDs.

The event records the ordered pair, binding, unique non-seed producer-event set,
optional fresh vertex, output-ID interval, scheduler, and RNG continuation.
Each output names the new event as producer. Seed edges have no producer.
Two consumed edges from the same producer yield one unique direct parent;
different producers yield two. A chronological ancestry DAG now has indegree at
most two. A two-parent event is an operational lineage merge, not a finding of
learning or adaptive integration. The scheduler is still outside that ancestry.

For fixed RHS size k and fresh indicator f, after t successful transitions,
`V(t)=V(0)+f*t` and `E(t)=E(0)+(k-2)*t`. These identities do not guarantee that a
next match exists: two or more remaining edges can still have no eligible path.
If k<2, nonnegative edge counts give a necessary upper bound on t; eligibility
can terminate sooner. No old k≥1 non-exhaustion argument transfers to G2.

## Scheduler, caps, and replay contract for the next kernel

At each event enumerate matches in lexicographic `(a,b)` order of numeric IDs.
The proposed policies are `lex_first`, `lex_last`, and `uniform_match`. These names
describe pair ordering; they do not claim fairness or independent edge selection.
Uniform selection reuses R01's specified SplitMix64 words and rejection sampler
over the match count, including a draw when there is only one match. Pair ordering
is role sensitive. Selecting a first edge uniformly and then a continuation
uniformly is a different distribution and is excluded.

Preflight order: parse/validate state and rule; determine the complete match set;
if empty, return `no_eligible_match`; otherwise check event, prospective node,
prospective edge, counter-overflow and match-enumeration caps before drawing.
R05b must register finite numeric engineering ceilings before implementing this
contract. An incomplete match enumeration is `match_cap`, never a smaller eligible
set. Arithmetic uses checked unsigned counters. Structural deltas are independent
of the selected match, so resource preflight needs no favorable-match search.

Prepare the draw, new edges, producer links, and event record in temporary state;
commit all together. Any cap or allocation failure leaves graph, history, IDs and
RNG unchanged. Event-cap and resource stops are censored; empty eligibility is
terminal. A reached terminal state is observable, while later event-indexed states
are unavailable. Checkpoints require a new version tag, original input, rule,
scheduler, caps, active occurrences and provenance, counters, history, and RNG;
restore must replay independently. A G1 checkpoint cannot be interpreted as G2.

## What commutes, and what does not

Two matches with disjoint consumed edge sets remain valid after either event:
neither transformation changes the other's endpoints or removes vertices.
Their RHS copies commute structurally up to renaming the two fresh vertices
and output IDs. Shared vertices alone do not break this argument. This concerns
two fixed redexes in an unrestricted transition relation, not equality of capped
executions, uniform-match distributions, or scheduler traces.

Overlapping consumed sets can disable each other, so R00's global diamond and
confluence conclusions do not transfer. A concrete counterexample uses the empty
RHS and three edges on retained vertices 0,1,2:

```
a: 0→0     b: 0→1     c: 1→2
matches: (a,b) and (b,c)
delete (a,b): only c remains, a nonloop
delete (b,c): only a remains, a loop
```

Both results are terminal because only one occurrence remains. They cannot be
isomorphic: loop count differs. This proves nonconfluence of this particular
G2 rule under unrestricted matching. It does not imply every G2 rule is
nonconfluent, chaotic, interactive in a stronger causal sense, or emergent.

## Static design audit

The registered `R05a-v1` checker enumerates all 790 directed multigraph fixtures
with 1–3 retained vertices and 0–4 edge occurrences, including loops, parallel
edges, and isolates. Edge multisets get consecutive occurrence IDs. A direct
ordered-pair matcher is checked against the separate degree identity

`number of matches = sum_v indegree(v)*outdegree(v) - number of loop occurrences`.

The product counts all composable pairs, including each loop paired with itself;
subtracting one per loop removes exactly the forbidden identical occurrences.
This is a match-count oracle, not an independent oracle for future execution.
All vertex permutations and all occurrence-ID permutations are also checked
separately for match-set equivariance. A named fixture covers the empty vertex
set. The checker records disjoint, one-edge-overlap, and same-consumed-set match
pairs; all five endpoint alias classes; the 969-rule census; and the explicit
terminal counterexample. It does not advance production trajectories.

## Controls and admission requirements

| Question | Required control or check before a scientific assay |
| --- | --- |
| Is matching correct? | Independent adjacency-join matcher versus occurrence-pair reference; all alias classes, loops, parallels, isolated vertices, empty eligibility, overlap and two-parent provenance fixtures. |
| Is execution correct? | Independent step/replay oracle for every registered engineering fixture; transactional cap/overflow/allocation tests; corrupt and cross-version checkpoint rejection. |
| Is match selection correct? | Exact fixture probabilities and RNG continuation; distinguish match-weighted selection from first-edge-weighted selection and measure each occurrence's match participation. |
| Does a second occurrence alter eligibility? | Prespecified context removal/addition fixtures, recording the changed eligible set before any downstream comparison. |
| Does a perturbation have a delayed total effect? | Registered target/sham design, parent-level coupling and sham validity checks, immediate offset accounting, eligibility/scheduler changes, power and complete test families. No automatic degree-preserving sham is assumed feasible. |
| Does topology add predictive value? | Disjoint detector-development, validation and final-test parent groups; frozen target; baseline B versus B plus motifs; account for size, degree, exposure and match count. |
| Are apparent effects size or scheduler artifacts? | Prior G1 evidence as a mathematical baseline; separate newly registered controls, with denominators and size/update budgets explicitly matched or mismatch disclosed. No raw G1/G2 event-count equivalence. |

The old untouched-edge product formula is invalid here. Conditional on the current
graph, avoiding a target occurrence set T in one uniform-match event has probability
`1 - |{m: consumed(m) intersects T}| / |matches|`. Later eligible sets depend on the
trajectory. Enumerating small path histories is required to calibrate any future
survival estimator; edge count alone is insufficient.

R02's eight-edge null domain, motif multiplicity exclusions, and frozen promotion
requirements remain constraints on reuse, not automatic G2 validation. If the
desired horizon exceeds measurement or execution limits, register a new calibration
before running. G1 holdouts retain their partitions and remain unopened. A G2
registry needs a new namespace, parent identity and split audit; reusing G1 data
for design does not make related G2 tests independent validation.

## Next bounded milestone

R05b should register an engineering fixture matrix and numeric budgets, implement
an inspectable G2 reference kernel, and validate it with independently written
matching/replay checks. The current deliverable freezes the proposed semantics and
static audit only. Statistical estimator calibration, campaign design, pilot,
source-bound launch, holdout use and scientific claims each remain later work.
