# Phase 17 storage audit and gated migration plan

Audit date: 2026-10-29. The working tree already contains uncommitted Phase 15 and
Phase 16 changes. They were retained. The baseline suite passed: 186 tests.

## Existing storage

The project currently has **one live SQLite database**,
`historical_data/prediction_tracking.sqlite3` (25,092,096 bytes at audit).
Its three append-only tables contain 9 snapshots, 19 predictions and 0
evaluation runs. Eleven predictions reference snapshot
`1e9f5094-9b24-42f6-a0ff-ddf201685aa8`; seven other GW10 predictions
reference separate snapshots. The original GW10 deadline is
2026-10-30 16:00 UTC. Import must preserve *all* records, including the
original eleven. The database has SQLite triggers that prohibit mutation.

`historical_data/` also contains 642 JSON, 14 CSV, 2 Markdown, one XLSX and
one lock file. The following patterns cover the persistent and generated
files discovered. Record counts below refer to files; JSON row counts need
schema-specific parsing before normalized import.

| Path/pattern | Format and count | Class | Main consumers/writers | Migration | Destination and risk |
|---|---:|---|---|---|---|
| `historical_data/prediction_tracking.sqlite3` | SQLite, 9/19/0 rows | persistent application data | `prediction_tracking`, `live_benchmark`, `benchmark_evaluation`, `prospective_monitor`, Flask | yes, first | `snapshots`, `predictions`, `evaluation_runs`; exact IDs, timestamp text and payloads required |
| `historical_data/players.json` | JSON, 572 current player rows | current runtime data | Flask `/lineup`, `live_benchmark`, backtests; official ingestion | yes | `players`, `player_state`, `collection_runs`; current values cannot prove historical state |
| `historical_data/player_<id>.json` | JSON, 572 player histories | historical data | historical backtests, Phase 11–15 features | yes | `player_gameweek_stats` plus raw evidence; omitted matches differ from zero points |
| `historical_data/tff_fixtures_verified_v5.json`, `fixtures_reconstructed_gw5_gw9.json` | JSON, 2 files | historical fixture evidence | Flask, dashboard, walk-forward reports | yes | `gameweeks`, `fixtures`, `source_payloads`; reconstructed and official tiers must stay separate |
| `historical_data/recovered/raw/official/*.json` | JSON, 14 files | immutable historical evidence | `recovered_history`, ranking evaluator, recovery collector | yes, retain raw bytes | `source_payloads`, `collection_runs`; retrieval date is not historical deadline proof |
| `historical_data/recovered/snapshots/*.json` | JSON, 27 files | retrospective reconstructions | recovery and Phase 12/13 evaluation | yes, separate classification | `source_payloads`, `player_state`; do not label pre-deadline verified |
| `historical_data/recovered/derived/*.json` | JSON, 4 files | derived historical evidence | recovery and evaluation | yes | `source_payloads`, identity/state tables; lineage must be retained |
| `historical_data/recovered/official_collection_manifest*.json`, `coverage_report.json` | JSON | evidence manifest / generated coverage | recovery collector, dashboard, Phase 15 | manifest yes; coverage as report | `collection_runs`, `historical_reports` |
| `historical_data/recovered/model_*`, `player_ranking_*`, `player_level_phase11/*`, `experimental_phase15/*`, `walkforward_phase10/*`, `v33_audit/*` | JSON/CSV reports | generated export/report | Flask `/benchmark`, research CLIs | store report if dashboard needs it; CSV export may remain | `historical_reports`, `model_evaluations`; preserve evidence tier and sample counts |
| `historical_data/next_week_gw*.json`, `direct_risk_gw10.json`, `production_evaluation.json`, `walkforward_backtest_v*.json/csv` | JSON/CSV outputs | generated runtime/output | dashboard cache, Flask, analysis scripts | migrate any still-read result; stop writing caches after cutover | `predictions`, `historical_reports`; some are derived, not original evidence |
| `historical_data/club_metadata.json`, `club_id_mapping_candidates.json` | JSON | reference mapping/cache | club metadata and fixture validation | mapping yes; transient cache optional | `teams`, `player_identity_mappings`, `source_payloads`; candidate mappings must not become verified |
| `historical_data/player_identity_crosswalk.json` | JSON, **absent** | expected persistent identity data | `data_sources/identity.py` | import only if later found | `player_identity_mappings`; absence must be explicit |
| root `tff_*.json` | JSON, 7 files | source-controlled discovery/reference | fixture/club discovery scripts, tests | not required for runtime cutover; retain files | no automatic import |
| `examples/`, `data_sources/examples/`, `*.example.json` | CSV/JSON templates | test/reference examples | documentation/import examples | no | retain in Git |
| `.env.example`, requirements, docs | text | configuration/docs | developers | no | retain in Git; `.env` ignored |
| `historical_data/*.lock`, recovery backup directories | lock/backup | temporary/backup | capture lock/rollback | no | retain outside Git; do not delete |

Additional external inputs: the official TFF API, xgEdge, API-Football and
optional CSV uploads. Their requests and responses need source IDs, retrieval
times, import status and content hashes before file-based caches can be
removed. Live source availability is not guaranteed. No missing xG, status,
price or historical position can be inferred from current values.

## Architecture and cutover gates

1. Back up the SQLite source and all historical evidence without changing it.
   Current SQLite copy: `.phase17_backup_20261029/prediction_tracking.sqlite3`.
   Its SHA-256 and the live source SHA-256 both equal
   `F01E15224A77A9B65076A17EDD85B75770B3F4E1753CE7FB820E524B52D220C0`.
   Back up the remaining historical files before any destructive operation.
2. Start the dedicated PostgreSQL 17 service on `127.0.0.1:5433` with named
   volume `fantasy-league-analyzer_fantasy_pgdata`. Another project's PostgreSQL
   already binds host port 5432; do not touch it.
3. Apply Alembic schema and import immutable tracking records transactionally.
   Exact source strings and source-row SHA-256 are retained alongside JSONB and
   timezone-aware timestamps. Duplicate identical rows are no-ops; conflicting
   IDs abort the transaction.
4. Reconcile every original SQLite row, FK, and the eleven-record GW10 set.
   **This gate passed for tracking only**: 9/9 snapshots, 19/19 predictions,
   0/0 evaluation runs, zero missing/conflicting/extra records, eleven original
   GW10 predictions on the shared snapshot.
   A separate append-only staging import also copied **657 historical JSON,
   CSV and XLSX files** byte-for-byte into `source_artifacts`, then verified
   all 657 SHA-256 hashes. This is preservation, not normalized runtime access.
5. Normalize player/fixture/history/evidence imports with their original
   provenance. Compare all existing Flask and CLI reads on identical inputs.
   Add isolated PostgreSQL integration tests, restart persistence checks and
   failure behavior. These gates are **not yet passed**.
6. Only after every gate passes, switch Flask, forecasting, ingestion and
   Phase 16 commands to PostgreSQL. A partial switch is prohibited.

## Rollback

Before cutover, leave the application on SQLite; rollback is simply stopping
the dedicated project container with `docker compose stop db`. Never use
`docker compose down -v` or delete the named volume. The original SQLite file
and backup remain the reference. After a future cutover, stop app writes,
restore the last PostgreSQL dump if needed, and change the backend only under
a tested deployment procedure. Do not replay post-cutover records into SQLite
without a separately validated reverse migration.
