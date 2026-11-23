# Phase 37 — multiweek external-model robustness

**Classification:** retrospective robustness audit of the Phase 36 local experiment; no prospective improvement claim.

## GW6–11 weekly score comparison

| GW | Variant | Predicted XI+C | Actual XI+C | Δ actual vs baseline | Captain ID (actual) | Formation | XI overlap | MAE / RMSE |
| ---: | --- | ---: | ---: | ---: | --- | --- | ---: | --- |
| 6 | baseline | 67.94 | 67 | +0 | 75 (2) | 3-4-3 | 11/11 | 1.343 / 2.606 |
| 6 | team_form | 70.29 | 56 | -11 | 75 (2) | 3-4-3 | 9/11 | 1.345 / 2.609 |
| 6 | opponent_defense | 69.71 | 67 | +0 | 75 (2) | 3-4-3 | 11/11 | 1.352 / 2.606 |
| 6 | combined | 71.36 | 66 | -1 | 75 (2) | 3-4-3 | 10/11 | 1.355 / 2.612 |
| 7 | baseline | 76.76 | 41 | +0 | 12 (6) | 3-4-3 | 11/11 | 1.254 / 2.348 |
| 7 | team_form | 77.61 | 41 | +0 | 12 (6) | 3-4-3 | 11/11 | 1.247 / 2.338 |
| 7 | opponent_defense | 75.92 | 42 | +1 | 12 (6) | 3-4-3 | 10/11 | 1.250 / 2.338 |
| 7 | combined | 78.91 | 52 | +11 | 12 (6) | 3-4-3 | 9/11 | 1.242 / 2.325 |
| 8 | baseline | 73.71 | 85 | +0 | 12 (11) | 3-4-3 | 11/11 | 1.055 / 2.059 |
| 8 | team_form | 79.82 | 74 | -11 | 12 (11) | 3-5-2 | 10/11 | 1.053 / 2.055 |
| 8 | opponent_defense | 75.52 | 76 | -9 | 12 (11) | 5-3-2 | 8/11 | 1.051 / 2.047 |
| 8 | combined | 79.59 | 76 | -9 | 12 (11) | 3-4-3 | 10/11 | 1.051 / 2.043 |
| 9 | baseline | 79.30 | 45 | +0 | 12 (2) | 4-4-2 | 11/11 | 1.227 / 2.395 |
| 9 | team_form | 82.50 | 49 | +4 | 12 (2) | 4-3-3 | 10/11 | 1.228 / 2.401 |
| 9 | opponent_defense | 81.41 | 45 | +0 | 12 (2) | 4-4-2 | 11/11 | 1.225 / 2.381 |
| 9 | combined | 85.82 | 49 | +4 | 12 (2) | 4-3-3 | 10/11 | 1.231 / 2.395 |
| 10 | baseline | 75.92 | 43 | +0 | 12 (3) | 3-4-3 | 11/11 | 1.406 / 2.618 |
| 10 | team_form | 78.90 | 39 | -4 | 12 (3) | 3-4-3 | 10/11 | 1.407 / 2.617 |
| 10 | opponent_defense | 79.19 | 43 | +0 | 12 (3) | 3-4-3 | 11/11 | 1.411 / 2.613 |
| 10 | combined | 81.46 | 39 | -4 | 12 (3) | 3-4-3 | 10/11 | 1.411 / 2.611 |
| 11 | baseline | 72.40 | 70 | +0 | 148 (5) | 3-4-3 | 11/11 | 1.217 / 2.277 |
| 11 | team_form | 76.45 | 70 | +0 | 148 (5) | 3-4-3 | 11/11 | 1.214 / 2.268 |
| 11 | opponent_defense | 74.72 | 75 | +5 | 12 (10) | 3-4-3 | 11/11 | 1.213 / 2.264 |
| 11 | combined | 79.44 | 75 | +5 | 12 (10) | 3-4-3 | 11/11 | 1.213 / 2.257 |

## Combined versus baseline attribution

