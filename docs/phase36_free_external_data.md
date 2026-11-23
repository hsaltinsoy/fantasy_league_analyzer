# Phase 36 — free external team data experiment

**Classification:** retrospective experimental analysis. No frozen prediction or production weight changed.

## Source refresh and measured coverage

The existing local [Football-Data Turkey CSV](https://football-data.co.uk/turkeym.php) (SHA-256 `86af3b956c49ea86c5e1a58c8ac45237ba0b7bd52e46e5874e9697f09336bf08`) was observed 2026-11-09T11:25:38.562794+00:00. Its 99 matches map one-to-one to official fixtures and all 18 clubs. A separate idempotent experimental import stores exactly the 18 previously missing GW10–11 fixture IDs at `historical_data\experimental_phase36\missing_gw10_gw11.json`; the original 81-row PostgreSQL archive and frozen external evidence were not changed. Re-running with the same bytes is a no-op; conflicting bytes are rejected. No new CSV download was made.

Measured CSV coverage: 99/99 matches with both team xG, 99/99 with both shot counts, 99/99 with both shots-on-target counts. Player appearances, starting XIs, injuries/suspensions and player xG/xA: **0 verified rows** from this source. Other free provider marketing claims were not treated as tested endpoints; no authorized credentials or measured current-season player responses were available.

The [source fair-use policy](https://football-data.co.uk/contact.php) permits only light personal/academic automated downloads (at most twice weekly) and does not grant commercial or heavy AI training use. The existing local file was reused; licensing for any broader deployment needs separate review.

## Experimental features and cutoff

Each target GW uses only CSV matches dated **before the first target-week kickoff**. Up to five recent matches per team yield goals for/against, xG for/against, shots, shots on target, and home/away xG. Fixture opponent and venue come from the frozen official fixture archive. The team-form variant uses capped xG balance; opponent-defense uses capped opponent xG conceded; combined uses both. Venue adjustment is capped and shared by experimental variants. All coefficients are fixed small heuristics and are not production weights. Missing or fewer than two team matches leaves the player at baseline xPts and is counted.

**Point-in-time limitation:** the 99-row CSV was first observed after GW11. Event-date filtering prevents target-match statistics from entering a target prediction, but does not prove that every earlier row was published by that earlier deadline. These are reconstructed experiments, not genuine pre-deadline forecasts. Historical player club, price and availability are also imperfect.

## Controlled GW6–11 results

| GW | Variant | Prior matches | Candidate N | Missing-feature candidates | MAE | RMSE | XI actual + captain | Captain actual | Zero-minute XI |
| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |
| 6 | baseline | 45 | 572 | 0 | 1.343 | 2.606 | 67.0 | 2.0 | 0 |
| 6 | team_form | 45 | 572 | 0 | 1.345 | 2.609 | 56.0 | 2.0 | 1 |
| 6 | opponent_defense | 45 | 572 | 0 | 1.352 | 2.606 | 67.0 | 2.0 | 0 |
| 6 | combined | 45 | 572 | 0 | 1.355 | 2.612 | 66.0 | 2.0 | 0 |
| 7 | baseline | 54 | 572 | 0 | 1.254 | 2.348 | 41.0 | 6.0 | 1 |
| 7 | team_form | 54 | 572 | 0 | 1.247 | 2.338 | 41.0 | 6.0 | 1 |
| 7 | opponent_defense | 54 | 572 | 0 | 1.250 | 2.338 | 42.0 | 6.0 | 0 |
| 7 | combined | 54 | 572 | 0 | 1.242 | 2.325 | 52.0 | 6.0 | 0 |
| 8 | baseline | 63 | 572 | 0 | 1.055 | 2.059 | 85.0 | 11.0 | 1 |
| 8 | team_form | 63 | 572 | 0 | 1.053 | 2.055 | 74.0 | 11.0 | 2 |
| 8 | opponent_defense | 63 | 572 | 0 | 1.051 | 2.047 | 76.0 | 11.0 | 1 |
| 8 | combined | 63 | 572 | 0 | 1.051 | 2.043 | 76.0 | 11.0 | 1 |
| 9 | baseline | 72 | 572 | 0 | 1.227 | 2.395 | 45.0 | 2.0 | 0 |
| 9 | team_form | 72 | 572 | 0 | 1.228 | 2.401 | 49.0 | 2.0 | 0 |
| 9 | opponent_defense | 72 | 572 | 0 | 1.225 | 2.381 | 45.0 | 2.0 | 0 |
| 9 | combined | 72 | 572 | 0 | 1.231 | 2.395 | 49.0 | 2.0 | 0 |
| 10 | baseline | 81 | 572 | 0 | 1.406 | 2.618 | 43.0 | 3.0 | 0 |
| 10 | team_form | 81 | 572 | 0 | 1.407 | 2.617 | 39.0 | 3.0 | 0 |
| 10 | opponent_defense | 81 | 572 | 0 | 1.411 | 2.613 | 43.0 | 3.0 | 0 |
| 10 | combined | 81 | 572 | 0 | 1.411 | 2.611 | 39.0 | 3.0 | 0 |
| 11 | baseline | 90 | 572 | 0 | 1.217 | 2.277 | 70.0 | 5.0 | 1 |
| 11 | team_form | 90 | 572 | 0 | 1.214 | 2.268 | 70.0 | 5.0 | 1 |
| 11 | opponent_defense | 90 | 572 | 0 | 1.213 | 2.264 | 75.0 | 10.0 | 1 |
| 11 | combined | 90 | 572 | 0 | 1.213 | 2.257 | 75.0 | 10.0 | 1 |

Six-week total XI-plus-captain scores: baseline 351, team_form 329, opponent_defense 348, combined 357. Mean player MAE across weeks: baseline 1.250, team_form 1.249, opponent_defense 1.250, combined 1.250. These descriptive totals are too small and too retrospective to justify production integration.


All variants within a week use the identical historical player pool, prices, target fixture and optimizer. Only external team-feature adjustments change. Full XI, bench and captain IDs are in JSON. The squad score uses XI official points plus captain once more; automatic substitution and chips are outside this evaluator. Compare objectives only within the same configuration.

## Other free-source verification

| Source | Turkish current-season evidence | Automated access / use | Outcome |
| --- | --- | --- | --- |
| Official TFF Fantasy API | Previous project audit measured 573 GW11 history rows and official fixtures | Existing authenticated integration; historical pre-deadline source timestamps incomplete | Useful for player minutes, starts, points and live status; no reliable populated player xG/xA |
| Football-Data Turkey CSV | 99/99 current-season matches mapped here | [Fair-use limits](https://football-data.co.uk/contact.php) apply | Team xG, goals, shots and SOT only |
| Yuvron / API-Football and other advertised free tiers | No authenticated current-season endpoint response measured in this phase | Key, quota and reuse rights not verified | No player/lineup/injury/xG fields integrated |

## Recommendation

Keep the team features experimental. The study can show directional sensitivity but cannot establish prospective benefit because CSV publication dates and historical player metadata are missing. Next capture a timestamped, permitted Football-Data observation before each deadline, verify its rights and completeness, and evaluate on multiple genuinely prospective weeks. Seek player-level free data only after legal access, current-season endpoint coverage and ID matching are measured. Do not assign production weights from this retrospective sample.

Focused regression tests check idempotent import, fixture matching and strict target-week date exclusion.
