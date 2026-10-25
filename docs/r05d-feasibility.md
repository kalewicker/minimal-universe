# R05d static G2 campaign feasibility

This review reads protocols and public engineering/calibration receipts only.
It executes no graph transitions, consumes no matches, reads no trajectory files
and creates no candidate or parent registry. All 969 formal G2 rules and all 14
existing engineering seeds (five core plus nine extra) remain in the denominator.
The fixed scope and source inputs are in `protocols/r05d.json`.

## Availability before domain checks

Every rule/seed cell is reviewed at horizons zero through 50. Horizon zero is the
initial state, including empty or already halted seeds. At positive horizons,
zero initial eligible matches proves that no first event can occur, regardless
of RHS. Initial eligibility is checked by the degree identity and independently
by ordered occurrence-pair enumeration.

For k<2, each successful event removes `2-k` net occurrences, and needs at least
two occurrences before it starts. If the initial eligible set is nonempty, the
count-only maximum number of successful events is
`floor((E0-2)/(2-k))+1`. A later horizon is provably unavailable. A horizon at or
below this upper bound is not proved reachable: compatible edge counts do not
guarantee an eligible path. For k≥2 there is no finite ceiling from edge count
alone, but topology can still terminate the trajectory.

The ledger keeps all cells and labels positive-horizon reachability
`not_established_by_static_sizes` unless one of those necessary conditions proves
unavailability. An unavailable horizon has no projected endpoint; negative edge
counts are never presented as states. Terminal endpoints, resource stops and
domain incompatibility are different concepts. This review observes none of their
future dynamical outcomes.

## Conditional projections and guarantees

If a horizon is not excluded by those necessary tests, size accounting gives
`V(h)=V0+f*h`, `E(h)=E0+(k-2)*h`, conditional on h successful events. Peak sizes
include the initial state and every intermediate index. The checker evaluates:

| Check | Meaning |
| --- | --- |
| G2 kernel count caps | Event, peak-node and peak-edge counts fit the existing hard ceilings |
| G2 kernel match cap | `peak_edges*(peak_edges-1)` fits the match cap; this sufficient worst-case bound is not an observed match count |
| R02 observer node domain | All projected retained-node counts fit the 64-node interface |
| Exact degree-null edge domain | Every projected edge count is at most eight |
| G2 local exposure domain | Every projected state fits eight nodes/eight edges and the 64-match bound, separately from any horizon limit |
| Exact G2 survival domain | Local size domain, at most three events, and a sufficient bound on every labelled frontier |
| Density definedness | Initial and conditional endpoint node counts are at least two, reported separately |
| Motif completeness | Known initial exclusions are retained; initial completeness plus at most two total edges guarantees future coverage, while larger cases remain unestablished |

The exact-survival frontier bound starts with the known initial match count and
multiplies subsequent pre-event bounds `E(t)*(E(t)-1)`. Histories can merge, so a
bound above the 50,000-state ceiling is not proof that the actual frontier exceeds
it. It is labelled unguaranteed. Outside the exact size/horizon domain, this
frontier calculation is not used to rescue support. Domain compatibility does
not establish informative null distributions, meaningful motifs or scientific
eligibility.

The initial motif flag follows from arc multiplicity: an arc repeated more than
twice already excludes a connected singleton or pair in the R02 motif grammar.
It is a static coverage fact, not a motif score or selected predictor. Future
coverage is conservatively unestablished when size alone cannot guarantee it.

## Arithmetic work bounds

For compatible observer/null sizes, `(h+1)*peak_edges!` bounds raw target-stub
permutation iterations over all requested indices, conditional on reaching them.
The bound deliberately ignores early stopping and duplicate target stubs. The
motif subset bound is the sum of vertex subsets of sizes one through three at
peak node count. Neither bound is elapsed time, RAM use or pilot evidence. No
benchmark or throughput claim is made by the review.

## Independent validation and accounting

The planner enumerates sorted arc multisets and uses closed-form projections.
The independent checker enumerates ordered arc products, retaining nondecreasing
sequences, and increments hypothetical integer size counters. It does not select
or rewrite any edge. The count ceiling is independently checked by exhausting
integer edge counts, not by applying the closed-form ceiling again.

All 13,566 cells are checked at all 51 horizons: 691,866 size views. Per-cell ledger
rows are retained for horizons zero, three and 50, totaling 40,698 rows. Summary
tables for every horizon retain all availability categories. Domain check totals
apply only to projections not proved unavailable, with their denominators explicit;
unavailable cells remain in the full-cell counts.

The greatest reviewed common horizon for each domain is reported across every
non-excluded cell, with no cell deleted or selected. This mathematical envelope
is not permission to shorten the fixed 50-event intervention requirement or run
another short descriptive atlas. Statistical plans, parent split coverage,
replication/power, target/sham validity, frozen families, resampling RNG and runtime
budgets still need their own registrations.

## Reproduction and scope boundary

The exclusive static attempt has a 240-second deadline and 256-MiB retained-output
allowance, reserving 64 KiB for compact metadata. It preserves a started record,
partial files and any failure receipt. Source-bound deterministic results are
separate from elapsed-time accounting. Bulk per-cell rows remain local under
ignored `results/`; compact public receipts bind their content hash.

```sh
python3 -B scripts/verify_r05d.py --output-directory results/r05d-001
python3 -B scripts/verify_r05d.py --verify reports/r05d.json
```

The first command records the identified original attempt and refuses overwrite.
The second recomputes the same static arithmetic without writing artifacts or
requiring local evidence/binaries. It does not launch a campaign or inspect
holdouts. See the R05d report for the completed review and decision.

If full-panel 50-event measurement support fails, the next stage is a separately
registered long-horizon measurement design/calibration. No shorter horizon,
favorable subgrammar, relaxed threshold, measured effect, causal conclusion or
scientific acceptance is inferred as a repair. All G1 holdouts remain unopened.
