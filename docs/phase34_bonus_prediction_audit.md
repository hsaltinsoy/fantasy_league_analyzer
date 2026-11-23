# Phase 34 — bonus prediction audit

## Verified source and scoring semantics

The [official TFF rules](https://tfffantezilig.com/yardim?tab=kurallar-1) award 3, 2 and 1 bonus points to the three highest-scoring players in a match (ties may share a tier). The official history has `points`, `bonus`, and event `breakdown` fields. Of 6199 GW1–11 player-week rows, 6199 have points and 6199 have bonus; 439 have positive bonus. 3104 rows contain event breakdowns and 0 disagree with `points` when subtotalled. Thus official `points` includes bonus. Base fantasy points are computed as `points - bonus` only where both fields exist. No bonus is added to official actual totals twice.

The production `project()` function forecasts from historical `points` and therefore already incorporates realized historical bonus implicitly. It does not have a separate expected-bonus feature. The experimental forecast removes bonus from each pre-target history row, runs the unchanged projection on base points, and adds a five-week mean of past bonus scaled by past minutes. It never reads target-week bonus before prediction. No production weights were changed.

## GW11 bonus accounting

| Squad | XI bonus | Captain extra bonus | Total bonus in project score |
| --- | ---: | ---: | ---: |
| human | 14 | 3 | 17 |
| baseline_5w | 10 | 2 | 12 |
| short_form_3w | 8 | 0 | 8 |
| stable_8w | 10 | 2 | 12 |
| uniform_xg | 8 | 0 | 8 |
| position_aware_xg | 8 | 0 | 8 |
| rest_days_control | 8 | 0 | 8 |

Murillo’s reported automatic substitution adds 0 bonus point(s) within his five official points. The project model evaluator omits substitutions; the human 105-point score includes Murillo. Player-level points, base and bonus are in the JSON artifact.

Highest actual scorers absent from every model XI (bonus shown separately): Mason Will John Greenwood 16 total / 3 bonus, Wagner Fabricio Cardoso de Pina 15 total / 3 bonus, Leandro Trossard 15 total / 3 bonus, Oğuz Aydın 13 total / 2 bonus, İrfan Can Kahveci 13 total / 2 bonus, Ali Sowe 13 total / 3 bonus, Dusan Vlahovic 12 total / 2 bonus, Haris Hajradinovic 11 total / 3 bonus.

## Multiweek player accuracy

| GW | Model | N | Baseline MAE / RMSE | Experimental MAE / RMSE |
| ---: | --- | ---: | ---: | ---: |
| 6 | baseline_5w | 572 | 1.343 / 2.606 | 1.352 / 2.605 |
| 6 | short_form_3w | 572 | 1.322 / 2.581 | 1.336 / 2.577 |
| 6 | stable_8w | 572 | 1.354 / 2.618 | 1.359 / 2.617 |
| 7 | baseline_5w | 572 | 1.254 / 2.348 | 1.260 / 2.355 |
| 7 | short_form_3w | 572 | 1.236 / 2.283 | 1.248 / 2.295 |
| 7 | stable_8w | 572 | 1.295 / 2.417 | 1.293 / 2.411 |
| 8 | baseline_5w | 572 | 1.055 / 2.059 | 1.056 / 2.055 |
| 8 | short_form_3w | 572 | 1.070 / 2.072 | 1.067 / 2.060 |
| 8 | stable_8w | 572 | 1.099 / 2.116 | 1.089 / 2.096 |
| 9 | baseline_5w | 572 | 1.227 / 2.395 | 1.241 / 2.410 |
| 9 | short_form_3w | 572 | 1.202 / 2.355 | 1.219 / 2.371 |
| 9 | stable_8w | 572 | 1.236 / 2.391 | 1.246 / 2.396 |
| 10 | baseline_5w | 572 | 1.406 / 2.618 | 1.424 / 2.639 |
| 10 | short_form_3w | 572 | 1.416 / 2.625 | 1.437 / 2.643 |
| 10 | stable_8w | 572 | 1.402 / 2.603 | 1.420 / 2.621 |
| 11 | baseline_5w | 572 | 1.217 / 2.277 | 1.226 / 2.283 |
| 11 | short_form_3w | 572 | 1.195 / 2.249 | 1.207 / 2.256 |
| 11 | stable_8w | 572 | 1.242 / 2.304 | 1.245 / 2.298 |

## Baseline 5W squad sensitivity

| GW | Baseline XI actual | Bonus-aware XI actual | Baseline captain | Bonus-aware captain | XI overlap |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 6 | 67.0 | 68.0 | 75 | 75 | 10/11 |
| 7 | 41.0 | 41.0 | 12 | 12 | 11/11 |
| 8 | 85.0 | 85.0 | 12 | 12 | 8/11 |
| 9 | 45.0 | 57.0 | 12 | 12 | 9/11 |
| 10 | 43.0 | 33.0 | 12 | 12 | 10/11 |
| 11 | 70.0 | 70.0 | 148 | 148 | 11/11 |

These are exploratory retrospective squads using the same candidates per week. Their player club and price metadata are not independently verified at each historical deadline, and fixture/availability inputs are absent. The squad scores should not be read as prospective performance. GW11 model lineups in Phase 32 are separate saved retrospective results.

## Free-data next steps

1. Capture timestamped official player histories and finalized bonus breakdowns weekly. This permits leak-free rolling validation.
2. Capture pre-deadline starting-XI and injury notices from official club or league channels with publication timestamps; bonus opportunities depend on playing time.
3. Capture free match-level shots, chances, saves and team scoring events where rights and coverage permit. Verify entity matching and point-in-time availability before testing player bonus signals.
4. Evaluate bonus calibration over more weeks and compare the same player cohort before considering any production integration. No paid API or GW11-specific tuning is recommended.

## Limits

Official histories were fetched after GW11 and may have later corrections. The experiment uses lagged rows only, but their actual pre-deadline publication is unverified. Price, club and availability histories are incomplete; historical squad scores are approximate. No target-week bonus entered any target-week forecast, and no frozen prediction was overwritten.
