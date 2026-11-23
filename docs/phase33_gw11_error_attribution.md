# Phase 33 — GW11 model decision and error attribution

**Scope:** offline analysis of Phase 32 and 32B retrospective artifacts. The GW10 history and deadline-time metadata limitations remain; these are not genuine prospective six-model forecasts.

## Score reconciliation

| Model | XI actual | Captain extra | Substitution effect | Recorded actual |
| --- | ---: | ---: | ---: | ---: |
| baseline_5w | 65 | 10 | 0 | 75 |
| short_form_3w | 54 | 3 | 0 | 57 |
| stable_8w | 63 | 10 | 0 | 73 |
| uniform_xg | 55 | 3 | 0 | 58 |
| position_aware_xg | 54 | 3 | 0 | 57 |
| rest_days_control | 54 | 3 | 0 | 57 |

Bench players did not score in the Phase 32 fresh-squad evaluation; no automatic substitution was applied. Every row reconciles as XI + captain extra.

## Every pair of starting XIs

Each row is **first model minus second model**. Common player points cancel. XI difference equals first-only actual points minus second-only actual points; total gap also includes the captain bonus. No substitution effect occurred.

| First / second | Shared | First-only actual | Second-only actual | XI Δ | Captain Δ | Total Δ |
| --- | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_5w / short_form_3w | 7/11 | 25 | 14 | +11 | +7 | +18 |
| baseline_5w / stable_8w | 9/11 | 6 | 4 | +2 | +0 | +2 |
| baseline_5w / uniform_xg | 7/11 | 24 | 14 | +10 | +7 | +17 |
| baseline_5w / position_aware_xg | 7/11 | 25 | 14 | +11 | +7 | +18 |
| baseline_5w / rest_days_control | 7/11 | 25 | 14 | +11 | +7 | +18 |
| short_form_3w / stable_8w | 6/11 | 17 | 26 | -9 | -7 | -16 |
| short_form_3w / uniform_xg | 9/11 | 3 | 4 | -1 | +0 | -1 |
| short_form_3w / position_aware_xg | 10/11 | 2 | 2 | +0 | +0 | +0 |
| short_form_3w / rest_days_control | 11/11 | 0 | 0 | +0 | +0 | +0 |
| stable_8w / uniform_xg | 6/11 | 25 | 17 | +8 | +7 | +15 |
| stable_8w / position_aware_xg | 6/11 | 26 | 17 | +9 | +7 | +16 |
| stable_8w / rest_days_control | 6/11 | 26 | 17 | +9 | +7 | +16 |
| uniform_xg / position_aware_xg | 10/11 | 2 | 1 | +1 | +0 | +1 |
| uniform_xg / rest_days_control | 9/11 | 4 | 3 | +1 | +0 | +1 |
| position_aware_xg / rest_days_control | 10/11 | 2 | 2 | +0 | +0 | +0 |

### Player identities and projections for each pair

Each entry is `player (ID): predicted xPts / actual GW11 points`. Shared players are listed so the full XI overlap is inspectable.

**baseline_5w vs short_form_3w** — shared: Mohamed Salah Hamed Mahrous Ghaly (12): 7.15 / 10, Stefan Savic (27): 5.59 / 6, Guram Giorbelidze (48): 5.98 / 1, Claudio Winck Neto (94): 6.37 / 7, Gift Emmanuel Orban (148): 6.49 / 5, Berkan İsmail Kutlu (212): 5.97 / 11, Samuel Leo Beat Ballet (600): 5.65 / 0.

baseline_5w only: Andre Onana Onana (22): 6.17 / 6, Adrian Dawid Benedyczak (75): 5.62 / 7, Diaa Sabi'a (136): 5.36 / 10, Eldor Shomurodov (404): 5.79 / 2. short_form_3w only: Ernest Muçi (4): 7.67 / 3, Serhat Öztaşdelen (130): 5.30 / 9, Franco Daryl Tongya Heubang (346): 5.69 / 2, Victor James Osimhen (507): 5.80 / 0. Captains: Mohamed Salah Hamed Mahrous Ghaly (+10) vs Ernest Muçi (+3).

**baseline_5w vs stable_8w** — shared: Mohamed Salah Hamed Mahrous Ghaly (12): 7.15 / 10, Andre Onana Onana (22): 6.17 / 6, Guram Giorbelidze (48): 5.98 / 1, Adrian Dawid Benedyczak (75): 5.62 / 7, Claudio Winck Neto (94): 6.37 / 7, Diaa Sabi'a (136): 5.36 / 10, Gift Emmanuel Orban (148): 6.49 / 5, Berkan İsmail Kutlu (212): 5.97 / 11, Eldor Shomurodov (404): 5.79 / 2.

