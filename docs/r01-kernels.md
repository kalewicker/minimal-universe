# R01 reference kernel contract

This implementation is deliberately small and bounded. It supports engineering
fixtures, not a production discovery campaign. Source semantics remain in
`semantics.md`; this document pins the execution details introduced by R01.

## Graph execution

Edges have monotonically allocated uint64 IDs. The active vector is kept in
ascending ID order; deletion preserves that order. Oldest/newest select the first/
last active occurrence. Uniform selection uses SplitMix64 with unsigned modulo
2^64 arithmetic and rejection sampling: discard words below `2^64 mod bound`,
then select `word mod bound`. A single uint64 state records the RNG continuation.
Seed edges have no producer; each new edge records its creating event index.

Before an event, check edge exhaustion, then the event cap, then prospective node
and edge counts (in that order). A rejected event consumes no RNG draw or ID.
The new active vector and history are allocated before committing by swapping
them into place. Thus allocation failure also leaves the original state intact.
No concurrent mutation is supported. Checked addition guards counters; hard
reference limits make near-uint64 graph states unreachable in the current CLI.
The overflow test exercises the same checked-add primitive used by the executor.

Graph reference limits are at most 100,000 events/nodes/edges; parsed seeds have
at most 4,096 edges. These are safety ceilings, not a throughput promise. The
immutable-transaction copy approach and history replay are quadratic in long
runs; do not use this implementation for large campaigns without a separately
verified optimization. There is no process-wide physical-memory or wall-time
budget manager yet. The differential runner imposes 30 seconds per subprocess.

## Config and checkpoint formats

The graph text format is whitespace-delimited:

```
MU_CONFIG_1
initial_node_count rng_seed scheduler
max_events max_nodes max_edges
rhs_count
source_symbol target_symbol   # repeated rhs_count times
seed_edge_count
source_node target_node       # repeated seed_edge_count times
```

The `#` annotations above explain the schema; comments are not accepted in actual
files. Symbols 0,1,2 mean u,v,w. RHS arcs must be sorted lexicographically, retaining
duplicates. Unsigned decimal integers only; unknown scheduler, out-of-range
endpoints, oversized grammar, extra tokens, and initial cap violations are errors.
See `examples/feedback.txt` for an actual config.

`MU_CHECKPOINT_1` stores the original config, successful event count, consumed ID
sequence, and complete final state including RNG and allocation counter. Restore
re-executes the selected scheduler from the initial config, verifies every choice,
then requires an exact match against canonical checkpoint bytes. It rejects
truncation, state mismatches, version changes, and trailing content. Restore does
not trust stored adjacency or silently reorder edges. A modified checkpoint that
encodes another completely valid history is not distinguishable from an authentic
one; this is semantic validation, **not cryptographic authentication**. Receipts
separately bind source and complete fixture traces with SHA-256.

Checkpoint output refuses an existing destination. JSON stdout includes status,
nodes, next edge ID, RNG state, all active edges, and all events. Edge arrays are
`[id, source, target, producer_or_null]`. Event arrays are
`[index, consumed, source, target, producer_or_null, fresh_node_or_null,
first_output_edge_id, output_count, rng_after]`.

Pause counts refer to total successful events, not additional events after a
checkpoint. `resume` continues under the original caps and configuration; there
are no hidden overrides. Ordinary execution emits the actual stop reason.

## Iota and SKI

`iota` accepts only i and binary application in its source; optional arguments
are fixture probes in the SKI execution alphabet. `ski` directly accepts S,K,I
and the free fixture atoms x,y,z,f. Every application is fully parenthesized.

Pure-iota translation occurs before reduction and does not count as SKI events.
Both source parsing and constructed terms are limited to depth 256, logical size
100,000, and source text 1 MiB; full evaluation is limited to 100,000 steps.
Trees are immutable; shared subtrees are implementation storage only. Cached
sizes count logical occurrences, including repeated references to shared nodes.

One event contracts the leftmost-outermost redex, searching arguments as well as
function positions. A full normal form at the step boundary reports normal_form,
including a zero-step atomic term. A reducible term at the event cap reports
event_cap. A proposed rewrite exceeding logical size or depth reports term_cap
without changing the current term. Invalid source or translation/probe application
that cannot fit the initial cap is an input error (exit 2), not an executed run.
Allocation errors are also errors; they are never labeled divergence.

The Python reference maps i directly to a lambda abstraction applying its argument
to the lambda definitions of S and K. It uses de Bruijn indices with explicit
capture-avoiding substitution and full beta normalization. It does not import or
reuse the C++ translation or SKI rewrite functions. Native normal forms are mapped
to lambda terms for comparison. This finite comparison is a semantic fixture
check, not a proof of equivalence for all inputs.

## Validation and evidence

The R01-v1 protocol fixes all 220 rules × seven seeds × three schedulers, with 12
events and 64-node/edge caps. Each case is compared event-for-event against a
Python dictionary implementation, then paused at five events (or earlier halt)
and restored in a fresh process. All 23 pure-iota terms through five leaves are
applied to x,y,z; encoded I/K/S receive three additional named semantic tests.

The runner saves a compact immutable receipt and complete local JSONL trace.
Receipts bind all kernel/checker/test source and protocol files. `--compare`
requires equal source hashes, counts, and trace digest, but permits different
binary hashes and environment metadata (e.g. release versus sanitizer builds).
The receipt generator does not itself run CTest: native/Python unit-test outcomes
are recorded separately in the closeout report.

Independent fixture processes may run concurrently (`--workers`, default 4,
maximum 16); result serialization remains in registered rule/seed/scheduler order.
The initial serial release receipt and historical checker source are retained.
The current comparison target is `reports/r01-release-parallel.json`.

No symbolic program search, motif measurements, causal interventions, checkpoint
authentication, or scientific acceptance is implied by this milestone.
