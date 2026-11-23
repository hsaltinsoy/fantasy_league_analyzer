# Phase 32B — GW11 historical price sensitivity

**Classification:** retrospective price-only sensitivity of the approximate Phase 32 GW11 simulation. No scenario is a verified immediately pre-GW11 forecast.

## Price evidence

Official GW11 deadline: 2026-11-06T16:00:00Z. The frozen GW11 snapshot was captured 2026-10-31T20:57:09.759788+00:00 before the deadline, with a verified input hash. Its prices are observed at capture, but their validity at the later deadline cannot be established. The same 572 players, GW1–10 histories, GW11 fixtures, availability, external evidence, model settings and optimizer constraints are used in every scenario.

GW10 history `cost` was retrieved 2026-11-09T09:59:22.453463+00:00, after the deadline. This is a gameweek result field, with no independent pre-deadline price timestamp. Prior project audits classify it as a **postmatch price, not a verified deadline price**. It is therefore a plausible sensitivity input, not a historically verified GW11 price. GW9 postmatch cost was already embedded in the Oct 31 snapshot; its deadline-time interpretation is also unverified.

| Scenario | Source | Positive history cost | Snapshot fallback | Price differences vs snapshot | Status |
| --- | --- | ---: | ---: | ---: | --- |
| snapshot_oct31 | Oct 31 frozen player price | — | 0 | 0 | verified Oct 31 observation; stale at deadline |
| gw9_postmatch | GW9 history cost | 572 | 0 | 220 | postmatch proxy; deadline validity unverified |
| gw10_postmatch | GW10 history cost | 572 | 0 | 220 | postmatch proxy; deadline validity unverified |

The 220 GW10 differences comprise 0 increases and 220 decreases relative to frozen prices. Among changed players, deltas range from -0.5 to -0.5; all 220 IDs and values are in the JSON artifact. Zero/missing history costs are treated as unavailable, never as free players.

GW9 and GW10 history cost agree for 572 players with positive values in both weeks and differ for 0. Thus the GW9 and GW10 price scenarios are the same observed price state, not independent evidence of a deadline-time update. Comparison with GW11 postmatch costs is reserved for field-semantics audit and never enters a prediction.

## Six-model results

| Scenario | Model | XI overlap | XI in / out | Bench in / out | Captain | Formation | Cost | Pred xPts | Actual | Δ actual | Rank |
| --- | --- | ---: | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| snapshot_oct31 | baseline_5w | 11/11 | — / — | — / — | Mohamed Salah Hamed Mahrous Ghaly | 3-4-3 | 82.0 | 73.29 | 75 | +0 | 1 |
| snapshot_oct31 | short_form_3w | 11/11 | — / — | — / — | Ernest Muçi | 3-5-2 | 90.5 | 74.39 | 57 | +0 | 6 |
| snapshot_oct31 | stable_8w | 11/11 | — / — | — / — | Mohamed Salah Hamed Mahrous Ghaly | 3-4-3 | 86.0 | 71.84 | 73 | +0 | 2 |
| snapshot_oct31 | uniform_xg | 11/11 | — / — | — / — | Ernest Muçi | 3-4-3 | 96.0 | 77.56 | 58 | +0 | 3 |
| snapshot_oct31 | position_aware_xg | 11/11 | — / — | — / — | Ernest Muçi | 4-4-2 | 91.0 | 78.10 | 57 | +0 | 4 |
| snapshot_oct31 | rest_days_control | 11/11 | — / — | — / — | Ernest Muçi | 3-5-2 | 90.5 | 74.39 | 57 | +0 | 5 |
| gw9_postmatch | baseline_5w | 11/11 | — / — | — / — | Mohamed Salah Hamed Mahrous Ghaly | 3-4-3 | 79.0 | 73.29 | 75 | +0 | 1 |
| gw9_postmatch | short_form_3w | 11/11 | — / — | — / — | Ernest Muçi | 3-5-2 | 87.0 | 74.39 | 57 | +0 | 6 |
| gw9_postmatch | stable_8w | 11/11 | — / — | — / — | Mohamed Salah Hamed Mahrous Ghaly | 3-4-3 | 83.0 | 71.84 | 73 | +0 | 2 |
| gw9_postmatch | uniform_xg | 11/11 | — / — | — / — | Ernest Muçi | 3-4-3 | 93.0 | 77.56 | 58 | +0 | 3 |
| gw9_postmatch | position_aware_xg | 11/11 | — / — | — / — | Ernest Muçi | 4-4-2 | 88.0 | 78.10 | 57 | +0 | 4 |
| gw9_postmatch | rest_days_control | 11/11 | — / — | — / — | Ernest Muçi | 3-5-2 | 87.0 | 74.39 | 57 | +0 | 5 |
| gw10_postmatch | baseline_5w | 11/11 | — / — | — / — | Mohamed Salah Hamed Mahrous Ghaly | 3-4-3 | 79.0 | 73.29 | 75 | +0 | 1 |
| gw10_postmatch | short_form_3w | 11/11 | — / — | — / — | Ernest Muçi | 3-5-2 | 87.0 | 74.39 | 57 | +0 | 6 |
| gw10_postmatch | stable_8w | 11/11 | — / — | — / — | Mohamed Salah Hamed Mahrous Ghaly | 3-4-3 | 83.0 | 71.84 | 73 | +0 | 2 |
| gw10_postmatch | uniform_xg | 11/11 | — / — | — / — | Ernest Muçi | 3-4-3 | 93.0 | 77.56 | 58 | +0 | 3 |
| gw10_postmatch | position_aware_xg | 11/11 | — / — | — / — | Ernest Muçi | 4-4-2 | 88.0 | 78.10 | 57 | +0 | 4 |
| gw10_postmatch | rest_days_control | 11/11 | — / — | — / — | Ernest Muçi | 3-5-2 | 87.0 | 74.39 | 57 | +0 | 5 |