baseline_5w only: Stefan Savic (27): 5.59 / 6, Samuel Leo Beat Ballet (600): 5.65 / 0. stable_8w only: Ernest Muçi (4): 4.68 / 3, Amar Gerxhaliu (53): 4.56 / 1. Captains: Mohamed Salah Hamed Mahrous Ghaly (+10) vs Mohamed Salah Hamed Mahrous Ghaly (+10).

**baseline_5w vs uniform_xg** — shared: Mohamed Salah Hamed Mahrous Ghaly (12): 7.15 / 10, Stefan Savic (27): 5.59 / 6, Claudio Winck Neto (94): 6.37 / 7, Gift Emmanuel Orban (148): 6.49 / 5, Berkan İsmail Kutlu (212): 5.97 / 11, Eldor Shomurodov (404): 5.79 / 2, Samuel Leo Beat Ballet (600): 5.65 / 0.

baseline_5w only: Andre Onana Onana (22): 6.17 / 6, Guram Giorbelidze (48): 5.98 / 1, Adrian Dawid Benedyczak (75): 5.62 / 7, Diaa Sabi'a (136): 5.36 / 10. uniform_xg only: Ernest Muçi (4): 8.43 / 3, Serhat Öztaşdelen (130): 5.55 / 9, Chidozie Collins Awaziem (217): 5.14 / 2, Victor James Osimhen (507): 6.04 / 0. Captains: Mohamed Salah Hamed Mahrous Ghaly (+10) vs Ernest Muçi (+3).

**baseline_5w vs position_aware_xg** — shared: Mohamed Salah Hamed Mahrous Ghaly (12): 7.15 / 10, Stefan Savic (27): 5.59 / 6, Guram Giorbelidze (48): 5.98 / 1, Claudio Winck Neto (94): 6.37 / 7, Gift Emmanuel Orban (148): 6.49 / 5, Berkan İsmail Kutlu (212): 5.97 / 11, Samuel Leo Beat Ballet (600): 5.65 / 0.

baseline_5w only: Andre Onana Onana (22): 6.17 / 6, Adrian Dawid Benedyczak (75): 5.62 / 7, Diaa Sabi'a (136): 5.36 / 10, Eldor Shomurodov (404): 5.79 / 2. position_aware_xg only: Ernest Muçi (4): 8.37 / 3, Serhat Öztaşdelen (130): 6.09 / 9, Chidozie Collins Awaziem (217): 5.53 / 2, Victor James Osimhen (507): 6.05 / 0. Captains: Mohamed Salah Hamed Mahrous Ghaly (+10) vs Ernest Muçi (+3).

**baseline_5w vs rest_days_control** — shared: Mohamed Salah Hamed Mahrous Ghaly (12): 7.15 / 10, Stefan Savic (27): 5.59 / 6, Guram Giorbelidze (48): 5.98 / 1, Claudio Winck Neto (94): 6.37 / 7, Gift Emmanuel Orban (148): 6.49 / 5, Berkan İsmail Kutlu (212): 5.97 / 11, Samuel Leo Beat Ballet (600): 5.65 / 0.

baseline_5w only: Andre Onana Onana (22): 6.17 / 6, Adrian Dawid Benedyczak (75): 5.62 / 7, Diaa Sabi'a (136): 5.36 / 10, Eldor Shomurodov (404): 5.79 / 2. rest_days_control only: Ernest Muçi (4): 7.67 / 3, Serhat Öztaşdelen (130): 5.30 / 9, Franco Daryl Tongya Heubang (346): 5.69 / 2, Victor James Osimhen (507): 5.80 / 0. Captains: Mohamed Salah Hamed Mahrous Ghaly (+10) vs Ernest Muçi (+3).

**short_form_3w vs stable_8w** — shared: Ernest Muçi (4): 7.67 / 3, Mohamed Salah Hamed Mahrous Ghaly (12): 6.02 / 10, Guram Giorbelidze (48): 5.29 / 1, Claudio Winck Neto (94): 6.75 / 7, Gift Emmanuel Orban (148): 6.62 / 5, Berkan İsmail Kutlu (212): 5.61 / 11.

