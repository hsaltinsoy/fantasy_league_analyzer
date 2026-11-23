# Phase 25 — GW12 optimizer diagnostics

**Classification:** exploratory frozen-input analysis, not a new prediction. Snapshot `ceddd5ae-a154-411b-9581-31a484c87f5f`; shared replay input hash `8029bd1b4525fd5fe5fb9835bfea1ea8e7a274289604afc3f188dfa62b87aa1d`. The full per-player minutes audit, six projection pools, forced XI and bench lists, and sensitivity runs are in [phase25_diagnostics.json](phase25_diagnostics.json). No saved prediction was changed.

## Critical input limitation

All 572 players with historical rows have a latest saved history week of **GW9**; one player has no history. Thus the GW12 optimizer used no GW10–GW11 player-week history, despite the live TFF player summary containing newer cumulative values. All six models share this limitation. The data do not establish how refreshed history would change selections. Updating the historical ingest before a future capture is the highest priority; do not backfill or mutate this frozen snapshot.

## Osimhen

Victor James Osimhen is TFF player **507**, club **17**, FWD, price **12.0**. Frozen weekly minutes GW1–GW9 are **90, 90, 90, 33, 0, 0, 13, 90, 88**. The last-four participation proxy is **0.710** (threshold **0.250**); official availability is `AVAILABLE`, factor 1. He has a fixture, valid price, historical rows, and passes every production gate. The five models that omit him do so after optimization, not eligibility filtering. The latest live summary in the frozen input reports 555 total minutes; it is not a substitute for missing GW10–GW11 weekly history.

| Model | Osimhen xPts | Eligible FWD rank | Saved cost | Saved objective | Forced squad objective (Δ) | Forced XI objective (Δ) | Forced XI cost |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_5w | 2.834 | 10 | 85.0 | 75.2252 | 74.2739 (−0.9513) | 72.1652 (−3.0600) | 89.5 |
| short_form_3w | 5.160 | 5 | 88.5 | 73.9714 | 73.0198 (−0.9516) | 72.9684 (−1.0030) | 94.5 |
| stable_8w | 4.151 | 5 | 91.5 | 71.9428 | 70.4753 (−1.4675) | 70.2118 (−1.7310) | 97.5 |
| uniform_xg | 5.934 | 4 | 87.5 | 76.2407 | 76.1561 (−0.0846) | 76.1561 (−0.0846) | 90.0 |
| position_aware_xg | 5.818 | 4 | 90.0 | 76.9593 | 76.4873 (−0.4720) | 76.4873 (−0.4720) | 96.0 |
| rest_days_control | 5.160 | 5 | 88.5 | 73.9714 | 73.0198 (−0.9516) | 72.9684 (−1.0030) | 94.5 |

All forced formation solves reported optimal. Forcing Osimhen into the squad leaves him on the bench in baseline_5w, short_form_3w, stable_8w and the rest control; he starts under both xG adjustments. In the forced XI, baseline replaces Shomurodov; short form, stable and rest replace Orban; position-aware replaces Benedyczak; uniform replaces Franculino and also changes the bench goalkeeper from Ederson to Onana. Full squad and captain outputs are in the JSON. These deltas compare objectives **within** each model only; model xPts scales are not treated as calibrated equivalents.

The saved starting forwards are Orban/Benedyczak/Shomurodov for baseline and stable; Orban/Benedyczak/Franculino for short form, uniform, position-aware and rest. Osimhen's higher price creates trade-offs, but budget alone does not exclude him: forced legal squads cost 89.5–97.5. Recent minutes and player-history form produce lower projections than those of selected forwards in most models. The xG variants bring him closer; uniform's objective loss is only 0.0846, an exploratory near-tie.

## Minutes filter

Exactly **252** players fail the `participation(past[-4:]) < 0.250` gate after passing history and fixture checks. The proxy is `clamp(0.65 × share of last four matches with minutes > 0 + 0.35 × min(1, average minutes / 75), 0.05, 1.00)`, rounded to three decimals. Of these 252, **216** have zero appearances in the last four saved rows and **36** have one; none have two or more. Their short-form projections if admitted reach at most **0.614 xPts**, and none exceed 1.0. The JSON records every ID, name, position, price, complete saved minutes sequence, recent appearances, threshold and hypothetical projection. One-appearance cases may include returners, but transfer status cannot be established from these fields alone. The missing-history player is excluded earlier and is not among the 252.

Controlled short-form eligibility thresholds, using identical frozen fixtures and history:

| Threshold | Eligible | Minutes excluded | Optimal objective | XI fantasy xPts | Cost |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 0.100 | 350 | 216 | 73.9714 | 73.93 | 88.5 |
| 0.250 production | 314 | 252 | 73.9714 | 73.93 | 88.5 |
| 0.400 | 290 | 276 | 73.9714 | 73.93 | 88.5 |

No threshold change altered this frozen optimum. This is not evidence that the gate will be harmless after histories are refreshed.

## Budget efficiency

Saved squads cost **85.0–91.5**, leaving **8.5–15.0**. Every saved model reports all formations proven optimal at its configured 100 budget. Lower-budget reruns show only small objective differences where the cap binds: position-aware loses 0.0217 at 85, short form/rest lose 0.0120 at 85, stable loses 0.0083 at 85 and 0.0041 at 90, uniform loses 0.0178 at 85. Baseline already costs 85. These results support that the optimizer is maximizing its configured projected objective rather than trying to spend money. Club and positional limits bind for some selections, but they do not explain all unspent funds. Expensive players are not proven systematically undervalued without finalized actual points; Osimhen's within-model forced results show that spending more on him usually lowers the current objective.

## Model disagreement

All six use the same 314 eligible players. The largest xPts ranges across models include Awaziem **2.113–6.065**, Antunes Gomez **1.636–5.097**, Osimhen **2.834–5.934**, Sonko Sundberg **0.860–3.926**, and Franculino **4.090–7.092**. These ranges include different form windows; they are not solely xG effects. Relative to short form, xG changes rankings materially: Lemina moves from rank 106 to 83 (uniform) or 89 (position-aware); Masuaku moves from 41 to 61 or 55. Saved XI members unique to one variant are Gerxhaliu and Kyziridis (baseline) and Onana and Sorescu (stable). The captain is Salah for baseline, stable, uniform and position-aware, and Sabi'a for short form and the rest control. The zero-weight rest control exactly reproduces short form's selected players, xPts, captain and objectives.

## Ranked next steps

1. **Restore weekly GW10–GW11 history ingestion before the next prospective capture.** Direct evidence: every saved GW12 history stops at GW9. This has the largest known potential impact on recent-form and minutes features; its direction is unknown.
2. **Audit the participation proxy after history freshness is fixed.** The frozen threshold sensitivity is flat and all 252 excluded projections are below 1 xPts, so changing the production threshold now lacks support.
3. **Evaluate xG adjustments against finalized official actuals before tuning.** Uniform xG nearly ties a forced Osimhen selection, but a higher projected total is not evidence of accuracy.
4. **Review price/club trade-offs with actual outcomes.** The optimizer uses budget as a cap, and forced premium spending usually lowers the model objective. Do not add a minimum-spend rule.

No production model weight or eligibility threshold was changed. The optimizer's new force arguments default to empty and affect only these explicitly requested experiments.
