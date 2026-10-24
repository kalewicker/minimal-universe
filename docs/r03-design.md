# R03a: static atlas design and feasibility

R03a constructs and independently audits a **planned** panel. It imports no world
engine, invokes no simulator, and does not inspect or rank trajectory results.
The R03b design is frozen, but it is not yet an executable launch protocol.

## Choice: preserve the grammar, shorten the descriptive horizon

For a rule with k output edges, after t successful events the edge count is
`E0+(k−1)t`. The largest registered seed has four edges and k is at most three.
The exact degree null is bounded at eight edges, so the largest shared event
budget with every reachable snapshot inside that domain is `(8−4)/2 = 2`.
At three events the largest growth cases have ten edges and are unsupported.

The planned caps are therefore two events, five nodes, and eight edges. The node
cap follows from at most three initial nodes and one fresh node per event. The
primary descriptive endpoint is event two; snapshots include events zero and one.
Deletion can terminate before event two. Preserve the terminal observation and
mark later requested snapshots `terminated_before_horizon`, never zero-fill them.
Terminal-at-two is a reached endpoint, even when the kernel reports exhaustion.

This does **not** shorten the frozen intervention horizon of 50 events. Applying
the edge bound at that horizon partitions the 1,540 rule/seed cells into 1,470
that exceed eight edges, seven deletion cells that terminate, and 63 k=1 cells
within the edge domain. Edge support alone does not establish informative nulls,
complete motif coverage, valid interventions, or adequate statistical power.

Consequently R03b is a descriptive atlas of the entire grammar, not a test of
persistent organization or an alternative path around R02's promotion gates.
A sampled-null extension is a separate option for later long-horizon work; it is
not silently substituted here.

## Registry and partitions

Each of the 220 rules is combined with each of the seven original seeds. For each
cell, schedule 16 distinct uniform-RNG replicates and one oldest/one newest run:
18 jobs, 1,540 cells, 27,720 jobs total. Deterministic jobs are not replicated to
inflate sample size. Replicate zero contains all three scheduler siblings;
replicates 1–15 contain uniform only. This gives 24,640 parent groups.

Rule identity hashes a canonical JSON schema tag and sorted RHS arcs. Seed IDs
and exact seed digests come from R00. Parent keys encode design ID, rule digest,
registered seed ID, and replicate. Scheduler suffixes identify child jobs. All
scheduler children inherit the parent's R02 partition, preventing one parent's
branches from entering different splits. RNG seeds use a separate hash domain
(`rng|` plus parent key). Changing worker order does not change identities or RNG.

The frozen split yields:

| Partition | Parent groups | Jobs |
|---|---:|---:|
| Discovery | 9,730 | 10,946 |
| Detector development | 4,942 | 5,562 |
| Validation | 4,956 | 5,572 |
| Final test | 5,012 | 5,640 |
| Total | 24,640 | 27,720 |

Only discovery jobs are candidates for a subsequent initial launch. The other
16,774 jobs remain reserved and unexecuted. No claim of complete census results
is permitted until all intended strata have actually been executed under their
appropriate frozen protocols.

Discovery covers 1,539 of 1,540 rule/seed cells. All replicas of one cell fall in
reserved partitions: rule `dd33ee46d0a021e75ccbd0189fc4d08d15865c526dfd325c986d95ef0a10d473`
with seed `cycle3`. Keep it reserved; do not adjust hashes, add a favorable seed,
or move a parent after observing split assignments. The full planned registry
still contains every cell.

## Observations and limits

At each reached snapshot, report reciprocal density, motif histogram, coverage,
and exact degree-null distribution/status. A density-minus-null-mean contrast is
descriptive. No hypothesis tests, confidence intervals, ranking, or promotion are
part of this short atlas. Sixteen stochastic parents per cell are already below
the frozen minimum of 30, and their discovery subset is smaller still.

The eight-edge bound guarantees that the exact null algorithm accepts a reached
snapshot, not that its distribution varies. Motif coverage is also unknown:
repeated arcs can exceed multiplicity two even in this small budget. Retain
excluded-subset counts and coverage flags; do not remove whole trials from the
denominator. Undefined V<2 density is a separate status from null degeneracy,
motif exclusion, early termination, resource censoring, or implementation error.

Static projections over the entire panel give 36 jobs terminating before event
two, 27,684 reaching it, and 612 reached endpoints with V<2. In discovery the
corresponding counts are 16 early terminations, 10,930 reached endpoints, and 243
undefined primary densities. These are deductions from sizes and the fixed panel,
not observed runtime outcomes. The projected discovery event total is 21,876.

## Runtime remains unmeasured

The current null implementation constructs permutations before deduplication.
Summing E! over reachable planned snapshots gives 64,470,952 raw target-permutation
iterations for discovery, before accounting for measurement costs. This is an
algorithmic work bound, not seconds, RAM, or a throughput benchmark. It is not
evidence that the runner fits its future two-hour wall budget.

The future runner must enforce the declared four-worker, 30-second per-job,
two-hour global, 64-KiB per-job-output, and 1-GiB total-output limits. It must
preserve partial/failed attempts, keep untouched jobs not-started after a budget
stop, and never selectively retry or reduce snapshots. An engineering pilot must
test those mechanisms and throughput before any atlas launch.

Next bounded implementation: build and validate that observer/runner with a
separately registered engineering pilot. A launch protocol must then bind this
design, the audited manifest, kernel/measurement receipts, and pilot results.
R03a itself runs none of those jobs.
