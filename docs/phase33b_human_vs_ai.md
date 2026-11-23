# Phase 33B — GW11 human vs AI decisions

**Classification:** user-reported genuine pre-deadline selection versus six approximate retrospective model replays. The human selection time is user-attested; no timestamped lineup export was supplied.

## Human squad and official results

| Role | Position | Player (TFF ID) | Club ID | GW11 minutes | Official points |
| --- | --- | --- | ---: | ---: | ---: |
| XI | GK | Serhat Öztaşdelen (130) | 4 | 90 | 9 |
| XI | DEF | Anfernee Jamal Dijksteel (120) | 4 | 90 | 6 |
| XI | DEF | Claudio Winck Neto (94) | 3 | 90 | 7 |
| XI | DEF | Stefan Savic (27) | 1 | 90 | 6 |
| XI | MID | Berkan İsmail Kutlu (212) | 4 | 90 | 11 |
| Captain | MID | Mason Will John Greenwood (176) | 6 | 64 | 16 |
| XI | MID | Orkun Kökçü (281) | 9 | 70 | 2 |
| XI | MID | Aleksey Batrakov (877) | 17 | 83 | 10 |
| Vice-captain | FWD | Victor James Osimhen (507) | 17 | 0 | 0 |
| XI | FWD | Gift Emmanuel Orban (148) | 5 | 90 | 5 |
| XI | FWD | Dusan Vlahovic (593) | 9 | 86 | 12 |
| Bench | GK | Bahadır Han Güngördü (216) | 7 | 90 | 2 |
| Reported auto-sub | DEF | Michael Amir Murillo Bermudez (277) | 9 | 70 | 5 |
| Bench | DEF | Fuka-Arthur Masuaku Kawela (597) | 7 | 90 | 1 |
| Bench | MID | Ernest Muçi (4) | 1 | 80 | 3 |

User formation: **3-4-3**. Starting XI official points: **84**. Greenwood captain extra: **+16**. Project evaluator total (XI + captain): **100**. Murillo’s reported automatic substitution: **+5**, yielding **105** if the substitution applies without removing any nonzero XI points. User-reported official total: **105**. Remaining difference: **+0**.