short_form_3w only: Stefan Savic (27): 5.92 / 6, Serhat Öztaşdelen (130): 5.30 / 9, Franco Daryl Tongya Heubang (346): 5.69 / 2, Victor James Osimhen (507): 5.80 / 0, Samuel Leo Beat Ballet (600): 6.05 / 0. stable_8w only: Andre Onana Onana (22): 5.91 / 6, Amar Gerxhaliu (53): 4.56 / 1, Adrian Dawid Benedyczak (75): 6.05 / 7, Diaa Sabi'a (136): 5.25 / 10, Eldor Shomurodov (404): 6.22 / 2. Captains: Ernest Muçi (+3) vs Mohamed Salah Hamed Mahrous Ghaly (+10).

**short_form_3w vs uniform_xg** — shared: Ernest Muçi (4): 7.67 / 3, Mohamed Salah Hamed Mahrous Ghaly (12): 6.02 / 10, Stefan Savic (27): 5.92 / 6, Claudio Winck Neto (94): 6.75 / 7, Serhat Öztaşdelen (130): 5.30 / 9, Gift Emmanuel Orban (148): 6.62 / 5, Berkan İsmail Kutlu (212): 5.61 / 11, Victor James Osimhen (507): 5.80 / 0, Samuel Leo Beat Ballet (600): 6.05 / 0.

short_form_3w only: Guram Giorbelidze (48): 5.29 / 1, Franco Daryl Tongya Heubang (346): 5.69 / 2. uniform_xg only: Chidozie Collins Awaziem (217): 5.14 / 2, Eldor Shomurodov (404): 5.62 / 2. Captains: Ernest Muçi (+3) vs Ernest Muçi (+3).

**short_form_3w vs position_aware_xg** — shared: Ernest Muçi (4): 7.67 / 3, Mohamed Salah Hamed Mahrous Ghaly (12): 6.02 / 10, Stefan Savic (27): 5.92 / 6, Guram Giorbelidze (48): 5.29 / 1, Claudio Winck Neto (94): 6.75 / 7, Serhat Öztaşdelen (130): 5.30 / 9, Gift Emmanuel Orban (148): 6.62 / 5, Berkan İsmail Kutlu (212): 5.61 / 11, Victor James Osimhen (507): 5.80 / 0, Samuel Leo Beat Ballet (600): 6.05 / 0.

short_form_3w only: Franco Daryl Tongya Heubang (346): 5.69 / 2. position_aware_xg only: Chidozie Collins Awaziem (217): 5.53 / 2. Captains: Ernest Muçi (+3) vs Ernest Muçi (+3).

**short_form_3w vs rest_days_control** — shared: Ernest Muçi (4): 7.67 / 3, Mohamed Salah Hamed Mahrous Ghaly (12): 6.02 / 10, Stefan Savic (27): 5.92 / 6, Guram Giorbelidze (48): 5.29 / 1, Claudio Winck Neto (94): 6.75 / 7, Serhat Öztaşdelen (130): 5.30 / 9, Gift Emmanuel Orban (148): 6.62 / 5, Berkan İsmail Kutlu (212): 5.61 / 11, Franco Daryl Tongya Heubang (346): 5.69 / 2, Victor James Osimhen (507): 5.80 / 0, Samuel Leo Beat Ballet (600): 6.05 / 0.

short_form_3w only: none. rest_days_control only: none. Captains: Ernest Muçi (+3) vs Ernest Muçi (+3).

**stable_8w vs uniform_xg** — shared: Ernest Muçi (4): 4.68 / 3, Mohamed Salah Hamed Mahrous Ghaly (12): 8.37 / 10, Claudio Winck Neto (94): 5.32 / 7, Gift Emmanuel Orban (148): 5.79 / 5, Berkan İsmail Kutlu (212): 5.67 / 11, Eldor Shomurodov (404): 6.22 / 2.

stable_8w only: Andre Onana Onana (22): 5.91 / 6, Guram Giorbelidze (48): 5.63 / 1, Amar Gerxhaliu (53): 4.56 / 1, Adrian Dawid Benedyczak (75): 6.05 / 7, Diaa Sabi'a (136): 5.25 / 10. uniform_xg only: Stefan Savic (27): 6.51 / 6, Serhat Öztaşdelen (130): 5.55 / 9, Chidozie Collins Awaziem (217): 5.14 / 2, Victor James Osimhen (507): 6.04 / 0, Samuel Leo Beat Ballet (600): 6.09 / 0. Captains: Mohamed Salah Hamed Mahrous Ghaly (+10) vs Ernest Muçi (+3).

