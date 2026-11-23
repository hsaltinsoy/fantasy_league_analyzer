# Phase 38 — fantasy squad optimizer decision quality

**Scope:** read-only audit of the existing CP-SAT optimizer using historical predicted points only. No GW target results enter selection.

## Declared constraints and objective

The model selects exactly 15 players (2 GK, 5 DEF, 5 MID, 3 FWD), 11 starters, one starter captain, at most three players per club and cost at most 100. It solves seven legal formations separately. The objective is XI xPts plus risk-adjusted captain-bonus xPts plus 1% of bench xPts, less opposing attacker/defender risk penalties. This is **not** simply maximum raw fantasy xPts. The solver returns `optimal` or a time-limited `feasible` status per formation; only all-optimal statuses prove global optimality under the encoded objective.

## Reconstructed historical checks

| GW | Pool | Formation | Captain ID | Objective | Fantasy xPts | All formations optimal | Feasible one-swaps | Best one-swap gap |
| ---: | ---: | --- | ---: | ---: | ---: | --- | ---: | ---: |
| 6 | 572 | 3-4-3 | 75 | 68.1174 | 67.94 | True | 1725 | 0.351 |
| 8 | 572 | 3-4-3 | 12 | 73.9088 | 73.71 | True | 1537 | 0.056 |
| 11 | 572 | 3-4-3 | 148 | 72.5836 | 72.40 | True | 1649 | 0.533 |

Every returned lineup passed independent arithmetic checks for squad size, position counts, formation, club limit, budget, starter membership and captain membership. The recomputed objective matched solver output. A separate feasible one-player starter swap scan found no better modeled score where the reported gap is nonnegative. This neighborhood scan is not a global proof and ignores multi-player swaps. Per-formation solver statuses are in JSON.

## Captain consistency

For the reconstructed pools, the captain is checked against the maximum raw XI xPts; results are in JSON. In production Phase 32, `make_optimizer` applies a risk-adjusted `captain_bonus_xpts`, so the mathematically correct captain may differ from the highest raw xPts. The CP-SAT objective chooses captain jointly with the XI and bench. The TFF scoring rule doubles captain fantasy points; risk adjustment is a decision preference, not a different official scoring multiplier.

## Human GW11 squad under reconstructed constraints

Human squad check: 15 players (count valid: True), cost 97.0, formation 3-4-3, club limit True, budget legal True. Predicted objective **50.1200** versus optimizer **72.5836**; gap **+22.4636** under the same Phase 36 reconstructed pool. Human captain xPts 2.389; optimizer captain xPts 7.064.

Human-only XI projections: Serhat Öztaşdelen (130) 4.638, Aleksey Batrakov (877) 3.676, Mason Will John Greenwood (176) 2.389, Dusan Vlahovic (593) 4.761, Anfernee Jamal Dijksteel (120) 3.314, Orkun Kökçü (281) 1.112, Victor James Osimhen (507) 3.647.

Optimizer-only XI projections: Diaa Sabi'a (136) 5.562, Adrian Dawid Benedyczak (75) 5.612, Mohamed Salah Hamed Mahrous Ghaly (12) 6.803, Guram Giorbelidze (48) 5.657, Eldor Shomurodov (404) 5.798, Andre Onana Onana (22) 6.087, Samuel Leo Beat Ballet (600) 5.796.

## Sensitivity and limitations

The objective gives bench quality only 1% weight, so near-tied XI choices can change after small xPts perturbations. Captain is selected jointly and can change when captain-bonus terms are close. This audit reports objective margins to feasible one-swaps; a complete perturbation sweep was not run. Do not infer realized superiority from a higher predicted objective.

GW8 local perturbation: raising player 237 by 0.1 xPts led to 10/11 XI overlap, 4/4 bench overlap, formation 3-4-3, captain 12. This is a sensitivity probe, not evidence of a better forecast.

Historical prices and clubs are reconstructed from postmatch/current metadata, and GW11 human feasibility here is not proof of exact deadline feasibility. Phase 32 and 33B remain separate: the human 105 actual points and model actual points were never fed to the optimizer. The optimizer omits **5-2-3**, which [current official TFF help](https://tfffantezilig.com/yardim?tab=sss) lists as legal. This is a confirmed rules-coverage gap. Thus `all_formations_proven_optimal` proves optimality only among the seven encoded formations, not all eight official formations. This audit did not alter production rules or retrospective lineups.

## Priorities

1. Verify formation coverage against current official TFF rules and add regression coverage for any confirmed omission.
2. Persist per-formation optimality status and objective gap with every future lineup; a `feasible` time-limited result is not a proof.
3. Audit captain-bonus alternatives and near-tied lineups on genuinely timestamped future inputs.
4. Capture historical price, club and availability metadata before deadlines to make retrospective feasibility meaningful.

Focused tests cover constraint arithmetic and objective/alternative comparisons. Frozen snapshots, saved predictions and production weights were not modified.
