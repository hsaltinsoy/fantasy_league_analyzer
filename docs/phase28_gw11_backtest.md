# Phase 28 — GW11 official results and historical input audit

**Classification:** read-only evaluation of three locally recorded pre-deadline predictions. A valid six-model GW11 comparison using history through GW10 is **blocked** by missing historical inputs. The separate GW12 refresh is an in-memory retrospective artifact, not a saved prediction.

## Official result status

The official TFF fixture response retrieved on 2026-11-09 reports all **9/9 GW11 matches FT** and the gameweek `finished: true`. Each match has `pointsAdded: true` and `bonusesAdded: true`; all three match days have `allPointsAdded: true` and `allBonusesAdded: true`. Official GW11 history rows have numeric fantasy points. The audit fetched histories for the 573 players in the frozen GW12 pool with **zero request failures**, and all 573 have one GW11 row. These API markers support treating current GW11 points and bonuses as complete; the feed does not provide an independent lock or revision guarantee. The exact observations and player rows are in [phase28_gw11_backtest.json](phase28_gw11_backtest.json) and [phase28_official_histories.json](phase28_official_histories.json).

## Historical inputs and leakage

The database holds three GW11 snapshots created on 2026-10-31, before the official 2026-11-06 16:00 UTC deadline: two identical `short_form_3w` predictions and one `stable_8w` prediction. Their frozen input hash is `3d10cc948ef74a9a21d4ebe1fa004158078b58633f4e095edc752676f0a207a0`. The snapshot pools contain 572 players with captured prices, availability and GW11 fixtures. All archived player histories stop at **GW9**, so the saved predictions were genuinely recorded before the deadline but used stale histories. Their local timestamps are not independent proof of pre-deadline publication.

No saved GW11 predictions exist for `baseline_5w`, `uniform_xg`, `position_aware_xg` or `rest_days_control`. The GW11 snapshots contain no frozen football-data match evidence for the xG variants. The official GW10 histories used in Phase 27B were first observed after the GW11 deadline; their pre-deadline availability is unproven. Current GW12 player prices or availability cannot replace the captured GW11 attributes. Consequently, a six-model GW11 comparison with histories through GW10 and identical historically valid non-history inputs cannot be established. No six-model accuracy ranking or xG benefit claim is made.

## Valid saved-prediction results

All 15 selected players in each saved lineup have a single GW11 row that passes gameweek ID, opponent, venue and numeric-points checks. Actual total is the XI point sum plus the captain's official points once more. MAE, RMSE and Spearman are calculated over each lineup's 15 selected players; they are not common-pool model metrics.

| Saved model | Predicted fantasy pts | Actual XI | Captain bonus | Actual total | Formation | Selected-player MAE | RMSE | Spearman |
| --- | ---: | ---: | ---: | ---: | --- | ---: | ---: | ---: |
| short_form_3w (two identical captures) | 76.61 | 56 | Giorbelidze: 1 | 57 | 3-4-3 | 3.500 | 3.936 | 0.140 |
| stable_8w | 72.05 | 66 | Salah: 10 | 76 | 4-3-3 | 3.438 | 4.394 | 0.097 |

The two short-form captures have identical lineups and outcomes and are one effective model observation. Their XI overlaps the stable XI by **8/11**. Stable's actual total is 19 higher in this week, largely including a 9-point captain-bonus difference; one week does not establish that a longer window is generally more accurate. The two lineups use different players, so their selected-player MAE and ranking correlations are not controlled common-player comparisons. No cross-model objective scores are compared.

## Player errors and participation

| Model | Player | Predicted | Official actual | Error (predicted − actual) |
| --- | --- | ---: | ---: | ---: |
| short form | Giorbelidze | 7.337 | 1 | +6.337 |
| short form | Franculino | 5.599 | 0 | +5.599 |
| short form | Awaziem | 7.012 | 2 | +5.012 |
| short form | Berkan Kutlu | 6.348 | 11 | −4.652 |
| stable | Greenwood | 4.544 | 16 | −11.456 |
| stable | Nwaiwu | 4.112 | 10 | −5.888 |
| stable | Berkan Kutlu | 5.928 | 11 | −5.072 |

Franculino was selected by short form, projected for 5.599 points, then played **0 minutes**. This is a clear participation miss. The saved predictions contain participation probabilities but no calibrated per-player predicted-minute values, so minute MAE cannot be calculated. The high actual scores of Greenwood and Nwaiwu show large underpredictions in the stable selected pool. A claim that any high-value player was *incorrectly excluded* requires a complete, historically valid candidate-level GW11 projection and common-pool evaluation; that evidence is unavailable. Full selected-player errors are in the JSON artifact.

## GW12 readiness

Official GW11 histories now cover **573/573** frozen GW12 players. The freshness audit reports `fresh` and its capture gate passes with GW11 as the latest completed week. An in-memory [GW12 refreshed version](phase28_gw12_refreshed.json) was prepared using the frozen GW12 players, fixtures, prices, availability and external evidence, with histories through GW11. All six variants returned legal lineups; eligible count is **322** for each. This artifact was generated after the original snapshot and is retrospective. It did not save or overwrite a tracking snapshot or prediction and must not be presented as the original pre-deadline forecast.

## Recommendation and checks

Preserve the three GW11 predictions as the only locally recorded pre-deadline GW11 evidence. Keep model weights unchanged. For a future comparable six-model evaluation, capture the same complete player, fixture, history and external-feature bundle before the deadline and retain source observation times. Evaluate on several finalized gameweeks with common-player errors before choosing a window or xG adjustment.

The Phase 28 audit confirmed the frozen GW11 input hash, checked all nine official result markers, verified selected-player row identity and 15/15 coverage for each saved prediction, fetched 573/573 GW11 histories, passed the GW12 freshness gate, and completed the six in-memory GW12 variants. Focused tests (`test_six_model_evaluation.py`, `test_history_freshness.py`, `test_capture_integrity.py`) passed: **10/10**. No database write, migration, commit or push was performed.
