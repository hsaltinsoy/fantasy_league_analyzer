# Phase 40 — player projection errors and missed high scorers

**Classification:** approximate retrospective audit of the exact Phase 36 baseline 5W candidate pool and legacy optimizer policy. Phase 32 is a different GW11 experiment. No lineup is chosen using actual results.

## GW11 human versus optimizer projection accounting

Human predicted objective **50.1200**, Phase 36 optimizer **72.5836**. Optimizer advantage **+22.4636** = XI selection **+17.7780** + captain **+4.6750** + 1% bench tie-break **+0.0107**. This is the optimizer’s own prediction scale; it does not include a substitution expectation.

On official outcomes the human XI + captain scored **100.0**, the Phase 36 model XI + captain **70.0**. Model minus human is **-19** from XI choices and **-11** from captain choice, exactly **-30**. The human’s reported Murillo substitution adds **5** separately, reaching 105; no equivalent model substitution was applied. These realized outcomes are evaluation only.

| Squad | Role | Player | Predicted xPts | Actual GW11 | Minutes | Proxy | Error |
| --- | --- | --- | ---: | ---: | ---: | ---: | ---: |
| human | XI | Serhat Öztaşdelen (130) | 4.638 | 9 | 90 | 1.000 | -4.362 |
| human | XI | Anfernee Jamal Dijksteel (120) | 3.314 | 6 | 90 | 0.802 | -2.686 |
| human | XI | Claudio Winck Neto (94) | 5.926 | 7 | 90 | 1.000 | -1.074 |
| human | XI | Stefan Savic (27) | 5.469 | 6 | 90 | 1.000 | -0.531 |
| human | XI | Berkan İsmail Kutlu (212) | 5.558 | 11 | 90 | 1.000 | -5.442 |
| human | Captain | Mason Will John Greenwood (176) | 2.389 | 16 | 64 | 0.723 | -13.611 |
| human | XI | Orkun Kökçü (281) | 1.112 | 2 | 70 | 0.261 | -0.888 |
| human | XI | Aleksey Batrakov (877) | 3.676 | 10 | 83 | 0.998 | -6.324 |
| human | XI | Victor James Osimhen (507) | 3.647 | 0 | 0 | 0.944 | +3.647 |
| human | XI | Gift Emmanuel Orban (148) | 7.064 | 5 | 90 | 1.000 | +2.064 |
| human | XI | Dusan Vlahovic (593) | 4.761 | 12 | 86 | 1.000 | -7.239 |
| human | Bench | Bahadır Han Güngördü (216) | 4.841 | 2 | 90 | 1.000 | +2.841 |
| human | Bench | Michael Amir Murillo Bermudez (277) | 3.739 | 5 | 70 | 1.000 | -1.261 |
| human | Bench | Fuka-Arthur Masuaku Kawela (597) | 3.428 | 1 | 90 | 1.000 | +2.428 |
| human | Bench | Ernest Muçi (4) | 5.687 | 3 | 80 | 0.996 | +2.687 |
| optimizer | XI | Mohamed Salah Hamed Mahrous Ghaly (12) | 6.803 | 10 | 89 | 1.000 | -3.197 |
| optimizer | XI | Diaa Sabi'a (136) | 5.562 | 10 | 90 | 1.000 | -4.438 |
| optimizer | Captain | Gift Emmanuel Orban (148) | 7.064 | 5 | 90 | 1.000 | +2.064 |
| optimizer | XI | Berkan İsmail Kutlu (212) | 5.558 | 11 | 90 | 1.000 | -5.442 |
| optimizer | XI | Andre Onana Onana (22) | 6.087 | 6 | 90 | 1.000 | +0.087 |
| optimizer | XI | Stefan Savic (27) | 5.469 | 6 | 90 | 1.000 | -0.531 |
| optimizer | XI | Eldor Shomurodov (404) | 5.798 | 2 | 86 | 1.000 | +3.798 |
| optimizer | XI | Guram Giorbelidze (48) | 5.657 | 1 | 89 | 1.000 | +4.657 |
| optimizer | XI | Samuel Leo Beat Ballet (600) | 5.796 | 0 | 0 | 1.000 | +5.796 |
| optimizer | XI | Adrian Dawid Benedyczak (75) | 5.612 | 7 | 86 | 1.000 | -1.388 |
| optimizer | XI | Claudio Winck Neto (94) | 5.926 | 7 | 90 | 1.000 | -1.074 |
| optimizer | Bench | Bahadır Han Güngördü (216) | 4.841 | 2 | 90 | 1.000 | +2.841 |
| optimizer | Bench | Franco Daryl Tongya Heubang (346) | 5.025 | 2 | 90 | 1.000 | +3.025 |
| optimizer | Bench | Davinson Sanchez Mina (516) | 4.234 | 1 | 90 | 1.000 | +3.234 |
| optimizer | Bench | Amar Gerxhaliu (53) | 4.664 | 1 | 90 | 1.000 | +3.664 |

