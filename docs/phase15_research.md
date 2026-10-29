# Phase 15: TFF forecasting research and first experiment

Research reviewed 2026-10-29. Reference source revisions: OpenFPL `ad055ba`; fpl-bot `056699e`. The local TFF production optimizer, forecast weights, and live tracking database were not changed.

## Repository comparison

| Topic | OpenFPL implementation / paper | fpl-bot implementation | TFF decision |
|---|---|---|---|
| Feature engineering | `play.ipynb` consumes prebuilt sample features; paper §2.3 describes 1/3/5/10/38-match player, team and opponent windows, status and position-specific sets. The released notebook does not provide the full training-data construction code. | `fpl_bot/core/features.py`: `_player_round_features` uses grouped `shift(1)`, `_team_round_features` aggregates team outcomes, `build_features` joins them. | Rebuild only validated prior player-week points/minutes/goals/assists; defer team/opponent until dated club evidence is reliable. |
| Model | `play.ipynb` loads saved position models/scalers and takes the median across them. Paper §2.4 describes RF/XGBoost candidate search, five team folds, 50-model position ensembles. | `fpl_bot/core/model.py:PointsModel` fits `HistGradientBoostingRegressor` on played rows; `core/features.py:_heuristic_xp` is a baseline feature. | Start with shared ridge regression and prior-position indicators; no tree model on the limited TFF weeks. |
| Validation | Paper §2.2–2.5: four development seasons, team-grouped CV and prospective 2024–25 predictions before deadlines. | `core/backtest.py` and `core/model.py:prediction_metrics` provide historical evaluation; `core/features.py` shifts lag features. | Chronological TFF week splits; train only on earlier outcomes, with a one-week training gap. Historical position evidence remains retrospective. |
| Horizon | Paper evaluates 1/2/3 gameweeks; `play.ipynb` predicts provided samples using saved ensembles. | `services/fixture_service.py:get_team_fixtures_for_horizon` computes 1/3/5/8-week fixture views; `core/squad_solver.py:solve_squad` solves a single squad decision, not a verified joint multi-period transfer MIP. | The first experiment is one week. Design 3/5-week planning only after point-in-time inputs and rules are validated. |
| Transfers and bench | Outside OpenFPL's forecast scope. | `core/squad_solver.py:solve_squad` includes FPL free-transfer and hit costs; `agents/optimization_agent.py:optimize` compares hold and transfer plans, and `evaluate_squad_and_bench_sequence` tests six outfield bench orders with appearance probabilities. | TFF rules allow unlimited transfers; FPL hit/free-transfer costs must not be copied. Bench ordering needs TFF substitution rules and defensible appearance probabilities. |
| Adaptive residuals | No residual updater in released inference notebook. | `core/database.py` has residual/checkpoint schema comments, while `core/models.py` explicitly says no residual adjustment is applied to current xPts. | Treat residual learning as an unimplemented research idea, not an existing proven method. |

OpenFPL contains an MIT `LICENSE` and depends on pandas, joblib, XGBoost, and scikit-learn in `plug.txt`. fpl-bot depends on pandas, NumPy, scikit-learn and PuLP in `pyproject.toml`; no license declaration or license file was found in the reviewed revision. No code or model artifact was copied from either project. The OpenFPL paper is CC BY 4.0. Do not load third-party serialized model files without a separate trust review.

## TFF data feasibility and compatibility

The local official player-result archive has 572 player files and 5,046 GW1–GW9 rows. Points, minutes, goals and assists are populated and can be lagged by stable TFF player ID. `xG` and `xA` fields are zero in all 5,046 rows; zero here is not reliable evidence of genuinely observed zero chance creation, so they are excluded. `cost` is zero in 1,694 rows, and historical price should not be imputed from current price. Fixture result rows identify opponents and venues, but future result scores must never enter forecasts. Clubs and transfers inferred from postmatch records are not proven deadline-time club snapshots. Historical availability and suspension statuses are missing. Official position evidence is recovered from earlier dream-team records, with severe selection bias; the combined tier adds a lower-confidence preseason workbook. Neither tier is independently verified before historical deadlines. The existing identity crosswalk is useful for present-day provider reconciliation but does not establish dated historical xG/xA.

