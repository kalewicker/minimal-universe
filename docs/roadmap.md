# Revised implementation boundaries

1. **R00 — Audit.** Mathematical proofs, corrected semantics, fixed small fixtures,
   compact reproducible receipt. Stop after reviewable audit evidence.
2. **R01 — Reference kernels.** C++20 graph execution and SKI evaluation; independent
   Python graph replay and independent lambda semantics; transactional caps,
   stable identity, checkpoint/RNG contracts, overflow and corruption tests.
3. **R02 — Calibration.** Validate motif and causal measurements against known
   controls. Freeze numerical outcomes, effect thresholds, nulls, partitions,
   multiplicity policy, budget, and candidate promotion requirements.
4. **R03 — Baseline census.** Only after its own registered protocol. Preserve all
   attempts, errors, censored runs, and not-started cells. Do not rerun selectively.
5. **R04 — Conditional validation.** Held-out interventions and prediction only
   for candidates that pass frozen gates. Zero candidates is a valid completion.
6. **R05 — Extension proposal.** A two-edge LHS is a new experiment, never an
   implicit modification of the baseline grammar.

## Current position

R00–R02 engineering/calibration stages are complete. R03b completed its registered
two-event discovery subset; it did not execute a full-panel census or promote
candidates. [R04a](../reports/r04a.md) closed conditional validation without launch,
with no candidate statistics evaluated and no intervention effects measured.
All 16,774 reserved jobs remain unopened. [R05a](../reports/r05a.md) completed the
two-edge extension proposal and static design audit, including matching/aliasing
semantics, an explicit nonconfluent rule, and required controls. The next bounded
milestone is R05b: register engineering fixtures and budgets, implement a G2
reference kernel, and independently verify matching/replay. Measurement calibration
and a campaign require subsequent registrations. This is a design transition,
not a finding that the one-edge rules failed a scientific effect test.

Discovery, detector development, validation, and final testing use disjoint parent
trajectory groups. All branches/interventions inherit their parent's partition.
Compare baseline features B against B plus motifs on the same frozen prediction
target. Lack of significance alone is not a rejection of an effect hypothesis.

Size caps must permit the registered event horizon. Budget calibration precedes
production registration. Protocol changes produce a new version and retain
previous evidence. Public commits contain source, protocols, small fixtures and
reports; exclude private settings, local binaries, and bulk generated runs.
