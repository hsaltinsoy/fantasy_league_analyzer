# Phase 17 PostgreSQL setup (Windows PowerShell)

**Status:** schema and immutable SQLite tracking import are validated, but
application cutover is **blocked** until player, fixture, history, evidence,
report and ingestion paths are migrated and compared. Flask and Phase 16 still
use the original files/SQLite. Do not remove them. Do not run prospective
capture using a PostgreSQL-only assumption.

## Setup and migration

Run from the repository root in PowerShell. Docker Desktop must be running.
`.env` is private and ignored. Copy `.env.example` to `.env` and set unique
`POSTGRES_PASSWORD`, `PGADMIN_DEFAULT_PASSWORD` and matching `DATABASE_URL`.
This checkout already has a locally generated `.env`; do not replace it while
the named volume contains data. Port 5433 is used because 5432 is occupied
by another project. Only this PostgreSQL service runs in Docker; Flask runs
in PyCharm or PowerShell.

```powershell
docker version
docker compose version
docker compose up -d db
docker compose ps
$env:DATABASE_URL = ((Get-Content -LiteralPath .env | Where-Object { $_ -like 'DATABASE_URL=*' }) -replace '^DATABASE_URL=','')
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m storage.migrate_sqlite import-sqlite
.\.venv\Scripts\python.exe -m storage.migrate_sqlite reconcile
.\.venv\Scripts\python.exe -m storage.import_artifacts import
.\.venv\Scripts\python.exe -m storage.import_artifacts reconcile
```

Use `docker compose --profile admin up -d pgadmin` only if you want pgAdmin.
It is optional and uses a separate named volume. The database binds to
`127.0.0.1`, not the network interface.

For an isolated integration database named `fantasy_league_phase17_test`,
set `PHASE17_TEST_DATABASE_URL` to that database, never to the live one:

```powershell
$env:PHASE17_TEST_DATABASE_URL = ($env:DATABASE_URL -replace '/fantasy_league$','/fantasy_league_phase17_test')
.\.venv\Scripts\python.exe -m pytest -q
```

The test database must already exist and have `alembic upgrade head`
applied. The full suite passes without this variable too; PostgreSQL
integration tests are then skipped.

## Current application commands

These still use existing SQLite/JSON storage until the full cutover gate:

```powershell
.\.venv\Scripts\python.exe run.py
.\.venv\Scripts\python.exe -m analysis.prospective_monitor capture
.\.venv\Scripts\python.exe -m analysis.prospective_monitor capture --include-phase15
.\.venv\Scripts\python.exe -m analysis.prospective_monitor evaluate --gameweek 10
.\.venv\Scripts\python.exe -m analysis.prospective_monitor status
```

Use the capture command before the *official* future deadline. The original
GW10 set is already saved and must not be regenerated. Evaluation remains
blocked until official fixtures/results are complete. No scheduled task was
created. See `docs/phase16_prospective_monitor.md` for optional Task Scheduler
setup.

## Inspect, back up and stop

```powershell
$dbUser = ((Get-Content .env | Where-Object { $_ -like 'POSTGRES_USER=*' }) -replace '^POSTGRES_USER=','')
$dbName = ((Get-Content .env | Where-Object { $_ -like 'POSTGRES_DB=*' }) -replace '^POSTGRES_DB=','')
docker compose exec -T db psql -U $dbUser -d $dbName -c 'SELECT COUNT(*) FROM predictions;'
docker compose exec -T db pg_dump -U $dbUser -d $dbName -Fc -f /tmp/fantasy_phase17.dump
docker cp fantasy-league-analyzer-db-1:/tmp/fantasy_phase17.dump .\fantasy_phase17.dump
docker compose stop db
```

Store the dump outside Git; `.gitignore` ignores `*.dump`. Verify its hash
and retain the original SQLite copy. A PostgreSQL restore into an existing
database is destructive and requires explicit approval and a fresh backup.
After approval, stop Flask writes and use these commands with a verified dump:

```powershell
docker compose up -d db
docker cp .\fantasy_phase17.dump fantasy-league-analyzer-db-1:/tmp/fantasy_phase17.dump
docker compose exec -T db pg_restore -U $dbUser -d $dbName --clean --if-exists /tmp/fantasy_phase17.dump
.\.venv\Scripts\python.exe -m storage.migrate_sqlite reconcile
```

Do **not** run this restore against a database with newer writes without a
reviewed recovery plan. Never use `docker compose down -v` or remove the
named volume as a rollback step. Before cutover, rollback is simply stopping
this dedicated container; Flask remains on its original storage.

## Reconciliation result, 2026-10-29

| Table | SQLite | PostgreSQL | Missing | Mismatched | Extra |
|---|---:|---:|---:|---:|---:|
| snapshots | 9 | 9 | 0 | 0 | 0 |
| predictions | 19 | 19 | 0 | 0 | 0 |
| evaluation_runs | 0 | 0 | 0 | 0 | 0 |

The original eleven GW10 prediction IDs, source-row hashes, snapshot UUID,
raw payload text, status labels, versions and timestamps match. The
`raw_expected_points` numeric column is rounded only at the declared
`NUMERIC(14,6)` precision; the original raw payload text and its hash are
unchanged. No extra prediction was generated. The dedicated container was
restarted and reconciliation passed again. Additionally, 657 historical
JSON/CSV/XLSX file versions were staged and byte-for-byte verified in
`source_artifacts`. The files are not yet normalized into football tables.
This is **tracking and artifact preservation**, not a full migration
validation.