| GW | Combined − baseline | XI player Δ | Captain Δ | Baseline-only players (actual) | Combined-only players (actual) |
| ---: | ---: | ---: | ---: | --- | --- |
| 6 | -1 | -1 | +0 | Massadio Haidara (132): 1.0 actual / 4.58 predicted | Davinson Sanchez Mina (516): 0.0 actual / 4.80 predicted |
| 7 | +11 | +11 | +0 | Anfernee Jamal Dijksteel (120): 0.0 actual / 4.77 predicted, Berkan İsmail Kutlu (212): 2.0 actual / 5.27 predicted | Diaa Sabi'a (136): 8.0 actual / 5.32 predicted, Florent Hadergjonaj (427): 5.0 actual / 4.54 predicted |
| 8 | -9 | -9 | +0 | Adrian Dawid Benedyczak (75): 11.0 actual / 5.13 predicted | Jesus Andres Ramirez Diaz (237): 2.0 actual / 5.47 predicted |
| 9 | +4 | +4 | +0 | Berkan İsmail Kutlu (212): 8.0 actual / 5.65 predicted | Gift Emmanuel Orban (148): 12.0 actual / 5.98 predicted |
| 10 | -4 | -4 | +0 | Claudio Winck Neto (94): 10.0 actual / 4.98 predicted | Chibuike Godfrey Nwaiwu (37): 6.0 actual / 5.27 predicted |
| 11 | +5 | +0 | +5 | none | none |

Combined advantage **+6** = XI changes +1 + captain changes +5. Every weekly and total decomposition reconciles exactly. Shared players cancel. No bench substitution or chip is modeled.

## Robustness

Weekly wins/losses/ties: **3/3/0**. Mean difference +1.000, median +1.500, sample standard deviation 7.127. Mean player-level MAE delta +0.0002; RMSE delta -0.0100 (combined minus baseline).

| Omitted GW | Remaining combined advantage |
| ---: | ---: |
| 6 | +7 |
| 7 | -5 |
| 8 | +15 |
| 9 | +2 |
| 10 | +10 |
| 11 | +1 |

The leave-one-week-out range shows that removing GW7 reverses the advantage. Six weeks are insufficient for a significance or superiority claim. The GW11 baseline here scored 70 under the Phase 36 historical pool and feature setup; it is a different experiment from the Phase 32 GW11 baseline lineup that scored 75. These scores must not be merged.

### Individual-player accounting sensitivity

The values below remove one player’s observed contribution from lineup-difference arithmetic across weeks. They **do not** reoptimize either squad and are not attainable counterfactual scores.

| Player ID | Net lineup-difference contribution | Combined advantage without contribution |
| ---: | ---: | ---: |
| 148 | +12 | -6 |
| 75 | -11 | +17 |
| 212 | -10 | +16 |
| 94 | -10 | +16 |
| 136 | +8 | -2 |
| 37 | +6 | +0 |
| 427 | +5 | +1 |
| 237 | +2 | +4 |
| 132 | -1 | +7 |
| 516 | +0 | +6 |
| 120 | +0 | +6 |

## Data rights and leakage audit

| Feature | Historical availability classification |
| --- | --- |
| Team goals, xG, shots, shots on target | Matches are dated before each target GW; CSV bytes were first observed after GW11. Publication by each earlier deadline is **unverified**. |
| Opponent strength and home/away form | Derived from the same retrospectively obtained CSV; publication timing unverified. |
| Target fixture/opponent | Official fixture archive was captured 2026-10-28; earlier GW6–9 pre-deadline snapshot unavailable. |
| Player club, price, availability | Historical deadline-time snapshots unavailable; retrospective proxy. |

The [Football-Data fair-use policy](https://football-data.co.uk/contact.php) limits free use to light personal/academic access and does not grant commercial or heavy AI training use. No new CSV download occurred in this audit. These features must not be promoted into production from this evidence.

## Recommendation

Continue combined-feature experiments only on newly timestamped, permitted pre-deadline captures. Prioritize expected-minutes and status calibration because Phase 35 found consequential zero-minute errors; then assess captain decisions and team features on the same prospective weeks. No alternative free provider has measured player/lineup coverage and confirmed reuse rights here, so switching provider now is unsupported. Wait for genuine prospective results before changing production weights.

Focused tests verify exact score decomposition, leave-one-week-out accounting and source-cutoff handling. Frozen predictions and production settings were untouched.
