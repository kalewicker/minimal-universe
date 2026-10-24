# R03b discovery atlas execution

The launch protocol is `protocols/r03b-launch.json`; the original design remains
unchanged. `protocols/r03b-seal.json` freezes the adapter, analyzer, observer,
supervisor, prerequisite receipts, measurement/kernel dependencies, tests, binary
hash and registry digest before execution. Every worker checks the seal again.

## Scope

The full 27,720-row registry is preserved in order. Only its 10,946 discovery
rows may dispatch; the 16,774 other rows remain reserved. Workers independently
validate their rule, seed, parent identity, inherited split and RNG key and reject
reserved partitions. No adapter test executed a production trajectory before the
registered launch. Validation tests used static rows only.

The attempt retains its exact registry and launch metadata. The supervisor works
on a full index-aligned dispatch plan, so reserved and unstarted jobs stay visible.
It uses the validated four-worker supervisor and unchanged two-event kernel limits.
The initial state and reached event-one/event-two states are observed. Terminal
states are recorded; later unavailable observations are not synthesized.

The global one-GiB allowance includes the saved manifest, metadata, supervisor
outputs, run receipt, and bounded post-run analysis. The adapter subtracts manifest
and metadata bytes and an eight-MiB analysis reserve from the supervisor allowance
before dispatch. Post-run analysis checks both its reserve and combined retained
output size before writing. Static source validation precedes the supervisor's
two-hour execution deadline; it is not counted as world execution time.

## One attempt, then saved-result auditing

`atlas_r03.py launch` uses the exclusive attempt path pinned by the protocol.
It cannot resume, overwrite, choose another subset, change caps, or selectively
retry errors. If supervision stops early, the receipt remains partial and all
suffix/holdout statuses remain present. The design's theoretical full-panel counts
are not substituted for actual observations.

`analyze_r03.py` reads saved artifacts only. It verifies source/input/ledger hashes,
indices, statuses, byte accounting and frozen budgets. Every completed trajectory
is re-executed in the independent Python reference, not the native binary. Every
snapshot is compared to the independent R03p observation oracle. This is replay
verification, not a new world experiment. Analysis never opens held-out trajectories
because none are executed or stored.

The machine-readable cell table has all 4,620 rule/seed/scheduler combinations,
including combinations with no discovery jobs. It records planned, discovery,
reserved, completed, error and unstarted counts plus endpoint measurement statuses.
Scheduler/event summaries preserve undefined density, degenerate nulls, motif
exclusions and early termination. Density contrasts are descriptive; there are
no rankings, significance claims, confidence intervals or promotion decisions.

## Interpretation

A completed discovery run is not a completed full-panel census. The original
split leaves one rule/seed cell entirely reserved, and many scheduler/cell
combinations may also be reserved. Counts and pooled summaries describe only the
fixed discovery panel at a two-event horizon. They do not estimate the prevalence
of organization in arbitrary rules, establish sustained persistence, or show
context-sensitive interactions. R00's one-edge ancestry/commutation limits and
the R02 50-event intervention criterion still apply.

## Commands

The original attempt was launched after tests and source sealing:

```sh
python3 -B -m unittest discover -s tests -v
python3 -B scripts/atlas_r03.py seal --binary build/msru
python3 -B scripts/atlas_r03.py launch --binary build/msru
```

These are provenance commands, not instructions to rerun a consumed registration.
For an existing local attempt, use an unused output directory for a read-only audit:

```sh
python3 -B scripts/analyze_r03.py --directory results/r03b-001 \
  --output-directory results/r03b-readonly-recheck
```

Bulk traces and per-cell CSV remain local under ignored results directories;
public compact receipts and reports bind their content hashes. A fresh clone
without those artifacts cannot reproduce a saved-result audit. Regenerating world
data is a new separately identified attempt, not a repair of this one.
