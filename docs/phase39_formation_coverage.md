# Phase 39 — complete formation coverage

**Policy change:** new optimization considers all eight standard TFF formations. Frozen predictions and snapshots remain unchanged.

## Official rules and implementation

The [current official TFF help](https://tfffantezilig.com/yardim?tab=sss) lists: 3-4-3, 3-5-2, 4-3-3, 4-4-2, 4-5-1, 5-2-3, 5-3-2, 5-4-1. It also requires a 15-player squad of 2 GK, 5 DEF, 5 MID and 3 FWD, with one starting GK and eleven total starters. Enumerating 3–5 DEF, 2–5 MID and 1–3 FWD subject to ten outfield starters produces exactly these eight formations. The old list omitted **5-2-3**.

The optimizer now derives formations from those position bounds. Its default policy is `current_tff_v2`; `legacy_pre39_v1` preserves the former seven-formation behavior for historical replays. Existing budget, club, captain and eligibility logic were not changed. Legacy replay bundles explicitly use the legacy policy.

## Historical before/after replays

| GW | Candidates | Old formation | New formation | XI overlap | Old → new captain | Old → new objective | Gain | Old → new fantasy xPts | Old → new actual |
| ---: | ---: | --- | --- | ---: | --- | ---: | ---: | ---: | ---: |
| 6 | 572 | 3-4-3 | 3-4-3 | 11/11 | 75 → 75 | 68.1174 → 68.1174 | +0.0000 | 67.94 → 67.94 | 67 → 67 |
| 8 | 572 | 3-4-3 | 3-4-3 | 11/11 | 12 → 12 | 73.9088 → 73.9088 | +0.0000 | 73.71 → 73.71 | 85 → 85 |
| 11 | 572 | 3-4-3 | 3-4-3 | 11/11 | 148 → 148 | 72.5836 → 72.5836 | +0.0000 | 72.40 → 72.40 | 70 → 70 |

All three comparisons use the same reconstructed player pool and predicted xPts for both policies. Actual scores were loaded only for evaluation after the lineups were selected. Per-formation statuses, XI and bench IDs are in JSON. These reconstructed pools do not establish point-in-time pre-deadline feasibility.

## Optimality and compatibility

The small synthetic test independently enumerates feasible XIs and captains and matches the CP-SAT objective. Regression tests enumerate the official eight formations, confirm 5-2-3 is reachable and verify legacy mode excludes it. A time-limited `feasible` result would not prove global optimality; each replay records whether every evaluated formation returned `optimal`.

The selected historical weeks show whether the missing formation caused modeled objective loss in these pools only. A zero gain does not prove it never matters; a synthetic pool demonstrates a case where 5-2-3 wins. Old saved predictions are not rewritten, and replays can request `legacy_pre39_v1`.

Focused regression suite: 16 passed, including eight formation-selection cases, a brute-force small-pool optimum, legacy replay routing, forced-selection and captain-scoring checks. No production prediction weights, frozen records, or eligibility thresholds were changed.
