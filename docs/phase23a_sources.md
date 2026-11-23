# Phase 23A source audit and integration plan

## Existing paths

- `data_sources/tff_official.py` ingests official fantasy players and prices. Runtime repositories retain player, fixture, and historical point records. `analysis/availability.py` handles official status and dated manual overrides.
- `data_sources/football_data.py` parses manually supplied Football-Data.co.uk CSVs; `storage/ingest_football_data.py` stores match rows with source provenance. `analysis/football_data_team_features.py` supplies team goals, shots, xG, venue and form. `analysis/football_data_live.py` supports opt-in uniform and position-aware xG adjustments.
- `analysis/predict_next_week.py` builds the eligible player pool, using `analysis/production_scoring.py` and historical form models. `analysis/optimizer.py` selects the squad. `analysis/historical_walkforward.py` and related backtests evaluate historical forecasts.
- Missing reliable player-level fields include shots, shots on target, xG, xA, confirmed starts, exact expected minutes, and verified suspension events. Team xG must not be labeled player xG.

## Provider decision

| Provider | Coverage and useful fields | Access and reliability decision |
| --- | --- | --- |
| TFF official match reports | Süper Lig match details, lineups and substitutions visible on match pages; player xG/xA not established | No documented public API or automated access permission verified. Manual, sourced imports only until permission and schema are confirmed. |
| FotMob | Süper Lig pages may show lineups and player statistics; historical depth and availability vary | No authorized free API or automation terms verified. Do not integrate unofficial endpoints. |
| SofaScore | Match pages and player statistics, including some advanced metrics | Terms prohibit scraping/aggregation without consent. Do not integrate without permission. |
| Football-Data.co.uk | Historical Turkish match CSVs with results and selected team match statistics; no player data | Already integrated. Free-file policy is for personal/academic use and light download, at most twice weekly. Avoid additional automated polling. |
| football-data.org | Documented API, but Turkish Süper Lig is absent from the published free tier; free tier offers 10 calls/minute | Not useful for this competition without a covered plan. |

Availability, precise xG/xA coverage, update frequency and retention are **unverified** for TFF reports and FotMob. No assumptions about those fields are used in predictions.

## Integration plan

1. Keep official TFF fantasy data authoritative. Retain third-party source IDs, original values, timestamps, confidence and optional reviewed canonical IDs in separate evidence records. Never infer identity from a name alone.
2. Reuse the existing Football-Data match repository. This phase adds last match date and rest features to its opt-in feature path. The rest coefficient defaults to zero; a nonzero value is a hypothesis and must pass walk-forward validation before activation.
3. Seek authorized player-level data with stable provider IDs and point-in-time historical access. Import only after confirming rights and mapping player, team and match IDs through reviewed crosswalks.
4. Compare baseline_5w, short_form_3w, stable_8w, uniform xG, position-aware xG and any new model on identical cutoff snapshots and eligible pools. Report MAE, RMSE, rank correlation, optimized XI actual points and captain outcomes only where official actuals are final. Tune on earlier weeks only.

No new source was fetched or prediction accuracy claim made in this phase. The dashboard reports unavailable freshness and player coverage rather than inventing values.
