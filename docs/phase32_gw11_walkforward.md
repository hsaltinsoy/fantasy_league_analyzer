# Phase 32 — GW11 walk-forward backtest

**Classification:** approximate retrospective simulation, generated after GW11. These are not genuine pre-deadline predictions.

## Historical inputs and leakage checks

Official GW11 deadline: **2026-11-06T16:00:00Z**. Official GW11 fixtures are finished and every match and match day is marked points and bonuses added (checked 2026-11-09T11:50:54.162071+00:00). Player results cover all selected players.

Frozen GW11 snapshot `72226192-1049-4d89-b9a9-aec4d9da4709` was captured 2026-10-31T20:57:09.759788+00:00; original hash `3d10cc948ef74a9a21d4ebe1fa004158078b58633f4e095edc752676f0a207a0` verifies. It contains 572 players, prices, availability, GW11 fixtures, and history through GW9. One official GW10 row per player was appended, giving replay hash `697a6a942b3c190be52943b5a1140becded4e15587b72846111cac4a61b67727`. GW11 and later histories are excluded from predictions.

**Limitation:** GW10 rows were retrieved 2026-11-09T09:59:22.453463+00:00, after the deadline. Their pre-deadline publication is not timestamped. Snapshot prices, availability and fixtures are from Oct 31, before GW10 ended; their exact Nov 6 state is unavailable. GW10 history cost differs from frozen snapshot price for 220 players with a positive history cost; see JSON. Thus this is an approximate retrospective simulation of the requested cutoff. No current GW12 attributes were substituted. Actuals are loaded only after all six predictions return.

The two xG variants use 81 Football-Data matches imported before the frozen snapshot cutoff. No later external match data enters the replay. Rest-days control uses its existing zero-weight configuration. The historical legacy availability rule is used to reproduce the original model era; it can admit a `DEPARTED` status, so eligibility is approximate. Model weights, optimizer rules, and original records were untouched.

## Results, ranked by realized score

| Rank | Model | Eligible | Predicted | Actual | Pred − actual | Captain (extra actual) | Formation | Cost | Objective | MAE / RMSE (15) |
| ---: | --- | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | --- |
| 1 | baseline_5w | 317 | 73.29 | 75 | -1.71 | Mohamed Salah Hamed Mahrous Ghaly (+10) | 3-4-3 | 82.0 | 72.881 | 2.93 / 3.42 |
| 2 | stable_8w | 317 | 71.84 | 73 | -1.16 | Mohamed Salah Hamed Mahrous Ghaly (+10) | 3-4-3 | 86.0 | 71.318 | 2.76 / 3.21 |
| 3 | uniform_xg | 317 | 77.56 | 58 | +19.56 | Ernest Muçi (+3) | 3-4-3 | 96.0 | 77.254 | 3.67 / 4.45 |
| 4 | short_form_3w | 317 | 74.39 | 57 | +17.39 | Ernest Muçi (+3) | 3-5-2 | 90.5 | 74.138 | 3.32 / 3.78 |
| 5 | position_aware_xg | 317 | 78.10 | 57 | +21.10 | Ernest Muçi (+3) | 4-4-2 | 91.0 | 77.810 | 3.30 / 3.77 |
| 6 | rest_days_control | 317 | 74.39 | 57 | +17.39 | Ernest Muçi (+3) | 3-5-2 | 90.5 | 74.138 | 3.32 / 3.78 |

Actual = starting XI official points plus the captain’s points once more (double captain). Bench points are listed but do not count: this optimizer chooses a fresh squad and the existing evaluation implements no automatic substitution. MAE/RMSE compare uncaptained player xPts to actual points over each model’s selected 15; the player sets differ. Objectives are comparable only within a model configuration.

## Starting XI overlap