| Idea | TFF fit | Reason |
|---|---|---|
| Prior-week rolling points/minutes, simple shrinkage | Implement now | Official result rows have explicit week IDs and nonappearances. |
| Position-aware model using prior evidence | Experimental only | Earlier dream-team position evidence is retrospective and selected. |
| Goals/assists rolling features | Experimental only | Official rows contain these statistics; usefulness needs holdout testing. |
| Team/opponent form and home/away | Later | Validate point-in-time club and fixture identity, transfers and postponed/double fixtures first. |
| Historical xG/xA, status and price features | Not currently evaluable | No trustworthy nonzero xG/xA history; deadline statuses/prices incomplete. |
| RF/XGBoost ensemble | Defer | Only nine historical weeks, small official sample, and no genuine prospective holdout. |
| FPL transfer penalties/free transfers | Incompatible | Official TFF rules say transfers are unlimited within squad constraints. |
| Read-only 3/5-week TFF planner | Design only | Needs current owned squad, forward fixtures, price/status snapshots, and calibrated horizon forecasts. |

The official [TFF Fantasy rules](https://tfffantezilig.com/yardim?tab=kurallar-1) specify 15 players (2 GK, 5 DEF, 5 MID, 3 FWD), a 100M budget, three players maximum per club, a legal XI with at least 1 GK/3 DEF/1 FWD, captain double points, automatic substitutions, and unlimited transfers. They do not state a transfer hit penalty. A future read-only planner should take a dated current squad and budget, enumerate legal 3/5-week options, account for captain and bench order, and display projected points plus uncertainty without submitting transfers. Manager cards require separate rule modeling and are excluded initially.

## First experiment and limits

`analysis/experimental_forecasting.py` adds a chronological 3/5/8-week and season-to-date feature builder. It uses a fixed ridge penalty and train-only feature imputation/scaling. Four historical fantasy positions are encoded as prior-evidence indicators; a fixed 50/50 blend with short_form_3w is compared separately. The target is unconditional next-week player points, so no second appearance multiplier is applied. A cold start with fewer than three prior rows is marked unavailable. No current club, price, availability, fixture outcome, xG or xA enters the feature vector. Training labels end at least one full gameweek before each evaluation target. The reports use the existing Phase 13 matched samples and write only under ignored `historical_data/experimental_phase15/`.

Priority next steps: (1) collect genuine forward deadline snapshots for several weeks and freeze model versions; (2) validate dated club/fixture participation and availability; (3) compare simple ensembles and position-specific training only if larger multi-season samples exist; (4) build a read-only TFF planner from verified current-squad and transfer data. Risk: a model that lowers player MAE can still select worse top players or full XIs, and any retrospective sample here is selected and uncertain.

### Observed retrospective result

All values below use identical within-week player samples. The official-only GW9 comparison has 60 players and 162 earlier training observations; the lower-confidence combined GW7/GW8/GW9 comparisons have 407/410/409 test players, with 806/1,212/1,619 earlier training observations. GW6 is not evaluable with the required two earlier training weeks, and official GW7/GW8 fall below the 120-row training minimum. The chosen penalty and blend were fixed before reading these outputs.

| Tier / week | Ridge MAE | Blend MAE | Short-form MAE | Ridge P@20 | Short-form P@20 |
|---|---:|---:|---:|---:|---:|
| Official GW9 | 3.155 | 2.942 | 2.786 | 0.446 | 0.432 |
| Combined GW7 | 1.700 | 1.454 | 1.291 | 0.100 | 0.186 |
| Combined GW8 | 1.556 | 1.364 | 1.242 | 0.288 | 0.313 |
| Combined GW9 | 1.522 | 1.414 | 1.339 | 0.213 | 0.213 |

This experiment does not improve MAE over production short-form on any evaluable week, so it is unsuitable for activation. P@20 and top-11 actual points fluctuate; official GW9 is one small selected sample. Complete MAE/RMSE/bias, Spearman, P@10/P@20, NDCG@20, top-11 actual points, high-return MAE and bootstrap intervals are in the generated local JSON reports. These are not full-XI scores and do not evaluate transfers, captaincy or bench order.