**stable_8w vs position_aware_xg** — shared: Ernest Muçi (4): 4.68 / 3, Mohamed Salah Hamed Mahrous Ghaly (12): 8.37 / 10, Guram Giorbelidze (48): 5.63 / 1, Claudio Winck Neto (94): 5.32 / 7, Gift Emmanuel Orban (148): 5.79 / 5, Berkan İsmail Kutlu (212): 5.67 / 11.

stable_8w only: Andre Onana Onana (22): 5.91 / 6, Amar Gerxhaliu (53): 4.56 / 1, Adrian Dawid Benedyczak (75): 6.05 / 7, Diaa Sabi'a (136): 5.25 / 10, Eldor Shomurodov (404): 6.22 / 2. position_aware_xg only: Stefan Savic (27): 6.08 / 6, Serhat Öztaşdelen (130): 6.09 / 9, Chidozie Collins Awaziem (217): 5.53 / 2, Victor James Osimhen (507): 6.05 / 0, Samuel Leo Beat Ballet (600): 5.93 / 0. Captains: Mohamed Salah Hamed Mahrous Ghaly (+10) vs Ernest Muçi (+3).

**stable_8w vs rest_days_control** — shared: Ernest Muçi (4): 4.68 / 3, Mohamed Salah Hamed Mahrous Ghaly (12): 8.37 / 10, Guram Giorbelidze (48): 5.63 / 1, Claudio Winck Neto (94): 5.32 / 7, Gift Emmanuel Orban (148): 5.79 / 5, Berkan İsmail Kutlu (212): 5.67 / 11.

stable_8w only: Andre Onana Onana (22): 5.91 / 6, Amar Gerxhaliu (53): 4.56 / 1, Adrian Dawid Benedyczak (75): 6.05 / 7, Diaa Sabi'a (136): 5.25 / 10, Eldor Shomurodov (404): 6.22 / 2. rest_days_control only: Stefan Savic (27): 5.92 / 6, Serhat Öztaşdelen (130): 5.30 / 9, Franco Daryl Tongya Heubang (346): 5.69 / 2, Victor James Osimhen (507): 5.80 / 0, Samuel Leo Beat Ballet (600): 6.05 / 0. Captains: Mohamed Salah Hamed Mahrous Ghaly (+10) vs Ernest Muçi (+3).

**uniform_xg vs position_aware_xg** — shared: Ernest Muçi (4): 8.43 / 3, Mohamed Salah Hamed Mahrous Ghaly (12): 6.62 / 10, Stefan Savic (27): 6.51 / 6, Claudio Winck Neto (94): 6.58 / 7, Serhat Öztaşdelen (130): 5.55 / 9, Gift Emmanuel Orban (148): 6.67 / 5, Berkan İsmail Kutlu (212): 5.88 / 11, Chidozie Collins Awaziem (217): 5.14 / 2, Victor James Osimhen (507): 6.04 / 0, Samuel Leo Beat Ballet (600): 6.09 / 0.

uniform_xg only: Eldor Shomurodov (404): 5.62 / 2. position_aware_xg only: Guram Giorbelidze (48): 5.43 / 1. Captains: Ernest Muçi (+3) vs Ernest Muçi (+3).

**uniform_xg vs rest_days_control** — shared: Ernest Muçi (4): 8.43 / 3, Mohamed Salah Hamed Mahrous Ghaly (12): 6.62 / 10, Stefan Savic (27): 6.51 / 6, Claudio Winck Neto (94): 6.58 / 7, Serhat Öztaşdelen (130): 5.55 / 9, Gift Emmanuel Orban (148): 6.67 / 5, Berkan İsmail Kutlu (212): 5.88 / 11, Victor James Osimhen (507): 6.04 / 0, Samuel Leo Beat Ballet (600): 6.09 / 0.

uniform_xg only: Chidozie Collins Awaziem (217): 5.14 / 2, Eldor Shomurodov (404): 5.62 / 2. rest_days_control only: Guram Giorbelidze (48): 5.29 / 1, Franco Daryl Tongya Heubang (346): 5.69 / 2. Captains: Ernest Muçi (+3) vs Ernest Muçi (+3).