| Pair | Shared players |
| --- | ---: |
| baseline_5w / short_form_3w | 7/11 |
| baseline_5w / stable_8w | 9/11 |
| baseline_5w / uniform_xg | 7/11 |
| baseline_5w / position_aware_xg | 7/11 |
| baseline_5w / rest_days_control | 7/11 |
| short_form_3w / stable_8w | 6/11 |
| short_form_3w / uniform_xg | 9/11 |
| short_form_3w / position_aware_xg | 10/11 |
| short_form_3w / rest_days_control | 11/11 |
| stable_8w / uniform_xg | 6/11 |
| stable_8w / position_aware_xg | 6/11 |
| stable_8w / rest_days_control | 6/11 |
| uniform_xg / position_aware_xg | 10/11 |
| uniform_xg / rest_days_control | 9/11 |
| position_aware_xg / rest_days_control | 10/11 |

## baseline_5w

Formation 3-4-3; captain Mohamed Salah Hamed Mahrous Ghaly; XI actual 65, captain extra 10, final 75.

| Position | Player (TFF ID) | Club ID | Predicted xPts | Actual GW11 | Pred − actual |
| --- | --- | ---: | ---: | ---: | ---: |
| GK | Andre Onana Onana (22) | 1 | 6.17 | 6 | +0.17 |
| DEF | Claudio Winck Neto (94) | 3 | 6.37 | 7 | -0.63 |
| DEF | Guram Giorbelidze (48) | 2 | 5.98 | 1 | +4.98 |
| DEF | Stefan Savic (27) | 1 | 5.59 | 6 | -0.41 |
| MID | Mohamed Salah Hamed Mahrous Ghaly (12) **(C)** | 1 | 7.15 | 10 | -2.85 |
| MID | Berkan İsmail Kutlu (212) | 4 | 5.97 | 11 | -5.03 |
| MID | Samuel Leo Beat Ballet (600) | 5 | 5.65 | 0 | +5.65 |
| MID | Diaa Sabi'a (136) | 5 | 5.36 | 10 | -4.64 |
| FWD | Gift Emmanuel Orban (148) | 5 | 6.49 | 5 | +1.49 |
| FWD | Eldor Shomurodov (404) | 13 | 5.79 | 2 | +3.79 |
| FWD | Adrian Dawid Benedyczak (75) | 3 | 5.62 | 7 | -1.39 |

Substitutes (no score contribution):

| Position | Player (TFF ID) | Club ID | Predicted xPts | Actual GW11 | Pred − actual |
| --- | --- | ---: | ---: | ---: | ---: |
| GK | Serhat Öztaşdelen (130) | 4 | 4.99 | 9 | -4.01 |
| DEF | Amar Gerxhaliu (53) | 2 | 4.93 | 1 | +3.93 |
| DEF | Chidozie Collins Awaziem (217) | 7 | 4.06 | 2 | +2.06 |
| MID | Franco Daryl Tongya Heubang (346) | 11 | 4.91 | 2 | +2.91 |

## short_form_3w

Formation 3-5-2; captain Ernest Muçi; XI actual 54, captain extra 3, final 57.

| Position | Player (TFF ID) | Club ID | Predicted xPts | Actual GW11 | Pred − actual |
| --- | --- | ---: | ---: | ---: | ---: |
| GK | Serhat Öztaşdelen (130) | 4 | 5.30 | 9 | -3.70 |
| DEF | Claudio Winck Neto (94) | 3 | 6.75 | 7 | -0.25 |
| DEF | Stefan Savic (27) | 1 | 5.92 | 6 | -0.08 |
| DEF | Guram Giorbelidze (48) | 2 | 5.29 | 1 | +4.29 |
| MID | Ernest Muçi (4) **(C)** | 1 | 7.67 | 3 | +4.67 |
| MID | Samuel Leo Beat Ballet (600) | 5 | 6.05 | 0 | +6.05 |
| MID | Mohamed Salah Hamed Mahrous Ghaly (12) | 1 | 6.02 | 10 | -3.98 |
| MID | Franco Daryl Tongya Heubang (346) | 11 | 5.69 | 2 | +3.69 |
| MID | Berkan İsmail Kutlu (212) | 4 | 5.61 | 11 | -5.39 |
| FWD | Gift Emmanuel Orban (148) | 5 | 6.62 | 5 | +1.62 |
| FWD | Victor James Osimhen (507) | 17 | 5.80 | 0 | +5.80 |

