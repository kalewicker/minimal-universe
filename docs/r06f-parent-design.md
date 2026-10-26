# R06f parent-population design review

This is a separately registered static comparison following R06e's failed
original-population time-zero admission gate. It changes no consumed protocol,
executes no trajectory, and adopts no scientific parent population.

## Two distinct questions

**Engineered supplied states:** initialize four labeled vertices with two disjoint
reciprocal dyads. Include all three perfect pairings, not a selected pairing.
Cross all 969 rules, three schedulers and four orientations. There are 2,907
law/state groups, 8,721 group/scheduler rows and 34,884 orientation slots. Every
initial state has one canonical eligible patch; initial admission is guaranteed
by construction. This asks how supplied reciprocal allocation behaves under an
intervention. It cannot demonstrate that the system forms that allocation itself.
Labels and scheduler ordering may matter, so retain all pairings and report their
separate denominators. Do not treat them as independent random parent replicates.

**Endogenous generated states:** retain all 14 original seeds and all 969 rules.
Compare fixed proposed generation windows of 10 and 50 successful events, followed
by the unchanged 50-event branch horizon. These are two design scenarios, not
executed burn-ins. Require reaching the chosen generation time and then an eligible
patch. No first-hit stopping, event-time search, seed replacement or top-up is
allowed. A missing patch, early terminal state or cap must remain unavailable in
the original denominator. Eligibility and completion are unmeasured. Conditioning
on pre-intervention eligibility defines a different population; it is not an
unconditional emergence claim or permission to discard unavailable groups.

## Static checks and independent arithmetic

Enumerate supplied pairings from all 24 vertex permutations and deduplicate exact
arc sets; expect three. Verify each with the frozen R06e patch detector. Enumerate
every rule and initial seed for each scenario. For k RHS arcs and fresh-node flag
f, after t successful events N=N0+f*t and E=E0+(k-2)*t. Compare closed-form arithmetic
with an independent iterative count-only update. Both describe necessary count
conditions, not graph reachability. Check initial match availability separately.

Rewiring consumes and emits four arcs with no new vertices, so generation plus
branch event counts share these formulas. For shrinking laws, the successful-event
upper bound is floor((E0-2)/(2-k))+1 when an initial match exists. Preserve every
provably unavailable row; never report impossible negative edge counts as states.
Check conditional peak N/E against 64 and the conservative E*(E-1) match bound
against 4032. Bounds that fail are lack of guaranteed observer support, not observed
overflow; bounds that pass are not evidence of survival or patch formation.

The supplied panel has 17 shrinking rules (empty RHS and 16 one-arc RHSs), so 51
law/state groups and 612 orientation slots cannot complete 50 events by edge
budget alone. Full-panel complete-pair inference is therefore already impossible
under the unchanged requirement. The other 2,856 groups have only count-conditional
support. The design preserves this failed requirement; no threshold, horizon or
rule-family relaxation is adopted.

## Accounting, partitions and resource planning

The two endogenous windows contribute 27,132 design rows; supplied states add
2,907, for 30,039 total. Each window retains all 13,566 original law/seed groups.
Calibration namespace `mu/G2-parent-design-v1/{mode}/law/{digest}/seed/{id}` omits
window, scheduler, orientation and branch. Every descendant inherits the R02 hash
partition. All partition labels here are bookkeeping only; no held-out trajectory
or reserved job is accessed. Seed IDs refer to different explicit populations;
these designs must not be pooled as samples from one distribution.

The supplied panel has 34,884*50 = 1,744,200 conditional branch event targets. This
is an arithmetic workload, not a runtime estimate or an attainable event total.
No null samples are needed to measure engineering completion. Future cost logging
must separate native evolution, independent replay, checkpoint costs and retained
bytes, and enforce per-case and global caps with not-started rows on interruption.
Current static audit budget: 120 seconds and 64 MiB. Store the full local ledger
and compact source-bound public receipt, preserving failures. No empirical assay
runtime, storage projection, completion rate or power claim is produced here.

## Recommendation and execution boundary

Recommend a **separately registered supplied-state engineering calibration** as
R06g, using all three pairings and all rules/schedulers/orientations at 50 events.
Its purpose is to measure completion and costs, including known and newly observed
failures. It is not repair of R06e, scientific acceptance, or evidence of endogenous
formation. Future software must pass the canonical patch to the native operator;
R06d's fixture CLI hardcodes vertices 0,1,2,3 and cannot correctly handle every
alternate pairing as its current input contract stands. Register that adapter and
its independent replay before execution. Retain undefined empty endpoints and all
unavailable/censored/not-started cases; compute no complete-case scientific mean.

Keep the endogenous option deferred: choose a generation window only through a
new scientific design, resolve parent sampling and patch-choice policy, and
address conditional size-domain failures before launching. Neither supplied-state
execution nor endogenous generation is authorized by this review.
