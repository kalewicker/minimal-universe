# R06d atomic rewiring and synthetic assay replay

This is a separate experimental native kernel in `g2_assay`, initially copied
from the frozen R05b implementation and extended without editing its sources.
Its checkpoint tag is `MU_G2_ASSAY_CHECKPOINT_1`. It is not a drop-in production
upgrade. The existing config grammar and scheduler algorithms are unchanged.

## Atomic operation and provenance

A supplied ordered patch (a,b,c,d) must contain four distinct valid vertices.
Its induced internal occurrences must be exactly a->b, b->a, c->d, d->c, each
unique. All other internal edges, loops and duplicate dyads cause rejection.
Orientation 0/1 emits a directed four-cycle; 2/3 emits alternate reciprocal pairs.
Every source emits once in patch order. Both branches consume four occurrences
and allocate four fresh monotonically increasing IDs. Outside IDs, producers,
node count and successful-event history remain unchanged. The allocator is never
reset. Only one intervention is allowed per graph.

The intervention is an external operation, not a successful world rewrite event.
Its explicit record contains consumed occurrence IDs/endpoints/producers, parent
event prefix, patch, orientation, branch seed and first output ID. The next four
IDs are externally created at that prefix. Their native world-event producer is
null; this does **not** identify them as seed edges: origin is recovered from the
intervention's output ID range. Subsequent events retain full consumed occurrences
and ordinary world-event parent links. Any analysis of causal ancestry must include
the external intervention record rather than treating event-parent lists as a
complete intervention-aware DAG. Both branches have the same birth convention.

Validation, overflow checks and all vector/string construction precede commit;
commit uses swaps and scalar writes. Fault injections before record creation and
before commit must leave serialized state and RNG unchanged. Invalid orientation,
missing/duplicate/looped patches and repeat interventions must do the same.

Restore replays the original config to the parent prefix, reapplies the intervention
and branch seed, then replays subsequent events. Exact serialization comparison
rejects altered snapshots or trailing bytes. Both immediate and terminal checkpoints
are replayed; uninterrupted and resumed trajectories must match exactly.

## Registered synthetic matrix

Use all 220 R06c contexts: one external vertex, all multisets of zero through three
incident arcs from nine types. For each, run four orientations, three schedulers
and parent prefixes zero/one: 5,280 cases. The fixture rule preserves the selected
path's endpoints (`[(0,1),(1,2)]`), so a one-event parent prefix tests existing
producers and nontrivial allocator state without removing patch eligibility.
Run exactly three additional events per branch. Twelve extra empty-RHS controls
(four orientations times three schedulers) must terminate after two events, with
empty states retained. Total: 5,292 cases per build; no scientific law selection,
50-event assay, candidate scoring or degree-null sampling.

The independent Python oracle uses dictionaries and ordered occurrence pairs,
explicit orientation endpoint lists and its existing independently implemented
scheduler. Compare every output field, consumed provenance, history, RNG and final
allocator state. Native checks exercise two allocation faults, two invalid vertex
patches, two invalid orientations, three invalid induced patches, duplicate
intervention, tamper rejection and both checkpoint replays in every case.

Calibration-only group `mu/G2-assay-cal-v1/context/{index}` excludes prefix,
scheduler, orientation and branch. All descendants inherit the frozen R02 hash
partition; terminal controls use a separate calibration group. Branch seeds are
first-eight-byte big-endian SHA-256 of newline-separated domain
`mu-r06d-branch-v1`, parent key, scheduler and target/sham label (no trailing newline).
All enumerated orientations of one branch share its stream. Confirm distinct
branch seeds per group/scheduler, not statistical independence. Native SplitMix64
and rejection sampling are checked against Python at every selected match.

Orientation selection itself is exhaustively enumerated, not randomly sampled.
No production orientation selector, parent sampler or population registry is
admitted. The branch stream derivation is fixture plumbing; random stream hashes
are not proof of independent parents. No aggregate scientific effect is computed.

## Registration, budgets and next boundary

One release and one ASan/UBSan attempt are registered up front on identical inputs.
Allow 120 seconds per native subprocess, 180 seconds total per attempt, 64 MiB
retained output per attempt. Preserve failures; source fixes after consumption
need a new protocol identity. Verify prior bound sources without rerunning prior
experiments. Record native binary hash, execution time and retained bytes locally;
publish compact receipts and source only. These measurements characterize short
synthetic fixtures, not campaign runtime or storage feasibility.

Next is a separately registered bounded assay-budget and completion calibration:
freeze the full unfiltered engineering input population, event horizon, missingness
accounting and runtime/storage limits before execution. Resolve production
orientation selection, parent sampling and causal estimand admission separately.
No scientific pilot, metric adoption or promotion follows automatically.
