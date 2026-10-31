# Football-Data 2026/27 local CSV

The importer reads a locally downloaded `T1.csv`; it never downloads or rewrites it. PostgreSQL migration `006_football_data_matches` creates separate source, team mapping, and match tables. `football_data_imports.raw_bytes` retains the exact file bytes, filename, SHA-256 and import time. Each match retains the original row and row hash. Official TFF fixtures and results remain separate.

The 18 provider names in `storage/football_data_repository.py` are explicitly mapped to TFF IDs after checking the team list and fixture pairs. New names remain unresolved. A changed mapping that conflicts with a stored verified mapping aborts the transaction.

```powershell
docker compose up -d db
.\.venv\Scripts\python.exe -m alembic upgrade head
.\.venv\Scripts\python.exe -m storage.ingest_football_data --file 'C:\Users\Said\Downloads\T1.csv' --season 2026-27
.\.venv\Scripts\python.exe -m analysis.compare_football_data
```

For a later CSV update, download the new file yourself, retain the old original, and run the same import command with the new path. The source hash makes exact repeat imports idempotent. New file versions are preserved as separate evidence. Forecast features use only completed matches before the prediction cutoff and imports that existed by that cutoff.

The comparison uses the same PostgreSQL player pool, histories and fixtures for both runs. Team feature weight is explicitly `0.0`: 81 matches without validated chronological fantasy outcomes do not establish a reliable coefficient for changing player expected points. The feature pipeline reports form, scoring, clean sheets, shot rates, opponent strengths and fixture difficulty. It does not claim improved fantasy results. Comparison reports are persisted in PostgreSQL as generated reports. For a specific cutoff, pass `--cutoff '2026-10-31T16:00:00+00:00'`; the cutoff must precede the selected official gameweek deadline. Missing optional match statistics stay missing.

The xG pipeline adds xG for/against, xG difference, recent three/five-match xG, home/away xG, opponent defensive xG, and an expected clean-sheet indicator. The candidate configuration uses only one xG rate per concept; derived xG difference and rolling windows are diagnostics, not additional weighted copies. The available player-state records are current API states or retrospective reconstructions, and no complete pre-deadline player pools exist for the earlier gameweeks. Historical fantasy points alone therefore cannot validate a retrospective lineup comparison or fit leakage-free xG coefficients. The report is an unpromoted prospective feature snapshot for GW11, not evidence of predictive improvement. Player-history archives lack original retrieval timestamps; comparison requires proof they were staged before the prospective cutoff and labels that provenance limitation explicitly. It also rejects current player or fixture evidence retrieved after the cutoff.