## GW6–11 projection quality

3432 player-weeks: MAE **1.250**, RMSE **2.392**. Calibration below is mean predicted versus mean actual by projection band, not a calibrated probabilistic forecast.

| Position | N | MAE | RMSE | Mean predicted / actual |
| --- | ---: | ---: | ---: | ---: |
| GK | 348 | 1.137 | 2.193 | 1.216 / 1.270 |
| DEF | 1104 | 1.447 | 2.527 | 1.211 / 1.391 |
| MID | 1440 | 1.208 | 2.405 | 1.076 / 1.511 |
| FWD | 540 | 1.033 | 2.187 | 0.919 / 1.248 |

| Predicted xPts band | N | MAE | RMSE | Mean predicted / actual |
| --- | ---: | ---: | ---: | ---: |
| 0-2 | 2608 | 0.774 | 1.835 | 0.397 / 0.798 |
| 2-4 | 634 | 2.503 | 3.460 | 2.851 / 3.047 |
| 4-6 | 164 | 3.462 | 3.902 | 4.783 / 4.122 |
| 6-8 | 23 | 4.587 | 5.485 | 6.550 / 5.217 |
| 8-plus | 3 | 4.377 | 4.897 | 9.426 / 6.333 |

| Actual minutes | N | MAE | Mean predicted / actual |
| --- | ---: | ---: | ---: |
| zero | 1729 | 0.311 | 0.311 / 0.000 |
| under60 | 620 | 1.188 | 0.953 / 1.285 |
| 60plus | 1083 | 2.785 | 2.472 / 3.722 |

High-upside realized scorers (10+ actual): 91 player-weeks, mean predicted 3.118 versus actual 12.088, MAE 8.970. This selection by **actual** score is descriptive and cannot be used to choose pre-deadline players.

## Missed scorers and participation errors

**GW6:** high actual (10+) with projection under 5: 11; high actual (8+) below 0.25 minutes gate: 0; high actual (10+) not in the 15 but feasible by one same-position squad replacement: 11; projected 4+ with zero minutes: 2.

**GW7:** high actual (10+) with projection under 5: 14; high actual (8+) below 0.25 minutes gate: 0; high actual (10+) not in the 15 but feasible by one same-position squad replacement: 14; projected 4+ with zero minutes: 1.

**GW8:** high actual (10+) with projection under 5: 11; high actual (8+) below 0.25 minutes gate: 1; high actual (10+) not in the 15 but feasible by one same-position squad replacement: 9; projected 4+ with zero minutes: 2.

**GW9:** high actual (10+) with projection under 5: 11; high actual (8+) below 0.25 minutes gate: 0; high actual (10+) not in the 15 but feasible by one same-position squad replacement: 11; projected 4+ with zero minutes: 1.

**GW10:** high actual (10+) with projection under 5: 18; high actual (8+) below 0.25 minutes gate: 2; high actual (10+) not in the 15 but feasible by one same-position squad replacement: 17; projected 4+ with zero minutes: 3.

**GW11:** high actual (10+) with projection under 5: 12; high actual (8+) below 0.25 minutes gate: 0; high actual (10+) not in the 15 but feasible by one same-position squad replacement: 12; projected 4+ with zero minutes: 1.

