# R00 mathematical audit

These are deductions from the specified rules. Finite checks corroborate their
implementation; they do not replace the proofs or establish emergent organization.

## Size and termination

Let k be RHS edge count and f indicate use of w. Each successful graph event
removes one edge, adds k edges, and adds f nodes. Induction gives
`V(t)=V(0)+ft`, `E(t)=E(0)+(k-1)t`. Node retention is essential to the first result.
For a nonempty seed, k=0 exhausts the seed after exactly E(0) events; k≥1 never
runs out of edges. If f=1 or k≠1, successful transitions cannot revisit a previous
structural state. The remaining case f=0,k=1 has fixed finite vertex and edge
counts and therefore a finite structural state space. An infinite path repeats
states, but an arbitrary nonperiodic scheduler need not produce a periodic path.
An initially edgeless graph is already halted under every rule.

## Ancestry and commutation

Every consumed edge has at most one producer, so the direct event-ancestry graph
has indegree at most one. Parents precede children, giving a forest. Multiple
initial edges may yield multiple roots even when they share nodes.

For two distinct eligible edges a and b, rewriting a does not consume b, change
b's endpoints, or invalidate its eligibility. Rewriting b has the symmetric
property. The two orders produce the same old nodes and edges and the same two
RHS copies; rename fresh nodes by the event's original consumed edge to obtain
an isomorphism. The argument includes parallel edges and loops. Selecting the
same occurrence twice as alternative first steps gives identical successors.
Thus the unrestricted structural rewrite relation has the diamond property
(allowing zero steps for coincident successors), which implies confluence by
commuting finite derivations. This does not imply termination, equality of
arbitrary prefixes, fairness, or confluence of a resource-capped runner.

No event consumes two lineages. Endpoint identity can affect aggregate topology,
but no neighborhood predicate selects a different local transformation. Scheduler
competition can couple observed trajectories and must not be mistaken for a
local context-sensitive interaction.

## Enumeration

There are nine symbolic arcs over u,v,w. Multisets of length k number
`choose(8+k,k)`, giving 1,9,45,165 for k=0,1,2,3, totaling 220. Four arc types
avoid w, giving 1,4,10,20, totaling 35. Hence 185 use w, and 180 use w with
k=2 or 3. No reversal quotient or additional semantic equivalence is applied.
Rules remain distinct even when a particular loop seed aliases u and v.

## Expansion-only iota failure

The pure-iota S macro contains five leaves and K contains four. Replacing
`(i x)` by `((x S_iota) K_iota)` adds eight leaves and sixteen full-tree nodes.
Every finite non-atomic pure-iota term contains a deepest application node whose
children are i, hence a redex. Rewriting preserves the non-atomic pure-iota
grammar, so there is always another step and no normal form is reachable. This
specific divergence is proved, not inferred from a timeout. It also rules out
the proposed syntactic identity contraction to a smaller argument.

The corrected SKI translation in semantics.md implements `i x = x S K`:
`S (S I (K S)) (K K) x -> (S I (K S) x) ((K K) x)`; the left component reduces
to `x S`, the right to K. R01 must still test the implementation independently.

## Persistence baseline

For a fixed set of m currently active edge occurrences, conditional on surviving
the preceding selections under uniform scheduling, the next event avoids that
set with probability `1-m/E(t+j)`. Multiplication gives the survival probability
through h events. This concerns untouched occurrences, not motif regeneration.
It applies only while the trajectory is defined and the target set remains
eligible; deterministic size formulas supply E for this grammar. Growing edge
counts alone can produce apparently long-lived motifs.

## Acceptance and interpretation

The executable audit checks all 220 definitions against seven fixed seed graphs,
12-event size/parent fixtures (or earlier edge exhaustion), and all unordered
pairs of initial edges for the two-step diamond. It also checks every redex in
every ordered pure-iota tree with 1–8 leaves for the expansion delta and continued
reducibility. It is a finite implementation audit, not a seed census or a test of
H1–H4. The full statements above depend on the proofs, not extrapolation from
these fixtures. Measurements, novelty gates, and causal interventions remain
unimplemented.
