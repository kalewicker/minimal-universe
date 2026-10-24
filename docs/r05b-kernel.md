# R05b G2 reference kernel

The standalone C++20 executable implements the frozen
[G2-path-v1 semantics](r05-two-edge.md). It has a separate CMake project,
configuration and checkpoint version, executable, and Python oracle. It does not
change the sealed G1 implementation or open its reserved trajectories.

## Build and run

```sh
cmake -S g2 -B build-g2 -DCMAKE_BUILD_TYPE=Release
cmake --build build-g2 -j 4
ctest --test-dir build-g2 --output-on-failure
./build-g2/mu-g2 run examples/g2-path.txt
./build-g2/mu-g2 run examples/g2-path.txt /tmp/mu-g2-prefix.g2 3
./build-g2/mu-g2 resume /tmp/mu-g2-prefix.g2
```

The optional checkpoint is written after at most three successful events, or an
earlier stop. The `run` command then continues to its configured stop. Output paths
must be unused. Checkpoint failure reports an error rather than overwriting data.
The unmodified example is an engineering fixture, not a discovery experiment.

For sanitizer verification:

```sh
cmake -S g2 -B build-g2-sanitize -DCMAKE_BUILD_TYPE=Debug -DMU_G2_SANITIZE=ON
cmake --build build-g2-sanitize -j 4
ctest --test-dir build-g2-sanitize --output-on-failure
```

## Configuration

Text input has this token structure:

```text
MU_G2_CONFIG_1
initial_nodes rng_seed scheduler
event_cap node_cap edge_cap match_cap
rhs_count
source_symbol target_symbol  (one pair per RHS occurrence)
seed_count
source_node target_node      (one pair per seed occurrence)
```

The comments and parentheses above describe fields and are not input tokens.
RHS symbols are 0=u, 1=v, 2=x, 3=w, with sorted arc pairs. Node IDs range from zero
through initial_nodes−1. Input seed order assigns edge IDs from zero. Schedulers
are `lex_first`, `lex_last`, and `uniform_match`. Loops and parallel occurrences
are legal. The CLI rejects unknown tags, invalid endpoints/schedulers/symbols,
unsorted RHS arcs, negative or overflowing unsigned fields, and trailing tokens.

Hard reference ceilings are 128 successful events, 256 retained nodes, 256 active
edges, and 65,536 ordered matches. The RHS has at most three arcs. Configurations,
individual checkpoints, and batch input/list files have a four-MiB input ceiling.
Initial state must fit node/edge caps. These are reference safety limits and do
not promise campaign throughput or satisfy measurement-domain constraints.

## Matching, preflight and atomic events

The native matcher joins each active edge to the outgoing adjacency list of its
target vertex, excluding the identical occurrence. Both lists retain ascending
edge-ID order, giving lexicographic ordered matches. A separate preflight counts
matches with the degree identity; bounded hard ceilings make the count arithmetic
safe. The runtime match cap applies to materialization during event execution.
The inspection method can return the complete match set within hard state limits.

The stopping priority is: no eligible match; event cap; checked prospective
node/edge/ID counts and node then edge cap; match cap. Empty eligibility is terminal.
Event, node, edge and match caps are resource stops. A match cap rejects the entire
step; it does not trim the eligible set or select from a prefix. Prospective
counts are match independent, so no resource check searches for a favorable match.

Uniform selection uses the specified SplitMix64 word function and rejection
sampling over the complete ordered match list. A singleton list still consumes
a word. Deterministic policies consume no words. The candidate RNG state, emitted
edges and event history remain temporary until a final no-throw commit. Exceptions,
including tested injected allocation failures after edge and history preparation,
leave graph, IDs, history and RNG unchanged. Native unit tests also cover RNG
wraparound, rejection-sampling continuation, exact match-cap boundaries, and the
checked-add overflow primitive. Artificial near-uint64 graph states are not
reachable through this bounded parser.

## Output and ancestry

One JSON state contains status, retained node count, next edge ID, RNG, scheduler,
active edges and full event history. An edge is `[id, source, target, producer]`,
where seed producer is `null`. Event objects contain the ordered consumed edge
records, bound u/v/x, sorted unique non-seed parent event IDs, optional fresh node,
first output ID/count, scheduler and post-event RNG. Every emitted arc receives
a new occurrence ID even if aliasing collapses its endpoints onto another arc.

The two-parent relation is occurrence-consumption ancestry. It does not include
all scheduler effects and is not a causal proof of adaptive integration.

## Checkpoint integrity and restart

`MU_G2_CHECKPOINT_1` stores the original canonical configuration, successful prefix
length, and complete prefix state/history. Restore constructs a new graph from
that input, independently of stored active state, and re-executes exactly the
claimed prefix. The serialized result must match byte for byte, including RNG,
IDs, producer links, history and newline termination. G1 and unknown version tags,
unreachable prefixes, corrupt snapshots and trailing material are rejected.
This is semantic replay consistency, not cryptographic authentication against an
attacker who can replace both input and its matching state.

The engineering batch command starts a new graph for each case, writes an exclusive
checkpoint directory, and streams initial matches plus prefix and final states.
`resume-batch` restores every checkpoint as a new graph in a second native process.
The verifier independently computes every event with a Python dictionary rewriter
using direct occurrence-pair enumeration. Native checkpoint replay alone would
share the native transition code; the Python comparison is the independent check.

## Registered engineering evidence

The [R05b protocol](../protocols/r05b.json) fixes 14,535 all-rule/alias/scheduler
cases, 108 additional cases, and 790 static matcher fixtures, totaling 15,433.
Dynamic cases have six-event, 16-node, 16-edge and 256-match caps; static cases
have event cap zero. The Python verifier compares initial match sets, complete
prefix/final state and history, and resumed final states. It binds all source,
binary, manifest, output and indexed checkpoint-collection digests in compact
receipts. Release and sanitizer outcomes must agree exactly.

Per-process wall time is 120 seconds, global attempt time 600 seconds, and retained
output allowance 512 MiB, including a reserved 64 KiB for the final receipt.
The supervisor checks output growth while each native process is running, kills
it on a stop condition, and preserves files and failure receipts. File monitoring
is sampled; an output overshoot can occur between polls. This is an engineering
supervisor, not an OS-enforced memory/disk quota. A process crash or external
interruption may leave a started record without a final receipt; that attempt is
incomplete and must not be called passing.

The original attempts and source-bound results are in [the R05b report](../reports/r05b.md).
Bulk JSONL and checkpoints remain local under ignored `results/`; a public clone
lacks those saved-result inputs. The following is the provenance command for
the full release matrix, not a selective repair or reuse of a consumed path:

```sh
python3 -B scripts/verify_r05b.py --binary build-g2/mu-g2 \
  --directory results/r05b-release-001 --build-kind release
```

A new full engineering reproduction needs an unused, separately identified
directory and retained outcome. No command in this verifier dispatches G1 holdouts
or computes scientific candidate statistics. A G2 measurement calibration and
budget pilot must precede any separately registered discovery campaign.