Rank is by official GW11 score, with model name breaking ties. Actual points equal XI points plus the captain’s points a second time; bench contributes zero. IDs in the lineup-change columns refer to official TFF player IDs. Full XI and bench player rows, predictions and outcomes are in the JSON artifact. Objectives are in the JSON and should only be compared within the same model.

## Baseline and stable sensitivity

**baseline_5w:** snapshot_oct31 75 actual, 73.29 predicted, 11/11 XI shared, captain Mohamed Salah Hamed Mahrous Ghaly; gw9_postmatch 75 actual, 73.29 predicted, 11/11 XI shared, captain Mohamed Salah Hamed Mahrous Ghaly; gw10_postmatch 75 actual, 73.29 predicted, 11/11 XI shared, captain Mohamed Salah Hamed Mahrous Ghaly.

**stable_8w:** snapshot_oct31 73 actual, 71.84 predicted, 11/11 XI shared, captain Mohamed Salah Hamed Mahrous Ghaly; gw9_postmatch 73 actual, 71.84 predicted, 11/11 XI shared, captain Mohamed Salah Hamed Mahrous Ghaly; gw10_postmatch 73 actual, 71.84 predicted, 11/11 XI shared, captain Mohamed Salah Hamed Mahrous Ghaly.

snapshot_oct31 realized ranking: baseline_5w (75) > stable_8w (73) > uniform_xg (58) > position_aware_xg (57) > rest_days_control (57) > short_form_3w (57).

gw9_postmatch realized ranking: baseline_5w (75) > stable_8w (73) > uniform_xg (58) > position_aware_xg (57) > rest_days_control (57) > short_form_3w (57).

gw10_postmatch realized ranking: baseline_5w (75) > stable_8w (73) > uniform_xg (58) > position_aware_xg (57) > rest_days_control (57) > short_form_3w (57).

## Interpretation and limitations

Every tested XI, bench, captain, formation and predicted total is unchanged. The 220 lower proxy prices reduce selected squad costs by 3.0–3.5, but no roster crosses an optimizer decision boundary. Baseline stays at 75 actual and Stable at 73; their ordering and the six-model realized-score ordering remain unchanged under the two distinct observed price states. This does not establish robustness to unobserved deadline prices or larger price changes.

Only price changes across scenarios. Official GW11 points are loaded after all 18 predictions are generated; they do not enter optimization. The GW10 history rows themselves were first observed after the GW11 deadline, and availability/fixture metadata also predates that deadline. Thus this isolates sensitivity to price assumptions within an approximate retrospective setup, not a validated pre-deadline price forecast.

GW10 `cost` may reflect an after-match or later-adjusted value. The available data do not establish when each price became selectable. The scenario cannot establish causal model superiority from one gameweek. The most defensible next step is to timestamp a player-price capture before each future deadline.

## Verification

The original frozen hash and all Phase 32 non-price inputs were checked. Prediction generation was completed before outcome loading. Focused tests cover price-only mutation, zero-cost fallback and outcome isolation. No saved snapshot, prediction, weights or optimizer rules were changed.
