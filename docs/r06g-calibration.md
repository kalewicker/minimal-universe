# R06g supplied-state completion and cost calibration

This registration implements the R06f recommendation as a separate engineering
population. It does not repair R06e's original-seed failure or admit a scientific
parent sample. No endogenous generation, scientific score, effect test, null
sample, threshold change or selected law subset is authorized.

## Full population, horizon and grouping

Use all 969 canonical G2 RHS multisets, all three four-node reciprocal perfect
pairings, lex_first/lex_last/uniform_match, and all four intervention orientations:
34,884 slots, 8,721 parent/scheduler rows and 2,907 law/state groups. Parent prefix
is zero; every branch requests 50 successful events with limits 64 nodes, 64 edges,
4032 matches. Include all 612 shrinking-law slots; run them to their natural stop.
Do not omit cases known in advance to stop early. No parent substitution or top-up.

Namespace `mu/G2-supplied-cal-v1/law/{digest}/seed/{pairing-id}` excludes scheduler,
branch and orientation. Inherit the R02 hash partition. These split labels are
calibration bookkeeping; no reserved holdout jobs are used. Use the first eight
big-endian SHA-256 bytes of newline-joined domain `mu-r06g-stream-v1`, parent,
scheduler and target/sham (no final newline). Orientations within a branch share
its stream. Seeds and fixtures are not independent scientific parents. Orientation
selection remains exhaustive, not a production random selector.

The adapter passes canonical patch order from the frozen R06e detector into the
unchanged R06d kernel. The independent oracle maps explicit orientation arc lists
through that order, retains source-order output allocation, and compares every
native output field: final state, IDs, allocator, producers, consumed provenance,
event history and RNG. Native immediate and final checkpoint restores must agree.

## Controls before the full panel

Register 108 controls: all three pairings, schedulers and orientations for each
of empty RHS, endpoint-preserving path RHS [(0,1),(1,2)], and fresh-node RHS
[(0,3),(1,3),(3,2)]. Run once in Release and once in Debug ASan/UBSan; require
identical deterministic receipts before launching the full Release panel. These
are adapter controls, not full-panel sanitizer coverage. A 36-case empty-RHS
smoke test was used in development before registration. Any registered mismatch
consumes the attempt and stops execution for separate diagnosis; never repair
and rerun the same registered identity.

## Denominators, budgets and failure accounting

A branch reaches the horizon iff its recorded event count is 50, even if the
kernel reports no eligible match on that final state. Record kernel stop status
separately. Preserve empty endpoints as undefined for the proposed edge-budget
score; do not assign zero or calculate a complete-case mean. Count parent/scheduler
rows with all four orientations reaching 50 as engineering completeness only.
Scientific complete-pair inference remains unadmitted regardless of the result.

Execute one fixed-order batch per RHS, 36 cases each. Per native batch: 30 seconds
and 16 MiB output allowance; native evolution checks a five-second per-case limit
at completion, while the parent process enforces the batch wall deadline. Each
Python replay case has a ten-second completion check. Global attempt limit: 1800
seconds and 1 GiB retained artifacts, reserving one batch plus 32 MiB for accounting.
Kernel event/size caps bound inner computations. These are execution safeguards,
not estimates of required production resources. Limits are frozen before launch.

Retain batch inputs, complete/partial native output, timings and failure receipts.
On batch failure mark all its 36 slots censored/unverified (even if partial native
output exists); remaining slots are not started. Do not infer observed zero from
unverified slots. Stop without retries, substitutions or extending a budget.

Measure native evolution, native checkpoint verification (including its replay),
process wall time, Python replay time, total wall time and retained bytes separately.
Components are not additive independent benchmarks: process time contains native
phases, and total time contains all phases and orchestration. Final reported
histories count one branch execution; internal checkpoint replays are extra work.
No null queries are billed. Machine-dependent costs apply only to this run.

## Verification and stop boundary

Freeze source hashes and prior receipts; use exclusive attempt directories for
release controls, sanitizer controls and the full release panel. Publish compact
receipts, code and reports, never bulk histories or binaries. Clean public-source
verification rebuilds/runs controls and recomputes the full saved ledger summary
without relaunching the full dynamics. Independent full-history replay occurs in
the registered panel itself. Keep these verification claims distinct.

After completion, separately register a read-only diagnosis of completion and cost
bottlenecks using the preserved evidence. Do not select surviving laws, alter
horizons or generate new parents automatically. Engineering completion is not
scientific readiness; all prior failed gates remain in force.
