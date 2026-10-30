# Phase 19A runtime repository (partial integration)

Run these commands from the repository root in PowerShell. The original SQLite
database and historical files remain in place. `STORAGE_BACKEND=postgres` routes
tracking through PostgreSQL; other application data paths still require work.

```powershell
docker compose up -d db
docker compose ps
$env:DATABASE_URL = ((Get-Content -LiteralPath .env | Where-Object { $_ -like 'DATABASE_URL=*' }) -replace '^DATABASE_URL=','')
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m storage.migrate_sqlite reconcile
.\.venv\Scripts\python.exe -m storage.ingest_current
$env:STORAGE_BACKEND = 'postgres'
.\.venv\Scripts\python.exe run.py
.\.venv\Scripts\python.exe -m analysis.prospective_monitor status
.\.venv\Scripts\python.exe -m analysis.prospective_monitor capture
.\.venv\Scripts\python.exe -m analysis.prospective_monitor evaluate --gameweek 11
```

The ingestion command uses the local authenticated browser profile and fetches
current players and fixtures. Login first with
`.\.venv\Scripts\python.exe -m data_sources.tff_official login` if the
profile is missing or expired. Each retrieval records raw API evidence and UTC
retrieval time. Repeating an identical feed object is idempotent; a new API
retrieval creates a new current observation.

For explicit SQLite rollback in a new Flask process:

```powershell
$env:STORAGE_BACKEND = 'sqlite'
.\.venv\Scripts\python.exe run.py
```

Write tests require `PHASE17_TEST_DATABASE_URL` ending in
`/fantasy_league_phase17_test`; Phase 18 tests require
`PHASE18_TEST_DATABASE_URL` ending in `/fantasy_league_phase18_test2`.
Do not point either variable at the live database. Set both for a full suite
without PostgreSQL skips. Phase 17 tests require a fresh test database because
they assert that its tracking tables contain exactly the imported SQLite rows;
the Phase 19A tests add synthetic tracking rows later in the suite.
