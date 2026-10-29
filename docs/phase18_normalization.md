# Phase 18: PostgreSQL historical normalization

Status: normalized staging data is queryable; Flask and forecasting still use
their original SQLite/JSON/CSV backend. No runtime cutover, predictions,
optimizer formulas or model weights were changed.

## Source assessment

- `source_artifacts` contains 657 byte-preserved JSON/CSV/XLSX files. Twenty-one
  content hashes occur at more than one path. Path plus hash identifies source
  evidence; hash alone does not identify the originating player file.
- The official recovery manifest selects the TFF club, current player and
  fixture responses and records their URLs, retrieval times and hashes.
  Current roster fields are **current state**, not historical GW1–GW9 state.
- `player_<id>.json` supplies 5,046 explicit GW1–GW9 result rows for 572 TFF
  IDs. Its original retrieval timestamps are unavailable. Every row maps to
  exactly one official fixture by gameweek ID, opponent and home/away.
  There are 2,512 explicit zero-minute rows; omitted rows remain missing.
- The official fixture response contains 34 gameweeks, 306 distinct fixtures
  and 81 finished matches. A second local fixture archive provides 306
  source-specific observations; the two sources show no differing fixture
  fields in this import.
- Derived position evidence contains 395 lower-confidence preseason workbook
  observations and 99 official historical Dream Team observations. Both are
  retrospective for GW1–GW9. The third-party workbook is not treated as a
  stable identity provider. Generated model/ranking reports and duplicate raw
  responses remain in `source_artifacts`; they are not football measurements.
- The persistent xgEdge crosswalk file was absent. No name-only external
  identity matches were promoted to verified mappings.

## Normalized PostgreSQL counts

| Table | Rows | Meaning |
|---|---:|---|
| `teams` | 18 | Official TFF stable club IDs |
| `players` | 572 | Official TFF stable player IDs |
| `gameweeks` | 34 | Official IDs and deadline evidence |
| `fixtures` | 306 | Official fixture IDs and relationships |
| `match_results` | 81 | Finished official fixture scores |
| `player_gameweek_stats` | 5,046 | Fixture-linked observed player weeks |
| `stat_observations` | 5,046 | Source-specific rows with source-row SHA-256 |
| `fixture_observations` | 612 | 306 official plus 306 local archive |
| `player_state` | 6,112 | 572 current, 5,046 postmatch, 494 position evidence |
| `player_identity_mappings` | 572 | Verified TFF ID-to-TFF ID only |
| `identity_reviews` | 572 | xgEdge links without a verified provider ID |
| `source_payloads` / `collection_runs` | 579 / 579 | Path-scoped source evidence and import provenance |
| `source_artifacts` | 657 | Immutable original bytes |

The import reported **0 normalization conflicts, 0 unresolved fixture/club
links and 0 duplicate player-week-fixture rows**. Re-running it inserted zero
rows and reported zero conflicts. Reconciliation checked hashes for every
player-history row, current player, club and both fixture observation sets:
5,046 + 572 + 18 + 612 exact matches; no missing or extra rows.

## Missingness and identity review

- Postmatch prices are present in 3,352 of 5,046 history rows. These are not
  verified deadline prices. Verified GW1–GW9 deadline prices and availability
  observations: **0**. Current roster price, position and availability exist
  for all 572 players but are not substituted for historical deadlines.
- Prior-position evidence for GW1 covers 395 of 572 roster players; for GW9
  it covers 412 of 572. These are retrospective evidence counts, not
  independently verified pre-deadline coverage. The read-only repository
  excludes these observations when a deadline-time evidence cutoff is used.
- Historical xG/xA placeholder zeroes were not imported as measurements.
  Raw source artifacts retain them unchanged; normalized xG/xA measurement
  count is **0**.
- All 572 TFF IDs have an exact verified TFF self-identity mapping. There are
  **0** verified xgEdge crosswalk links in staged evidence. The 572 open
  `identity_reviews` rows explicitly record the missing provider IDs; they
  are not failed name matches and must not trigger automatic merges.
- Historical source retrieval times are unknown for the per-player local
  history files. `source_payloads.retrieved_at` is NULL for those files;
  `collection_runs.retrieved_at` records only the later local artifact import
  time, with `retrieval_time_from_source=false`.

## Query rules

`HistoricalRepository` exposes players, fixtures, statistics, previous-N-week
form, historical position/club evidence, exact provider ID resolution and
source provenance. `before_week` is a strict `< target_week` filter. An
`as_of` cutoff also requires documented source retrieval by that time;
retrospective player states require explicit deadline proof and are excluded.
Calling without `as_of` requests a retrospective research view, not a
point-in-time forecast input.

## PowerShell commands

Run from the project root with Docker Desktop running. The private `.env`
from Phase 17 must point at the project's PostgreSQL container on localhost
port 5433. Do not print or commit its password.

```powershell
docker compose up -d db
$env:DATABASE_URL = ((Get-Content -LiteralPath .env | Where-Object { $_ -like 'DATABASE_URL=*' }) -replace '^DATABASE_URL=','')
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m storage.normalize_history import
.\.venv\Scripts\python.exe -m storage.history_quality reconcile
.\.venv\Scripts\python.exe -m storage.history_quality report
.\.venv\Scripts\python.exe -m storage.migrate_sqlite reconcile
$env:PHASE17_TEST_DATABASE_URL = ($env:DATABASE_URL -replace '/fantasy_league$','/fantasy_league_phase17_test')
$env:PHASE18_TEST_DATABASE_URL = ($env:DATABASE_URL -replace '/fantasy_league$','/fantasy_league_phase18_test2')
.\.venv\Scripts\python.exe -m pytest -q
```

The isolated test databases must exist and have `alembic upgrade head`
applied. Keep both test URLs distinct from the live staging URL.

## Phase 19 blockers

The normalized dataset is suitable for read-only research queries. It is not
yet sufficient for a complete runtime cutover: ingestion still writes files,
Flask and Phase 16 still read SQLite/JSON/CSV, historical deadline eligibility
is incomplete, and external xgEdge provider IDs are not persistently linked.
Phase 19 must compare identical runtime inputs and outputs, implement
PostgreSQL writes with deadline/immutability safeguards, and verify the
original GW10 prediction set again before switching any route or CLI.
