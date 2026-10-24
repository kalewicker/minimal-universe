# R03p observer/runner contract

R03p registers six engineering fixtures under three schedulers, using separate
engineering identities and a fixed RNG seed. They do not consume production
discovery/holdout parents. The fixture panel covers early deletion, identity,
unsupported loop multiplicity, feedback, the eight-edge endpoint, and reversal.

## Observation and independent checking

`observe_r03.py` accepts only registered fixture IDs and schedulers. It runs the
unchanged native kernel and reconstructs snapshots from its event log, checking
consumed IDs, bindings, ancestry, fresh nodes, output ID ranges, and final state.
Observation is outside the kernel and cannot alter redex selection. Snapshots
contain motif coverage, reciprocal density, exact null distribution/status/mean,
and descriptive density-minus-mean. Rationals are numerator/denominator arrays.
Unavailable post-terminal snapshots are not padded with measurements.

The pilot checker independently re-executes each requested horizon with the R01
Python dictionary reference. Its measurement oracle uses R02's independent motif
orbit table/connectivity checks and generates target assignments recursively from
multiplicity counters, rather than the observer's permutation/deduplication code.
All native events, endpoints and observation values are compared exactly.

## Supervision and accounting

`bounded_runner.py` starts at most four workers, each in a new POSIX process
group including its native child. Monotonic deadlines cover execution and
observation together. Timeouts/output violations kill the process group and wait
for its leader. OS scheduling and cleanup can add latency: this is not a real-time
deadline or physical-memory isolation guarantee.

Nonblocking reads share a stdout-plus-stderr byte allowance. A successful JSON
result is checked again after adding its stored envelope. Oversized records become
compact `record_output_cap` failures. Other failures retain bounded diagnostics
and hashes. No failed job is retried.

Before dispatch, reserve a full per-job output allowance for every in-flight
worker and a separate allowance for the final accounting/status vector. Ledger
records are flushed after each completed job. Exhausted storage reservations leave
untouched entries `not_started_global_output_cap`; a global deadline terminates
active workers and leaves the suffix `not_started_global_wall_cap`. Reserved
entries never call the command factory. Conservative reservations can stop a batch
even when smaller eventual records might have fit.

An output directory must not already exist. Its retained content is exactly
`events.jsonl` and `summary.json`. The summary records total file-content bytes,
ledger/plan digests, limits, elapsed time and all job statuses. Indices bind records
to the ordered input plan; concurrent completion order can vary. Byte accounting
excludes filesystem allocation overhead and temporary configuration files.

An externally interrupted supervisor can leave a partial ledger without a final
summary. Preserve it as incomplete; automatic crash recovery/resume and selective
retries are not implemented. Files are hash-bound, not authenticated or physically
write-protected. There is no RSS cap. The future launch wrapper must retain its
authoritative input plan for resolving ledger indices.

## Holdouts and remaining launch work

The pilot statically validates all 27,720 production rows, including hashes,
parent keys, RNG seeds and inherited partitions. Only 10,946 classify as discovery;
a forged partition is rejected. None are dispatched. The generic supervisor trusts
validated input, so the future production adapter must validate the complete
manifest and mark holdouts reserved. It is not a security boundary against an
arbitrary Python caller. The pilot CLI has no production mode.

The next milestone must bind the frozen design, audited registry, kernel and
measurement receipts, and this pilot in a launch protocol; add and test the
production adapter; then execute only its declared discovery scope. Pilot
throughput does not guarantee that every atlas job fits its deadline. Budget stops
must remain visible as partial completion.

## Reproduce

With the R01 build and R03a manifest available, use fresh output destinations:

```sh
python3 -B -m unittest discover -s tests -v
python3 -B scripts/pilot_r03.py --binary build/msru \
  --manifest results/r03a-plan.jsonl --plan-receipt reports/r03a-plan.json \
  --directory results/r03p-recheck --output results/r03p-recheck.json
```

Timing, completion order and artifact hashes can vary. Fixed panel counts, exact
comparisons, source bindings and required fault statuses must pass. Preserve each
attempt separately.
