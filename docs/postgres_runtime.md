# PostgreSQL runtime operations (Windows PowerShell)

Run these commands from the repository root with Docker Desktop started. Use
the `.venv` interpreter configured in PyCharm. `DATABASE_URL` must point to
the database named by `POSTGRES_DB` in `.env`.

PyCharm can run `run.py` directly with the project `.venv`; the database
connection reads `DATABASE_URL` from the project `.env` when the process
environment does not provide it. An explicitly set process value wins.

## Start and reconcile

```powershell
docker compose up -d db
docker compose ps
$env:DATABASE_URL = ((Get-Content .env | Where-Object { $_ -like 'DATABASE_URL=*' }) -replace '^DATABASE_URL=','')
$env:STORAGE_BACKEND = 'postgres'
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m storage.migrate_sqlite import-sqlite
.\.venv\Scripts\python.exe -m storage.migrate_sqlite reconcile
.\.venv\Scripts\python.exe -m storage.ingest_current
.\.venv\Scripts\python.exe -m storage.import_runtime_metadata
.\.venv\Scripts\python.exe run.py
```

The import is append-only and idempotent. It rejects an existing ID whose
content differs. Historical forecasts remain blocked when dated player-state
evidence is unavailable. The optional TFF browser login profile is local
configuration; if it has expired, run
`.\.venv\Scripts\python.exe -m data_sources.tff_official login` interactively.

## Back up both stores

```powershell
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'
$backup = Join-Path (Get-Location) ("backups/phase19-$stamp")
New-Item -ItemType Directory -Path $backup -Force | Out-Null
Copy-Item -LiteralPath 'historical_data/prediction_tracking.sqlite3' -Destination (Join-Path $backup 'prediction_tracking.sqlite3')
$dbUser = ((Get-Content .env | Where-Object { $_ -like 'POSTGRES_USER=*' }) -replace '^POSTGRES_USER=','')
$dbName = ((Get-Content .env | Where-Object { $_ -like 'POSTGRES_DB=*' }) -replace '^POSTGRES_DB=','')
docker compose exec -T db pg_dump -U $dbUser -d $dbName -Fc -f /tmp/fantasy_runtime.dump
docker cp fantasy-league-analyzer-db-1:/tmp/fantasy_runtime.dump (Join-Path $backup 'postgres.dump')
Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $backup 'prediction_tracking.sqlite3'),(Join-Path $backup 'postgres.dump')
```

Test a restore only into a new, named database. Never restore over the live
database while Flask is running. The final archive was restored into
`fantasy_league_phase19_complete_restore`; its 11 snapshots, 21 predictions,
572 players, 306 fixtures, 11 model definitions, and 24 reports matched live.

## Explicit rollback

Stop the Flask process, then:

```powershell
$env:STORAGE_BACKEND = 'sqlite'
.\.venv\Scripts\python.exe run.py
```

This selects the preserved SQLite and file workflow. It does not transfer
PostgreSQL-only records to SQLite. Before using newer records after rollback,
export and reconcile them deliberately.

## Full integration tests

Use only dedicated test databases. `PHASE17_TEST_DATABASE_URL`,
`PHASE18_TEST_DATABASE_URL`, and `PHASE19_CAPTURE_TEST_DATABASE_URL` must end
in `fantasy_league_phase17_test`, `fantasy_league_phase18_test2`, and
`fantasy_league_phase19_capture_test`, respectively. Migrate the first two
with Alembic; restore a verified live archive into the third before running
the suite. The tests never target the live database for writes.

```powershell
$base = ((Get-Content .env | Where-Object { $_ -like 'DATABASE_URL=*' }) -replace '^DATABASE_URL=','')
$env:PHASE17_TEST_DATABASE_URL = $base -replace '/[^/]+$','/fantasy_league_phase17_test'
$env:PHASE18_TEST_DATABASE_URL = $base -replace '/[^/]+$','/fantasy_league_phase18_test2'
$env:PHASE19_CAPTURE_TEST_DATABASE_URL = $base -replace '/[^/]+$','/fantasy_league_phase19_capture_test'
.\.venv\Scripts\python.exe -m pytest -q -rs
```

The test databases need a clean state for each full run. The Phase 17 suite
copies the SQLite source into a temporary path before importing it. Never
point a test URL at `POSTGRES_DB`.

## Final migration verification (2026-10-30)

- PostgreSQL is the code default. `STORAGE_BACKEND=sqlite` is the explicit
  rollback setting.
- SQLite and PostgreSQL reconcile at 11 snapshots and 21 predictions, with
  zero missing, mismatched or extra rows. The original shared GW10 snapshot
  still contains its original 11 predictions with identical IDs and hashes.
- The two later GW10 snapshots were imported append-only. Their predictions
  retain `deadline_unknown` status; neither has a recorded deadline, so they
  are not treated as independently verified pre-deadline forecasts.
- Frozen GW11 production, team-of-week, Phase 15 training, and GW10 risk
  frontier comparisons matched the legacy outputs. The final low-floor
  frontier point was feasible in both solvers rather than proven optimal.
- A synthetic GW11 production and Phase 15 capture ran in the isolated
  restored database and was idempotent. It did not read historical files or
  alter the original SQLite database.
- The PostgreSQL container was restarted. Live 11/21 and isolated 10/26
  tracking counts survived. The final PostgreSQL backup restored into a new
  database with 11 snapshots, 21 predictions, 572 players and 306 fixtures.
- The final full suite after the default switch and metadata import passed:
  228 passed, 0 failed, 0 skipped. An application process without
  `STORAGE_BACKEND` set served `/`,
  `/lineup`, `/benchmark`, and `/tools` from PostgreSQL with HTTP 200.

Live data contains 572 players, 18 teams, 306 fixtures, 5,046 player-week
statistic rows, 1,144 current-state observations and 1,530 fixture
observations. It also contains 11 model definitions and 24 reports. The
current player pool must be refreshed from the authenticated
TFF API before it becomes stale. Historical requests that lack reliable
deadline-time player state remain blocked.
