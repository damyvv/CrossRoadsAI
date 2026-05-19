# Conflict-derived signal groups for lane control

CrossRoadsAI will model one signal head per lane but control them through conflict-derived **Signal Groups** instead of independent per-lane timing. Group compatibility is derived from geometric path conflicts, **Clearance Interval** is applied as explicit all-red time between groups, and left turns are protected-only in the first release. This was chosen to preserve safety invariants across 2/3/4-arm topologies while avoiding fragile hand-maintained compatibility matrices.
