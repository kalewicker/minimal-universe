# R06i terminal outcome design

The proposed primary outcome is the fraction of the 50-event horizon completed,
averaged across the two target orientations minus the corresponding average
across the two sham orientations. Report horizon reach and joint structural
outcomes alongside it. An observed terminal branch contributes its actual
event count, including zero when it stops before any successful rewrite.

R06h established that horizon reach differs across the intervention in 143
parent/scheduler rows. The earlier R06c draft compared changes in reciprocity at
event 50. Completion-based filtering would change the population behind that
contrast. R06i proposes a different estimand that can include verified early
stops. The proposal uses synthetic outcome records and retains the failed R06g
completion gate. [R06c design](r06c-scientific-design.md) · [R06h diagnosis](../reports/r06h.md)

## Proposed outcomes

Let (T) be the number of successful events before verified match exhaustion,
restricted to at most (H=50). A horizon state contributes (T=H) even when
the final event removes the last eligible match. Event progress (T/H)
measures persistence measured in successful rewrites. It gives distinct values
to termination at events 2 and 49. The horizon reach indicator (1{T=H})
reports the original completion question directly.

For each threshold (q), the joint structural indicator is one when a branch
reaches the horizon, its reciprocity score is defined, and (Q_H\ge q). An early
terminal branch contributes zero to the indicator. This coding makes no
assignment to the unobserved (Q_H). A reached empty endpoint also contributes
zero to the indicator and remains explicitly undefined for (Q). A reached
nonempty endpoint with (Q_H=0) contributes one at threshold zero. Thus the
joint outcome at zero reports the fraction of branches with a defined horizon
score. Report empty endpoint counts and any conditional score summary with
their own denominators. The thresholds in the synthetic checks exercise
boundary behavior and carry no scientific acceptance meaning.

A reciprocal nonloop dyad contains a valid ordered path of two distinct edge
occurrences. Therefore a verified nonempty G2 terminal graph has (Q=0).
A verified empty graph has undefined (Q). Keep terminal-state metadata
with its own event index. Horizon reach, progress, and the joint structural
distribution answer different questions. The structural distribution combines
reach with endpoint allocation and can reflect differences present immediately
after rewiring. Evidence for recovery would require a separately specified
change-from-baseline claim.

## Unresolved branches and denominators

A resource-censored or unsupported branch with a verified prefix of (k<50)
successful events gives progress in ([k/50,1]). Horizon reach and each joint
indicator remain in ([0,1]). An unstarted branch has (k=0). These are
conservative bounds for a 50-event run under the same rule, scheduler and
orientation, treating resource limits as interruptions to observation.
They use the verified prefix alone. Additional constraints from the law or
additional evidence could narrow them. The proposed record contract assumes a
usable state at event 50 whenever it accepts `reached`. A missing horizon
snapshot needs a separately represented known-reach, unknown-structure status
before this contract can admit it.

Use uniform weights within each pair of orientations. Average the two lower
and two upper bounds on each side, then subtract the upper sham bound from
the lower target bound and the lower sham bound from the upper target bound.
This gives componentwise bounds. The coordinate extrema need not occur in a
single assignment of outcomes. An interval spanning zero leaves the sign
unresolved for that component. These are bounds on missing outcomes, distinct
from confidence intervals for a sampled population.

Report the full parent-generation roster and the pre-intervention eligibility
count. The branch contrast applies to the prespecified patch-eligible population.
An ineligible parent belongs in the generation denominator and gets no branch
contrast. All eligible planned orientations count, including those with
unresolved outcomes. All branches and schedulers for a group inherit that
group's partition. A future assay must freeze group weights and the population
before keeping a weighted average of group bounds. Schedulers and orientation
replicates within a group are repeated measurements. A sampling design needs
its own uncertainty and power analysis.

## Static acceptance and next boundary

Check the complete product of ten synthetic branch records across four
orientations, 10,000 quartets. An enumeration of extremal outcome completions
must agree with each interval calculation. The fixtures exercise arithmetic
and record boundaries, including a defensive empty-horizon record, independent
of reachability under any specific law. Check nine invalid records and retain
controls for early terminal versus horizon, two distinct terminal times, a
censored prefix at event 49, and empty versus defined zero at event 50.

A successful review supports a future synthetic bookkeeping adapter and a
separate registration of population, censoring, weights, and any inference.
Scientific testing requires those decisions and an admitted execution protocol.
