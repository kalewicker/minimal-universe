# Semantics v0.1

## G: independent recursive edge replacement

A state retains every allocated node, including isolates, and a finite collection
of independently identified directed edge occurrences. Loops and parallel edges
are allowed. The rule consumes exactly one selected edge u→v and emits a sorted
multiset of zero to three arcs over u, v, and optionally one fresh node w. Bind
u=v for loops. Allocate w if and only if it occurs in the RHS. Never delete nodes.
All produced edges are new occurrences. A single rule is fixed for a run.

Numeric IDs are bookkeeping. Structural equality preserves direction,
multiplicity, loops, and isolates, but ignores IDs. Scheduler state and provenance
are not discarded merely because two structural states are isomorphic.

The consumed edge has zero or one producer event; this is the only direct parent
in the edge-consumption ancestry relation. Shared endpoints do not introduce
additional ancestry edges. This relation is not a complete causal model of the
scheduler. Every extant edge is eligible, regardless of neighborhood.

Distinct scheduling policies for R01: oldest-first (smallest monotonically
allocated edge ID), newest-first, and uniform over edge occurrences. There is no
separate first-ID policy. Stochastic execution, checkpointing, and intervention
coupling require their own pinned RNG contract in R01 before use.

## I: pure-iota sources evaluated by SKI semantics

Source syntax: `T ::= i | (T T)`. Source application is binary and ordered.
Translate compositionally, mapping i to `S (S I (K S)) (K K)` and application to
application. The evaluator alphabet contains S, K, I and application; it is not
claimed to be a single-operation pure-iota intermediate machine.

Operational rules, with application left associative:

```
I x       -> x
K x y     -> x
S x y z   -> (x z) (y z)
```

Reference strategy: leftmost-outermost over the complete tree, including arguments,
until **full SKI normal form** or a cap. Each contracted SKI rule counts as one
event. Translation is accounted for separately. Immutable tree semantics apply;
physical DAG sharing must not change occurrence-level rewriting. Observable
execution metrics name the SKI representation explicitly. No cross-substrate
comparison of raw graph-edge counts and SKI reduction counts is licensed.

R01 must compare the encoded I/K/S applications on symbolic probe arguments to
an independently implemented lambda evaluator (or another independently justified
semantic oracle), including erasure and duplication. Probe atoms belong only to
fixtures, not the pure-iota source census. A known divergent fixture may hit a
cap, but the cap alone is not its divergence proof. No arbitrary SKI normal form
is presumed convertible back to a pure-iota normal form with identical size.

The former rule `(i x) -> ((x S_iota) K_iota)` with expanded pure-iota macros is
retained only in the R00 negative-control checker. It is not the evaluator.

Primary source: [Chris Barker, Iota and Jot](https://web.archive.org/web/20201112014512/http://www.nyu.edu/projects/barker/Iota/).