**position_aware_xg vs rest_days_control** — shared: Ernest Muçi (4): 8.37 / 3, Mohamed Salah Hamed Mahrous Ghaly (12): 6.56 / 10, Stefan Savic (27): 6.08 / 6, Guram Giorbelidze (48): 5.43 / 1, Claudio Winck Neto (94): 7.29 / 7, Serhat Öztaşdelen (130): 6.09 / 9, Gift Emmanuel Orban (148): 6.48 / 5, Berkan İsmail Kutlu (212): 5.93 / 11, Victor James Osimhen (507): 6.05 / 0, Samuel Leo Beat Ballet (600): 5.93 / 0.

position_aware_xg only: Chidozie Collins Awaziem (217): 5.53 / 2. rest_days_control only: Franco Daryl Tongya Heubang (346): 5.69 / 2. Captains: Ernest Muçi (+3) vs Ernest Muçi (+3).

## Osimhen and forward choices

Osimhen (TFF 507) played **0 minutes** and scored **0 official points** in GW11. This is a verified nonappearance. The source artifacts do not contain an ex-ante minute forecast, so the precise minutes forecast error cannot be measured.

| Model | Osimhen xPts | Selected | Other starting forwards (actual) |
| --- | ---: | --- | --- |
| baseline_5w | unavailable in selected 15 | out | Gift Emmanuel Orban (5), Eldor Shomurodov (2), Adrian Dawid Benedyczak (7) |
| short_form_3w | 5.802 | XI | Gift Emmanuel Orban (5) |
| stable_8w | unavailable in selected 15 | out | Eldor Shomurodov (2), Adrian Dawid Benedyczak (7), Gift Emmanuel Orban (5) |
| uniform_xg | 6.041 | XI | Gift Emmanuel Orban (5), Eldor Shomurodov (2) |
| position_aware_xg | 6.055 | XI | Gift Emmanuel Orban (5) |
| rest_days_control | 5.802 | XI | Gift Emmanuel Orban (5) |

Baseline and Stable started Orban (5), Shomurodov (2), and Benedyczak (7), for 14 forward points. Short Form and the zero-weight Rest control started Orban (5) and Osimhen (0), for 5; Uniform xG started Orban (5), Shomurodov (2), and Osimhen (0), for 7; Position-aware xG started Orban (5) and Osimhen (0), for 5. The 7-point Benedyczak versus 0-point Osimhen contrast is observed, but it is not a standalone causal substitution: formation and other positions also changed.

## Salah captain decision

The rank below is Salah’s **uncaptained xPts rank within the selected XI**. Phase 32 did not persist the optimizer’s separate captain-bonus alternatives; therefore this is an observable projection rank, not a verified internal captain ranking.

| Model | Salah xPts | XI xPts rank | Captain | Highest XI xPts | Actual captain extra |
| --- | ---: | ---: | --- | --- | ---: |
| baseline_5w | 7.148 | 1/11 | yes | Mohamed Salah Hamed Mahrous Ghaly (7.148) | 10 |
| short_form_3w | 6.018 | 5/11 | no | Ernest Muçi (7.672) | 3 |
| stable_8w | 8.370 | 1/11 | yes | Mohamed Salah Hamed Mahrous Ghaly (8.370) | 10 |
| uniform_xg | 6.616 | 3/11 | no | Ernest Muçi (8.434) | 3 |
| position_aware_xg | 6.561 | 3/11 | no | Ernest Muçi (8.365) | 3 |
| rest_days_control | 6.018 | 5/11 | no | Ernest Muçi (7.672) | 3 |

Salah scored 10 official points. Baseline and Stable doubled him, adding **10** to each XI. The four other variants doubled Muçi, who scored 3, adding **3**. Thus the observed captain-choice component of each Baseline/Stable gap against those variants is **+7**. Salah’s higher projected XI xPts in Baseline/Stable and Muçi’s higher projection in the other variants are consistent with the captain choices; exact optimizer tie-break and risk-adjusted captain scores were not saved in these artifacts.

## Largest selected-player errors

Errors are predicted player xPts minus actual points, before captain doubling. The five rows in each direction use distinct TFF player IDs and show the most extreme model/player observation for each ID.

