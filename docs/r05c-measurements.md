# R05c exact G2 measurement calibration

This implements bounded exact measurements on supplied states and theoretical
toy histories. It does not sample rules, execute the native kernel, open holdouts,
estimate scientific effects, or select candidates. The fixed controls and matrix
are in `protocols/r05c.json`; G2 matching semantics remain `G2-path-v1`.

## Exposure under uniform-match scheduling

Input edges are `(occurrence_id, source, target)` triples. IDs must be distinct
nonnegative integers and endpoints valid retained vertices. Loops, parallels,
isolates and sparse IDs are retained. Targets are a subset of supplied occurrence
IDs without duplication. Boolean values are not accepted as integers.

`exposure` joins incoming and outgoing lists at each middle vertex and excludes
pairing an occurrence with itself. It returns the complete ordered-match count,
each occurrence's participation count including zeros, and the number of matches
intersecting the target set. Participation counts sum to twice the match count.
Target-set exposure counts the union: a match touching two targets contributes
once. Summing target participation can double count and is not the union measure.

When M>0, the exact one-event avoidance probability is `(M-hit)/M`. With no eligible
matches it is undefined (`None`), including for an empty target set: there is no
next event. Uniform-match sampling is essential. These probabilities do not apply
to deterministic schedulers or to selecting a first edge uniformly and then a
continuation. Untouched occurrences are a narrow identity measure, not motif
regeneration, repair, heredity or adaptation.

## Exact horizon and probability denominators

`exact_horizon` performs Fraction-weighted dynamic programming over complete
labelled states `(retained_nodes, sorted_occurrences, next_edge_id)`. All ordered
matches receive equal mass. Nodes are retained; RHS substitutions and fresh IDs
follow the G2 semantics. New edge IDs start above every supplied ID and are never
reused. Identical labelled states merge by summing their mass. Structurally
isomorphic states with different IDs remain distinct.

No-match paths stop at their actual successful-event index. They contribute
terminal mass at that index and are not padded into later event-indexed states.
The state at a reached horizon remains observable even when it has no next match.
`survival` reports:

| Field | Denominator / meaning |
| --- | --- |
| `reached_mass` | Probability of reaching the requested successful-event index |
| `surviving_reached_mass` | Joint probability of reaching that index with every initial target ID intact |
| `consumed_reached_mass` | Reached mass on which at least one target was consumed |
| `unavailable_mass` | Probability of termination before the requested index |
| `conditional_survival` | Surviving-reached mass divided by reached mass, or `None` when reached mass is zero |
| `terminal_mass_by_event` | Mass terminating at each index strictly before the requested horizon |

Reached plus unavailable mass is one; surviving plus consumed mass equals reached
mass. A completely unavailable horizon is not an observed zero survival probability,
even if an earlier event already consumed the target. Horizon zero is reached with
mass one, including on an empty state. Empty target sets survive vacuously only on
reached branches; their conditional survival is still undefined if none reach.

A control uses a loop at 0, edge 0→1, loop at 1, and isolated loop at 2, with RHS
`u→u`. Half the branches halt after one event; half reach event two while retaining
the isolated loop. Joint surviving-reached mass is 1/2, conditional survival is 1,
and unavailable mass is 1/2. All branches halt before event three. This prevents
silently conditioning on the favorable reached subset or synthesizing later states.

## Computational domain

The module accepts at most eight nodes, eight edges, three successful-event steps,
64 ordered matches and 50,000 distinct frontier states. RHS has zero to three
canonical sorted arcs over u,v,x,w. Prospective node/edge growth must fit the domain
through the requested horizon even if some paths would terminate earlier. A domain
violation rejects the entire request; it is not a partial probability distribution
or resource-censored world result. These conservative bounds are computational,
not scientific gates or a replacement for the unchanged 50-event intervention
requirement. The returned distribution is inspectable; callers must not mutate it.

## Target/sham bookkeeping

The paired function consumes synthetic supplied reciprocal-density endpoints and
match counts. Each row declares one canonical parent in the `mu/G2-cal-v1/`
namespace, target and sham branches, inherited partition, scheduler and horizon.
Partition buckets use the frozen R02 SHA-256 rule on the parent; children cannot
rehash themselves into new partitions. Duplicate parent IDs and malformed or
inconsistent branch identities, splits, horizons, schedulers or statuses fail
closed. This namespace identifies synthetic calibration records, not reserved
scientific trajectories.

Allowed endpoint statuses are reached, terminal-before-horizon, resource-censored
and domain-unsupported. Unreached branches require missing endpoint density and
match count; invented values are rejected. Reached states may have zero matches
and undefined density. Defined densities must be exact integers or Fractions in
[0,1]; missing densities remain explicit. Per-pair effects use the frozen difference
in changes `(target_h-target_0)-(sham_h-sham_0)` only when all endpoints are defined.

Every row stays in accounting. If any row lacks a defined effect, the aggregate
mean is unavailable; the code does not silently compute a complete-case mean.
Both initial and endpoint match counts and their between-branch changes are
reported. Equal counts do not certify a valid sham; unequal counts do not erase
the row. `sham_validity` remains `not_established` and scientific acceptance false.
The function checks supplied bookkeeping, not graph-derived density provenance,
causal identification, statistical independence, power, intervals or test families.

## Registered independent checks and reproduction

Exposure is compared with direct ordered-pair enumeration on 790 multigraphs and
all 10,239 initial target subsets. Survival uses 259 multigraphs, six fixed RHSs,
all 1,743 initial target subsets and horizons zero through three: 6,216 endpoint
distribution comparisons and 41,832 survival comparisons. The independent oracle
expands every labelled branch history without merging; it uses direct pair
matching and separately written substitution. It compares complete endpoint
distributions and terminal-by-depth mass, not only a final scalar. It does not
call the DP transition, the G2 replay oracle or native code.

Four named controls and 18 synthetic paired cases cover nonuniform occurrence
exposure, union counting, the failure of the G1 formula here, partial availability,
nonparticipating targets, immediate offsets, delayed arithmetic effects,
eligibility changes, unavailable endpoints and malformed identities/statistics.
These exact outcomes calibrate code behavior; they are not sampled scientific
effect estimates or new promotion criteria. R02 motif exclusions and exact-null
domains are unchanged and are not extended by this calibration.

The original attempt writes an exclusive directory with a started record, trace,
deterministic calibration receipt and separate execution receipt. It has a
240-second global deadline and 256-MiB retained-output allowance, reserving 64 KiB
for compact receipts. Failures preserve their partial files and failure receipt;
there are no selective retries. The deterministic receipt binds sources,
protocol, prerequisite receipts and the complete calibration trace digest.

```sh
python3 -B scripts/calibrate_r05c.py --output-directory results/r05c-001
python3 -B scripts/calibrate_r05c.py --verify reports/r05c.json
```

The first command records the original identified attempt and refuses to reuse
its path. The second re-evaluates the same exact theoretical fixtures without
writing artifacts; it works from a public clone without local traces or binaries.
It is read-only arithmetic verification, not a fresh sampled world campaign.
See the R05c report for the consumed attempt and any limitations. Any new scientific
campaign still needs its own namespace, split audit, measurement feasibility,
budget pilot and source-bound launch. G1 holdouts remain unopened.
