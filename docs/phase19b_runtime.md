# Phase 19B PostgreSQL runtime status

PostgreSQL is available through the explicit `STORAGE_BACKEND=postgres` switch.
The application-wide default remains SQLite while the remaining paths below
are verified. The original SQLite database and historical archives are retained.

## Start on Windows PowerShell

Run from the repository root:

```powershell
docker compose up -d db
docker compose ps
$env:DATABASE_URL = ((Get-Content -LiteralPath .env | Where-Object { $_ -like 'DATABASE_URL=*' }) -replace '^DATABASE_URL=','')
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m storage.migrate_sqlite reconcile
.\.venv\Scripts\python.exe -m storage.ingest_current
$env:STORAGE_BACKEND = 'postgres'
.\.venv\Scripts\python.exe run.py
```

Current player and fixture ingestion should be refreshed before a prospective
lineup. The PostgreSQL lineup and forecasting paths reject current source
evidence older than one hour. A past-week forecast cannot use today's player
pool as deadline-time evidence.

The command-line forecast uses the same backend switch:

```powershell
.\.venv\Scripts\python.exe -m analysis.predict_next_week --week 11
```

To run the full PostgreSQL integration suite, configure fresh dedicated test
databases named `fantasy_league_phase17_test` and
`fantasy_league_phase18_test2`, apply `alembic upgrade head` to both, then:

```powershell
$base = $env:DATABASE_URL
$env:PHASE17_TEST_DATABASE_URL = $base -replace '/[^/]+$','/fantasy_league_phase17_test'
$env:PHASE18_TEST_DATABASE_URL = $base -replace '/[^/]+$','/fantasy_league_phase18_test2'
.\.venv\Scripts\python.exe -m pytest -q -rs
```

The Phase 17 test requires a fresh database because it reconciles exact
tracking counts before Phase 19A's synthetic rows are inserted. The Phase 18
test also requires a fresh database for exact normalization counts.

## Remaining cutover gates

- PostgreSQL team-of-week evidence is not yet available for nonzero lineup
  weighting; the route rejects that option explicitly.
- Phase 15 experimental prospective training still reads local historical
  analysis files. `capture --include-phase15` needs a PostgreSQL-backed training
  path and parity test.
- Optional CSV uploads and exports remain file-based by design. The remaining
  normal `/tools` flows need a complete route-by-route PostgreSQL verification.
- Historical forecast player-state snapshots with proved evidence times are
  incomplete. Past-week requests are rejected rather than using current state.
- End-to-end risk-frontier and dashboard parity, and Flask route behavior after
  a fresh process start, need dedicated frozen-input integration tests.

Do not change the default backend until these gates pass.
