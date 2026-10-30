# Phase 19C cutover gate

This is the Phase 19C gate record. The final migration subsequently made
PostgreSQL the default; see [PostgreSQL runtime operations](postgres_runtime.md).
No original GW10 prediction was regenerated.

## Verified evidence and parity

- The staged `historical_data/team_of_week_verified.json` artifact has nine
  complete weeks and 99 memberships. The repository parses its exact staged
  bytes. GW11 with team-of-week weight 0.1 matched the file-backed forecast
  and optimizer output exactly.
- Phase 15 GW11 training used 2,438 rows from GW4–9. Fitted coefficients,
  settings, and training metadata were exactly equal between file and database
  evidence. The last allowed label was two weeks before target.
- Frozen GW10 risk-frontier inputs, covariance, maximum-mean solution, and
  seven solver points matched between backends at the configured 12-second
  limit. Five constrained points were optimal; the final lower floor was
  feasible in both runs, so its point is not a proof of the full frontier.
  Expected-point and variance differences were zero in these comparisons.

## Run PostgreSQL mode in PowerShell

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

## Back up PostgreSQL

```powershell
$dbUser = ((Get-Content .env | Where-Object { $_ -like 'POSTGRES_USER=*' }) -replace '^POSTGRES_USER=','')
$dbName = ((Get-Content .env | Where-Object { $_ -like 'POSTGRES_DB=*' }) -replace '^POSTGRES_DB=','')
docker compose exec -T db pg_dump -U $dbUser -d $dbName -Fc -f /tmp/fantasy_phase19c.dump
docker cp fantasy-league-analyzer-db-1:/tmp/fantasy_phase19c.dump .\fantasy_phase19c.dump
Get-FileHash -Algorithm SHA256 -LiteralPath .\fantasy_phase19c.dump
docker compose exec -T db pg_restore -l /tmp/fantasy_phase19c.dump
```

The backup command and archive listing were exercised. The archive was also
restored into the isolated `fantasy_league_phase19c_restore_test` database.
Restored and live counts matched: 9 snapshots, 19 predictions, 572 players,
306 fixtures, 657 source artifacts, and 7,256 player-state rows. The live
database was not restored in place.

## Explicit application rollback

Stop the Flask process, then start a new one with:

```powershell
$env:STORAGE_BACKEND = 'sqlite'
.\.venv\Scripts\python.exe run.py
```

The four main pages returned HTTP 200 in this explicit SQLite mode. This
switch does not copy PostgreSQL-only writes back into SQLite; reconcile and
export newer records before relying on them in rollback mode.

## Remaining gates

- Complete content and persistence parity for every `/tools` workflow,
  including browser-supplied xgEdge and free-fixture inputs.
- Verify Phase 15 `capture --include-phase15` end to end with an isolated
  future snapshot and no file reads.
- Add dated historical player-state snapshots before enabling historical
  forecasts. Current state remains barred from past deadline forecasts.
- Verify generated report updates and optional import/export boundaries.
- Complete the remaining workflow gates before changing the default backend.

## Latest verification

The complete suite ran against freshly migrated isolated Phase 17 and Phase 18
PostgreSQL test databases: 218 passed, 0 failed, 0 skipped. Live SQLite to
PostgreSQL reconciliation passed with 9 matching snapshots, 19 matching
predictions, and all 11 original GW10 predictions unchanged.

## Phase 19D reconciliation blocker

On the subsequent Phase 19D run, the original SQLite source contained 11
snapshots and 21 predictions, while PostgreSQL still contained 9 and 19.
The two additional GW10 snapshot IDs are
`ca0d9799-18d1-43fb-84ff-ae1225f499da` and
`29131e7e-47f2-4bbb-808d-63ac555f1188`, captured on 2026-10-30 at
14:59:39 and 15:00:11 UTC. The original shared GW10 snapshot and its 11
predictions still reconcile exactly. The new records were subsequently backed
up and imported append-only into PostgreSQL with their original IDs,
timestamps, metadata, payload text and row hashes. Both predictions have
`deadline_unknown` status and no recorded deadline; their source labels do
not independently establish pre-deadline capture. The migration did not
regenerate them. Reconciliation now passes at 11 snapshots and 21 predictions,
with zero missing, mismatched or extra rows.

The Phase 17 test now imports from a temporary SQLite copy and compares source
counts dynamically. The subsequent clean isolated run passed: 219 passed,
0 failed, 0 skipped. A targeted transaction rollback test for opt-in Phase 15
capture also passed. Generated-report tests were added afterward and require
a final clean full-suite run.