Substitutes (no score contribution):

| Position | Player (TFF ID) | Club ID | Predicted xPts | Actual GW11 | Pred − actual |
| --- | --- | ---: | ---: | ---: | ---: |
| GK | İrfan Can Eğribayat (195) | 11 | 4.65 | 3 | +1.65 |
| DEF | Chidozie Collins Awaziem (217) | 7 | 5.15 | 2 | +3.15 |
| DEF | Adem Arous (84) | 3 | 4.93 | 7 | -2.07 |
| FWD | Eldor Shomurodov (404) | 13 | 5.45 | 2 | +3.45 |

## stable_8w

Formation 3-4-3; captain Mohamed Salah Hamed Mahrous Ghaly; XI actual 63, captain extra 10, final 73.

| Position | Player (TFF ID) | Club ID | Predicted xPts | Actual GW11 | Pred − actual |
| --- | --- | ---: | ---: | ---: | ---: |
| GK | Andre Onana Onana (22) | 1 | 5.91 | 6 | -0.09 |
| DEF | Guram Giorbelidze (48) | 2 | 5.63 | 1 | +4.63 |
| DEF | Claudio Winck Neto (94) | 3 | 5.32 | 7 | -1.68 |
| DEF | Amar Gerxhaliu (53) | 2 | 4.56 | 1 | +3.56 |
| MID | Mohamed Salah Hamed Mahrous Ghaly (12) **(C)** | 1 | 8.37 | 10 | -1.63 |
| MID | Berkan İsmail Kutlu (212) | 4 | 5.67 | 11 | -5.33 |
| MID | Diaa Sabi'a (136) | 5 | 5.25 | 10 | -4.75 |
| MID | Ernest Muçi (4) | 1 | 4.68 | 3 | +1.68 |
| FWD | Eldor Shomurodov (404) | 13 | 6.22 | 2 | +4.22 |
| FWD | Adrian Dawid Benedyczak (75) | 3 | 6.05 | 7 | -0.94 |
| FWD | Gift Emmanuel Orban (148) | 5 | 5.79 | 5 | +0.80 |

Substitutes (no score contribution):

| Position | Player (TFF ID) | Club ID | Predicted xPts | Actual GW11 | Pred − actual |
| --- | --- | ---: | ---: | ---: | ---: |
| GK | Serhat Öztaşdelen (130) | 4 | 4.95 | 9 | -4.05 |
| DEF | Milan Skriniar (172) | 6 | 4.30 | 6 | -1.70 |
| DEF | Anfernee Jamal Dijksteel (120) | 4 | 3.96 | 6 | -2.04 |
| MID | Samuel Leo Beat Ballet (600) | 5 | 4.32 | 0 | +4.32 |

## uniform_xg

Formation 3-4-3; captain Ernest Muçi; XI actual 55, captain extra 3, final 58.

| Position | Player (TFF ID) | Club ID | Predicted xPts | Actual GW11 | Pred − actual |
| --- | --- | ---: | ---: | ---: | ---: |
| GK | Serhat Öztaşdelen (130) | 4 | 5.55 | 9 | -3.44 |
| DEF | Claudio Winck Neto (94) | 3 | 6.58 | 7 | -0.42 |
| DEF | Stefan Savic (27) | 1 | 6.51 | 6 | +0.51 |
| DEF | Chidozie Collins Awaziem (217) | 7 | 5.14 | 2 | +3.14 |
| MID | Ernest Muçi (4) **(C)** | 1 | 8.43 | 3 | +5.43 |
| MID | Mohamed Salah Hamed Mahrous Ghaly (12) | 1 | 6.62 | 10 | -3.38 |
| MID | Samuel Leo Beat Ballet (600) | 5 | 6.09 | 0 | +6.09 |
| MID | Berkan İsmail Kutlu (212) | 4 | 5.88 | 11 | -5.12 |
| FWD | Gift Emmanuel Orban (148) | 5 | 6.67 | 5 | +1.67 |
| FWD | Victor James Osimhen (507) | 17 | 6.04 | 0 | +6.04 |
| FWD | Eldor Shomurodov (404) | 13 | 5.62 | 2 | +3.62 |