The project evaluator counts XI plus captain once more and has no auto-substitution, manager-card or Nostradamus scoring implementation. The [official TFF rules](https://tfffantezilig.com/yardim?tab=kurallar-1) say a zero-minute starter is replaced by a playing bench player in bench order when the resulting formation is legal; captain points are doubled. Murillo is the first outfield substitute, played 70 minutes, and replacing Osimhen makes a legal 4-4-2 with two forwards. Thus the official scoring rule supports the +5 substitution. The arithmetic exactly reconciles 105 without additional card or Nostradamus points; account-level ledger evidence was not supplied to independently exclude such adjustments.

## Six model comparisons

Human minus model. XI delta is human-only player points minus model-only player points; shared players cancel. Captain delta is Greenwood’s extra points minus the model captain’s extra points. Murillo is a conditional extra and is not included in the project-scoring gap.

| Model | Shared XI | Human-only pts | Model-only pts | XI Δ | Captain Δ | Project gap | With Murillo | Reported 105 gap |
| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| baseline_5w | 4/11 | 55 | 36 | +19 | +6 | +25 | +30 | +30 |
| short_form_3w | 6/11 | 46 | 16 | +30 | +13 | +43 | +48 | +48 |
| stable_8w | 3/11 | 61 | 40 | +21 | +6 | +27 | +32 | +32 |
| uniform_xg | 6/11 | 46 | 17 | +29 | +13 | +42 | +47 | +47 |
| position_aware_xg | 6/11 | 46 | 16 | +30 | +13 | +43 | +48 | +48 |
| rest_days_control | 6/11 | 46 | 16 | +30 | +13 | +43 | +48 | +48 |

### Exact lineup differences

**baseline_5w** — shared: Stefan Savic (27) 6 actual / 5.59 xPts, Claudio Winck Neto (94) 7 actual / 6.37 xPts, Gift Emmanuel Orban (148) 5 actual / 6.49 xPts, Berkan İsmail Kutlu (212) 11 actual / 5.97 xPts.

Human only: Anfernee Jamal Dijksteel (120) 6 pts, Serhat Öztaşdelen (130) 9 pts, Mason Will John Greenwood (176) 16 pts, Orkun Kökçü (281) 2 pts, Victor James Osimhen (507) 0 pts, Dusan Vlahovic (593) 12 pts, Aleksey Batrakov (877) 10 pts. Model only: Mohamed Salah Hamed Mahrous Ghaly (12) 10 actual / 7.15 xPts, Andre Onana Onana (22) 6 actual / 6.17 xPts, Guram Giorbelidze (48) 1 actual / 5.98 xPts, Adrian Dawid Benedyczak (75) 7 actual / 5.62 xPts, Diaa Sabi'a (136) 10 actual / 5.36 xPts, Eldor Shomurodov (404) 2 actual / 5.79 xPts, Samuel Leo Beat Ballet (600) 0 actual / 5.65 xPts.

Model captain Mohamed Salah Hamed Mahrous Ghaly added 10; Greenwood added 16. Model formation 3-4-3, bench: Serhat Öztaşdelen (130) 9 actual / 4.99 xPts, 90 min, Amar Gerxhaliu (53) 1 actual / 4.93 xPts, 90 min, Chidozie Collins Awaziem (217) 2 actual / 4.06 xPts, 90 min, Franco Daryl Tongya Heubang (346) 2 actual / 4.91 xPts, 90 min.

**short_form_3w** — shared: Stefan Savic (27) 6 actual / 5.92 xPts, Claudio Winck Neto (94) 7 actual / 6.75 xPts, Serhat Öztaşdelen (130) 9 actual / 5.30 xPts, Gift Emmanuel Orban (148) 5 actual / 6.62 xPts, Berkan İsmail Kutlu (212) 11 actual / 5.61 xPts, Victor James Osimhen (507) 0 actual / 5.80 xPts.

Human only: Anfernee Jamal Dijksteel (120) 6 pts, Mason Will John Greenwood (176) 16 pts, Orkun Kökçü (281) 2 pts, Dusan Vlahovic (593) 12 pts, Aleksey Batrakov (877) 10 pts. Model only: Ernest Muçi (4) 3 actual / 7.67 xPts, Mohamed Salah Hamed Mahrous Ghaly (12) 10 actual / 6.02 xPts, Guram Giorbelidze (48) 1 actual / 5.29 xPts, Franco Daryl Tongya Heubang (346) 2 actual / 5.69 xPts, Samuel Leo Beat Ballet (600) 0 actual / 6.05 xPts.

Model captain Ernest Muçi added 3; Greenwood added 16. Model formation 3-5-2, bench: İrfan Can Eğribayat (195) 3 actual / 4.65 xPts, 90 min, Chidozie Collins Awaziem (217) 2 actual / 5.15 xPts, 90 min, Adem Arous (84) 7 actual / 4.93 xPts, 90 min, Eldor Shomurodov (404) 2 actual / 5.45 xPts, 86 min.

**stable_8w** — shared: Claudio Winck Neto (94) 7 actual / 5.32 xPts, Gift Emmanuel Orban (148) 5 actual / 5.79 xPts, Berkan İsmail Kutlu (212) 11 actual / 5.67 xPts.

Human only: Stefan Savic (27) 6 pts, Anfernee Jamal Dijksteel (120) 6 pts, Serhat Öztaşdelen (130) 9 pts, Mason Will John Greenwood (176) 16 pts, Orkun Kökçü (281) 2 pts, Victor James Osimhen (507) 0 pts, Dusan Vlahovic (593) 12 pts, Aleksey Batrakov (877) 10 pts. Model only: Ernest Muçi (4) 3 actual / 4.68 xPts, Mohamed Salah Hamed Mahrous Ghaly (12) 10 actual / 8.37 xPts, Andre Onana Onana (22) 6 actual / 5.91 xPts, Guram Giorbelidze (48) 1 actual / 5.63 xPts, Amar Gerxhaliu (53) 1 actual / 4.56 xPts, Adrian Dawid Benedyczak (75) 7 actual / 6.05 xPts, Diaa Sabi'a (136) 10 actual / 5.25 xPts, Eldor Shomurodov (404) 2 actual / 6.22 xPts.

Model captain Mohamed Salah Hamed Mahrous Ghaly added 10; Greenwood added 16. Model formation 3-4-3, bench: Serhat Öztaşdelen (130) 9 actual / 4.95 xPts, 90 min, Milan Skriniar (172) 6 actual / 4.30 xPts, 90 min, Anfernee Jamal Dijksteel (120) 6 actual / 3.96 xPts, 90 min, Samuel Leo Beat Ballet (600) 0 actual / 4.32 xPts, 0 min.

**uniform_xg** — shared: Stefan Savic (27) 6 actual / 6.51 xPts, Claudio Winck Neto (94) 7 actual / 6.58 xPts, Serhat Öztaşdelen (130) 9 actual / 5.55 xPts, Gift Emmanuel Orban (148) 5 actual / 6.67 xPts, Berkan İsmail Kutlu (212) 11 actual / 5.88 xPts, Victor James Osimhen (507) 0 actual / 6.04 xPts.

Human only: Anfernee Jamal Dijksteel (120) 6 pts, Mason Will John Greenwood (176) 16 pts, Orkun Kökçü (281) 2 pts, Dusan Vlahovic (593) 12 pts, Aleksey Batrakov (877) 10 pts. Model only: Ernest Muçi (4) 3 actual / 8.43 xPts, Mohamed Salah Hamed Mahrous Ghaly (12) 10 actual / 6.62 xPts, Chidozie Collins Awaziem (217) 2 actual / 5.14 xPts, Eldor Shomurodov (404) 2 actual / 5.62 xPts, Samuel Leo Beat Ballet (600) 0 actual / 6.09 xPts.

Model captain Ernest Muçi added 3; Greenwood added 16. Model formation 3-4-3, bench: Alexander Nübel (280) 7 actual / 4.59 xPts, 90 min, Michael Amir Murillo Bermudez (277) 5 actual / 4.90 xPts, 70 min, Guram Giorbelidze (48) 1 actual / 4.84 xPts, 89 min, Leandro Trossard (273) 15 actual / 5.10 xPts, 90 min.

**position_aware_xg** — shared: Stefan Savic (27) 6 actual / 6.08 xPts, Claudio Winck Neto (94) 7 actual / 7.29 xPts, Serhat Öztaşdelen (130) 9 actual / 6.09 xPts, Gift Emmanuel Orban (148) 5 actual / 6.48 xPts, Berkan İsmail Kutlu (212) 11 actual / 5.93 xPts, Victor James Osimhen (507) 0 actual / 6.05 xPts.

Human only: Anfernee Jamal Dijksteel (120) 6 pts, Mason Will John Greenwood (176) 16 pts, Orkun Kökçü (281) 2 pts, Dusan Vlahovic (593) 12 pts, Aleksey Batrakov (877) 10 pts. Model only: Ernest Muçi (4) 3 actual / 8.37 xPts, Mohamed Salah Hamed Mahrous Ghaly (12) 10 actual / 6.56 xPts, Guram Giorbelidze (48) 1 actual / 5.43 xPts, Chidozie Collins Awaziem (217) 2 actual / 5.53 xPts, Samuel Leo Beat Ballet (600) 0 actual / 5.93 xPts.

Model captain Ernest Muçi added 3; Greenwood added 16. Model formation 4-4-2, bench: Alexander Nübel (280) 7 actual / 4.54 xPts, 90 min, Adem Arous (84) 7 actual / 5.32 xPts, 90 min, Franco Daryl Tongya Heubang (346) 2 actual / 5.34 xPts, 90 min, Eldor Shomurodov (404) 2 actual / 5.42 xPts, 86 min.

**rest_days_control** — shared: Stefan Savic (27) 6 actual / 5.92 xPts, Claudio Winck Neto (94) 7 actual / 6.75 xPts, Serhat Öztaşdelen (130) 9 actual / 5.30 xPts, Gift Emmanuel Orban (148) 5 actual / 6.62 xPts, Berkan İsmail Kutlu (212) 11 actual / 5.61 xPts, Victor James Osimhen (507) 0 actual / 5.80 xPts.

Human only: Anfernee Jamal Dijksteel (120) 6 pts, Mason Will John Greenwood (176) 16 pts, Orkun Kökçü (281) 2 pts, Dusan Vlahovic (593) 12 pts, Aleksey Batrakov (877) 10 pts. Model only: Ernest Muçi (4) 3 actual / 7.67 xPts, Mohamed Salah Hamed Mahrous Ghaly (12) 10 actual / 6.02 xPts, Guram Giorbelidze (48) 1 actual / 5.29 xPts, Franco Daryl Tongya Heubang (346) 2 actual / 5.69 xPts, Samuel Leo Beat Ballet (600) 0 actual / 6.05 xPts.

Model captain Ernest Muçi added 3; Greenwood added 16. Model formation 3-5-2, bench: İrfan Can Eğribayat (195) 3 actual / 4.65 xPts, 90 min, Chidozie Collins Awaziem (217) 2 actual / 5.15 xPts, 90 min, Adem Arous (84) 7 actual / 4.93 xPts, 90 min, Eldor Shomurodov (404) 2 actual / 5.45 xPts, 86 min.

## Decisions and evidence

Greenwood scored **16**; his captaincy added the same amount beyond his XI score. The models captained Salah (10 actual) or Muçi (3 actual). The human captain advantage is therefore +6 against Baseline/Stable and +13 against the other four models. This is an observed outcome, not evidence Greenwood was predictably the better captain before the deadline.

Osimhen played **0 minutes** and scored **0**. Four models started him; Baseline and Stable did not. His zero is present in the human XI and those model XIs. Under the [official substitution rule](https://tfffantezilig.com/yardim?tab=kurallar-1), Murillo adds five points and the final human formation becomes 4-4-2. The project evaluator leaves zero-minute starters in place, so its model totals remain on a different scoring basis.

Berkan, Batrakov, Orban, Vlahovic and the other human choices have exact official points in the squad table. The local player archive prices sum to **100.0M** for the human 15 and their club counts respect the three-player limit; those prices are not verified at the GW11 deadline. The Phase 32 artifact’s high-scoring unselected list includes Greenwood and Vlahovic; both were in the historical short-form candidate pool, but candidate eligibility alone does not establish budget feasibility for a model replacement squad or pre-deadline superiority.

### Demonstrated errors versus hypotheses

- **Verified:** zero-minute Osimhen was selected by four models and the human; the project’s actual-score evaluator omits automatic substitutions. Greenwood’s captain outcome exceeded the model captains’ outcomes.
- **Hypotheses:** expected minutes, lineup probability, availability, recent-form windows, opponent strength, team strength and team-level xG may have affected selections. The artifacts do not retain pre-deadline injury/lineup evidence or per-player feature contributions needed to attribute these causally.
- **External-statistics limit:** the existing xG variants used team-level Football-Data matches, not verified player xG/xA. Their one-week outcomes do not establish xG reliability or value.

## Free pre-deadline data priorities

| Priority | Feature and free source | Needed evidence before deadline | Feasibility / limit |
| ---: | --- | --- | --- |
| 1 | Official TFF player status and dated squad/fixture notices | Timestamped status, suspension and expected availability per player | Official identity is reliable; historical deadline snapshots must be captured prospectively |
| 2 | Team-published starting XI and club injury notices | Published timestamp, player ID match and expected role | Often free, but confirmed XI may arrive after fantasy deadline; only earlier notices qualify |
| 3 | Official recent starts/minutes | GW1–10 rows observed before deadline; lagged participation features | Already available, but source availability time and calibration need auditing |
| 4 | Free Football-Data team results/xG | Pre-deadline retrieval timestamp, match coverage and opponent features | Existing 81-match archive is usable with publication lag; no player xG or guaranteed freshness |
| 5 | Official fixture, venue and rest schedule | Snapshot and reschedule timestamps before deadline | Free and stable identifiers; late changes require new observations |

Test these features across multiple genuinely timestamped gameweeks before changing weights. No paid API is recommended.

## Scientific limits and verification

The six model replays use GW10 histories first retrieved after the GW11 deadline, unverified deadline prices, frozen October 31 metadata and postmatch price proxies. Phase 32B found unchanged model XIs under its two distinct price states. The three genuine saved GW11 predictions remain separate (saved short-form actual 57; saved stable actual 76). No GW11 outcomes were used to generate new lineups here.

All comparison equations are asserted in code. Focused regression tests cover captain arithmetic, lineup differences and the conditional substitution. No frozen prediction or previous report was modified.