Repeated underprediction (at least two weeks with actual exceeding prediction by 3+): İrfan Can Kahveci (199) GW[6, 7, 9, 11], Tanguy Bemin Coulibaly (453) GW[8, 9, 10, 11], Guram Giorbelidze (48) GW[6, 7, 8, 9], Dusan Vlahovic (593) GW[6, 7, 10, 11], Diaa Sabi'a (136) GW[6, 7, 8, 11], Ederson Santana de Moraes (166) GW[6, 7, 8, 11], Adem Arous (84) GW[8, 9, 11], Aleksey Batrakov (877) GW[7, 10, 11], Oğuz Aydın (178) GW[7, 9, 11], Ernest Muçi (4) GW[7, 9, 10], Miguel Felipe Nunes Cardoso (746) GW[6, 8, 9], Haris Hajradinovic (92) GW[9, 10, 11]. Full player-level lists and minutes are in JSON. Repeated misses warrant study, but these thresholds and labels were applied after outcomes and do not prove predictability.

Repeated overprediction (at least two weeks with prediction exceeding actual by 3+): Mason Will John Greenwood (176) GW[7, 8, 9, 10], zero-minute GW[10], Deian Cristian Sorescu (567) GW[6, 7, 8, 11], zero-minute GW[], Mohamed Salah Hamed Mahrous Ghaly (12) GW[7, 9, 10], zero-minute GW[], Abdülkerim Bardakcı (533) GW[6, 9, 10], zero-minute GW[10], Adrian Dawid Benedyczak (75) GW[6, 7, 10], zero-minute GW[], Eldor Shomurodov (404) GW[7, 9, 11], zero-minute GW[], Paulo Victor de Mileo Vidotti (419) GW[9, 10, 11], zero-minute GW[], Lucas Sebastian Torreira di Pascua (539) GW[6, 7, 8], zero-minute GW[8], Yahia Fofana (362) GW[7, 8, 10], zero-minute GW[10], Jesus Andres Ramirez Diaz (237) GW[7, 8, 11], zero-minute GW[], Guram Giorbelidze (48) GW[10, 11], zero-minute GW[], Archibald Norman Brown (182) GW[8, 9], zero-minute GW[]. The JSON retains full lists. These outcome-defined groups are diagnostic, not causal.

## Missing information and controlled next experiments

| Priority | Hypothesis | Required free pre-deadline data | Evaluation / leakage control | Success criterion |
| ---: | --- | --- | --- | --- |
| 1 | Zero-minute and short-appearance errors depress selected-XI scores | Timestamped official status, recent starts/minutes, legally accessible club injury/squad notices | Prospective snapshots; compare zero-minute rate and player MAE on identical eligible pools | Lower zero-minute XI rate and MAE across multiple weeks without reducing realized XI score |
| 2 | Team attack and opponent defense explain repeated high-upside misses | Permitted, timestamped team xG/goals/shots and opponent conceded data | Event and publication time before deadline; paired model comparison on same players | Lower high-upside MAE and improved multiple-week XI scores |
| 3 | Captain potential differs from raw form | Save captain bonus alternatives and prior starts/minutes | Pre-deadline captain rankings; evaluate captain actuals after finalization | Consistent multiweek gain, not one exceptional week |

Existing free TFF fantasy histories contain points, starts and minutes; deadline-time status revisions are not archived. Football-Data offers team-level CSV with [restrictive fair-use terms](https://football-data.co.uk/contact.php), not player-level xG/xA. No unverified provider was used as if it supplied historical player availability.

## Limits and verification

All rows use history strictly before each target GW for xPts and participation proxies. The local player archive supplies current club/position labels and positive postmatch price proxies; exact historical prices, availability and club assignments are unverified. The GW11 comparison uses Phase 36 only and the original seven-formation legacy policy. Model weights, optimizer, frozen snapshots and earlier reports were not changed. Focused regression tests cover objective decomposition and outcome-independent feasibility.