Substitutes (no score contribution):

| Position | Player (TFF ID) | Club ID | Predicted xPts | Actual GW11 | Pred − actual |
| --- | --- | ---: | ---: | ---: | ---: |
| GK | Alexander Nübel (280) | 9 | 4.59 | 7 | -2.41 |
| DEF | Michael Amir Murillo Bermudez (277) | 9 | 4.90 | 5 | -0.10 |
| DEF | Guram Giorbelidze (48) | 2 | 4.84 | 1 | +3.84 |
| MID | Leandro Trossard (273) | 9 | 5.10 | 15 | -9.90 |

## position_aware_xg

Formation 4-4-2; captain Ernest Muçi; XI actual 54, captain extra 3, final 57.

| Position | Player (TFF ID) | Club ID | Predicted xPts | Actual GW11 | Pred − actual |
| --- | --- | ---: | ---: | ---: | ---: |
| GK | Serhat Öztaşdelen (130) | 4 | 6.09 | 9 | -2.90 |
| DEF | Claudio Winck Neto (94) | 3 | 7.29 | 7 | +0.28 |
| DEF | Stefan Savic (27) | 1 | 6.08 | 6 | +0.08 |
| DEF | Chidozie Collins Awaziem (217) | 7 | 5.53 | 2 | +3.53 |
| DEF | Guram Giorbelidze (48) | 2 | 5.43 | 1 | +4.43 |
| MID | Ernest Muçi (4) **(C)** | 1 | 8.37 | 3 | +5.37 |
| MID | Mohamed Salah Hamed Mahrous Ghaly (12) | 1 | 6.56 | 10 | -3.44 |
| MID | Samuel Leo Beat Ballet (600) | 5 | 5.93 | 0 | +5.93 |
| MID | Berkan İsmail Kutlu (212) | 4 | 5.93 | 11 | -5.07 |
| FWD | Gift Emmanuel Orban (148) | 5 | 6.48 | 5 | +1.48 |
| FWD | Victor James Osimhen (507) | 17 | 6.05 | 0 | +6.05 |

Substitutes (no score contribution):

| Position | Player (TFF ID) | Club ID | Predicted xPts | Actual GW11 | Pred − actual |
| --- | --- | ---: | ---: | ---: | ---: |
| GK | Alexander Nübel (280) | 9 | 4.54 | 7 | -2.46 |
| DEF | Adem Arous (84) | 3 | 5.32 | 7 | -1.68 |
| MID | Franco Daryl Tongya Heubang (346) | 11 | 5.34 | 2 | +3.34 |
| FWD | Eldor Shomurodov (404) | 13 | 5.42 | 2 | +3.42 |

## rest_days_control

Formation 3-5-2; captain Ernest Muçi; XI actual 54, captain extra 3, final 57.