| Direction | Player | Model | Slot | Predicted | Actual | Error | Minutes |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| Over | Samuel Leo Beat Ballet (600) | uniform_xg | XI | 6.09 | 0 | +6.09 | 0 |
| Over | Victor James Osimhen (507) | position_aware_xg | XI | 6.05 | 0 | +6.05 | 0 |
| Over | Ernest Muçi (4) | uniform_xg | XI | 8.43 | 3 | +5.43 | 80 |
| Over | Guram Giorbelidze (48) | baseline_5w | XI | 5.98 | 1 | +4.98 | 89 |
| Over | Eldor Shomurodov (404) | stable_8w | XI | 6.22 | 2 | +4.22 | 86 |
| Under | Leandro Trossard (273) | uniform_xg | bench | 5.10 | 15 | -9.90 | 90 |
| Under | Berkan İsmail Kutlu (212) | short_form_3w | XI | 5.61 | 11 | -5.39 | 90 |
| Under | Diaa Sabi'a (136) | stable_8w | XI | 5.25 | 10 | -4.75 | 90 |
| Under | Serhat Öztaşdelen (130) | stable_8w | bench | 4.95 | 9 | -4.05 | 90 |
| Under | Mohamed Salah Hamed Mahrous Ghaly (12) | short_form_3w | XI | 6.02 | 10 | -3.98 | 89 |

### Observed match context for these errors

| Player | Opponent | Venue | Result | Goals | Assists | Clean sheet | Bonus |
| --- | --- | --- | --- | ---: | ---: | ---: | ---: |
| Samuel Leo Beat Ballet (600) | Galatasaray | A | 4-3 | 0 | 0 | 0 | 0 |
| Victor James Osimhen (507) | Amed | H | 4-3 | 0 | 0 | 0 | 0 |
| Ernest Muçi (4) | Alanyaspor | A | 0-2 | 0 | 0 | 0 | 0 |
| Guram Giorbelidze (48) | Rizespor | A | 2-1 | 0 | 0 | 0 | 0 |
| Eldor Shomurodov (404) | Göztepe | A | 1-2 | 0 | 0 | 0 | 0 |
| Leandro Trossard (273) | Gençlerbirliği | H | 3-0 | 0 | 3 | 1 | 3 |
| Berkan İsmail Kutlu (212) | Eyüpspor | A | 0-2 | 1 | 0 | 1 | 3 |
| Diaa Sabi'a (136) | Galatasaray | A | 4-3 | 1 | 0 | 0 | 3 |
| Serhat Öztaşdelen (130) | Eyüpspor | A | 0-2 | 0 | 0 | 1 | 2 |
| Mohamed Salah Hamed Mahrous Ghaly (12) | Alanyaspor | A | 0-2 | 1 | 0 | 0 | 2 |

## Mechanisms and evidential limits

**Minutes:** Samuel Leo Beat Ballet (600, up to 6.09 xPts), Victor James Osimhen (507, up to 6.05 xPts) earned zero minutes. Their nonappearance directly explains their realized zero, while the reason for nonappearance and pre-deadline knowability are unverified. Other differences could reflect fantasy events or minutes; projected minutes were not saved.

**Fixtures:** All models used the same frozen GW11 fixture inputs. Outcome rows contain actual opponent and result, but no saved per-player fixture multiplier or counterfactual projection without fixtures. Match outcomes and fantasy clean sheets can explain realized point components; they cannot establish that fixture weighting caused the model gap.

**xG adjustments:** Uniform and position-aware variants altered short-form projections using 81 pre-snapshot team-level external matches. Uniform scored 58 and position-aware 57 versus short-form 57. Their XI changes and captain choices are tabulated above. These are observed one-week differences; they do not identify an xG effect apart from optimizer interactions and do not establish long-run xG value.

**Prices:** Phase 32B tested the frozen Oct 31 price and the GW9/GW10 postmatch cost proxy. All XIs, benches, captains, predicted totals and realized ranking were unchanged. The postmatch cost is not a verified deadline price.

## Prioritized improvements

1. Capture official price and availability snapshots shortly before every deadline, with source and timestamp. The retrospective metadata gap limits the strength of every GW11 explanation.
2. Record predicted participation/minutes and the optimizer’s captain-bonus alternatives in future batch artifacts. This allows direct minutes-error and captain-choice audits.
3. Backtest participation and captain selection across many completed gameweeks before changing thresholds or weights. GW11 alone cannot justify tuning.
4. Preserve fixture-feature and xG adjustment provenance per player so future differences can be decomposed without refetching or inferring.

## Verification

Read-only analysis of existing JSON artifacts; no live API call or prediction replay. Every model total and every pairwise score gap was asserted to reconcile exactly. Focused tests cover pairwise accounting and unique-player error selection. Frozen predictions and production weights were not changed.