| Position | Player (TFF ID) | Club ID | Predicted xPts | Actual GW11 | Pred − actual |
| --- | --- | ---: | ---: | ---: | ---: |
| GK | Serhat Öztaşdelen (130) | 4 | 5.30 | 9 | -3.70 |
| DEF | Claudio Winck Neto (94) | 3 | 6.75 | 7 | -0.25 |
| DEF | Stefan Savic (27) | 1 | 5.92 | 6 | -0.08 |
| DEF | Guram Giorbelidze (48) | 2 | 5.29 | 1 | +4.29 |
| MID | Ernest Muçi (4) **(C)** | 1 | 7.67 | 3 | +4.67 |
| MID | Samuel Leo Beat Ballet (600) | 5 | 6.05 | 0 | +6.05 |
| MID | Mohamed Salah Hamed Mahrous Ghaly (12) | 1 | 6.02 | 10 | -3.98 |
| MID | Franco Daryl Tongya Heubang (346) | 11 | 5.69 | 2 | +3.69 |
| MID | Berkan İsmail Kutlu (212) | 4 | 5.61 | 11 | -5.39 |
| FWD | Gift Emmanuel Orban (148) | 5 | 6.62 | 5 | +1.62 |
| FWD | Victor James Osimhen (507) | 17 | 5.80 | 0 | +5.80 |

Substitutes (no score contribution):

| Position | Player (TFF ID) | Club ID | Predicted xPts | Actual GW11 | Pred − actual |
| --- | --- | ---: | ---: | ---: | ---: |
| GK | İrfan Can Eğribayat (195) | 11 | 4.65 | 3 | +1.65 |
| DEF | Chidozie Collins Awaziem (217) | 7 | 5.15 | 2 | +3.15 |
| DEF | Adem Arous (84) | 3 | 4.93 | 7 | -2.07 |
| FWD | Eldor Shomurodov (404) | 13 | 5.45 | 2 | +3.45 |

## Decisions and limitations

Osimhen (507): official GW11 0 points, 0 minutes. Selection: baseline_5w out, short_form_3w XI, stable_8w out, uniform_xg XI, position_aware_xg XI, rest_days_control XI.

Salah (12): official GW11 10 points, 89 minutes. Selection: baseline_5w captain, short_form_3w XI, stable_8w captain, uniform_xg XI, position_aware_xg XI, rest_days_control XI.

The short-form XI scored 57, while the stable XI scored 73 here. Short-form captain Ernest Muçi scored 3; stable captain Salah scored 10. The zero-weight rest-days control exactly matches short-form. The uniform xG variant scored 58 and the position-aware xG variant 57; these are team-level xG adjustments, not player xG estimates. The one-week result does not establish causal benefit or harm from xG or history-window length.

Largest selected-player misses (predicted minus actual): Leandro Trossard -9.90 (uniform_xg), Samuel Leo Beat Ballet +6.09 (uniform_xg), Victor James Osimhen +6.05 (position_aware_xg), Samuel Leo Beat Ballet +6.05 (short_form_3w), Samuel Leo Beat Ballet +6.05 (rest_days_control), Victor James Osimhen +6.04 (uniform_xg).

Highest actual scorers absent from every XI: Mason Will John Greenwood (176) 16 points [eligible], Wagner Fabricio Cardoso de Pina (28) 15 points [eligible], Leandro Trossard (273) 15 points [eligible], Oğuz Aydın (178) 13 points [eligible], İrfan Can Kahveci (199) 13 points [eligible], Ali Sowe (353) 13 points [eligible], Dusan Vlahovic (593) 12 points [eligible], Haris Hajradinovic (92) 11 points [eligible].

The short-form candidate screen excluded 248 players for recent participation and 7 for availability. The JSON identifies whether high actual scorers were in the short-form pool. This does not prove a threshold error without valid deadline-time availability.

The genuine pre-deadline saved GW11 predictions remain separate: short-form scored 57 actual points, stable scored 76 (Phase 28). They used GW9 history and are not the six retrospective GW10-history results above. Differences between short and stable windows are observations from one week, not evidence of long-run superiority. Pre-deadline GW10 publication and exact Nov 6 metadata remain unverified, so a fully valid prospective six-model comparison is blocked.

## Verification

The input hash was checked before replay, all 572 players received exactly one GW10 row, six models completed, and official GW11 points were applied after prediction generation. Focused pytest: 2 passed (actual-result isolation and captain/bench scoring). No saved GW11/GW12 snapshot or prediction was modified.
