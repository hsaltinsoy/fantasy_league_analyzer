# Prospective monitor operations

The monitor reuses the existing SQLite snapshots, predictions, benchmark generator and official evaluator. It does not create a second tracking database. Existing GW10 predictions remain immutable. Each new benchmark capture is selected from the authenticated official TFF fixture API, checks a fresh timezone-aware official deadline, and uses one source snapshot for production and supported experimental lineups. Local process time is **not** independent timestamp proof.

## Windows PowerShell commands

Run these from the repository root, using the project's PyCharm virtual environment. First establish or refresh the local TFF browser session if necessary:

```powershell
& .\.venv\Scripts\python.exe -m data_sources.tff_official login
```

Capture the next official gameweek before its deadline:

```powershell
& .\.venv\Scripts\python.exe -m analysis.prospective_monitor capture
```

To opt in to the Phase 15 ridge and fixed-blend lineups on that same snapshot, use `capture --include-phase15` **on the initial capture**. A repeated capture reports `already_captured` and does not add or replace records. The standard capture includes short_form_3w, the four existing form variants, and experimental covariance only if its historical evidence is sufficient. The Phase 15 models require valid recovered training data, three earlier player weeks and a legal experimental candidate pool; otherwise the command reports `not_available`. The appearance model remains withheld because production xPts already discounts minutes.

After all fixtures have official final scores, evaluate a specific saved week:

```powershell
& .\.venv\Scripts\python.exe -m analysis.prospective_monitor evaluate --gameweek 11
& .\.venv\Scripts\python.exe -m analysis.prospective_monitor status
```

Replace `11` with the gameweek printed by `capture`. If several benchmark snapshots exist for one week, use `evaluate --snapshot-id <ID>` instead. Evaluation returns `not_ready` without saving a run when fixtures are incomplete or inconsistent. Once complete, official player histories are fetched for all selected players, validated against IDs, gameweek and fixture participation, then scored once per snapshot. Identical evidence yields the same immutable evaluation-run ID. Missing results remain incomplete, never zero-filled. The dashboard at `/` and JSON endpoint `/api/prospective/report` show cumulative prospective results. XI ranking is **within the selected eleven only**; no full player-pool ranking is claimed.

At the 2026-10-29 check, the authenticated official API returned GW10, deadline 2026-10-30 16:00 UTC, with nine fixtures. `capture` returned `already_captured` for the original shared GW10 snapshot and created zero predictions. After GW10 finishes, use `evaluate --gameweek 10` for that preserved set. Once the official API moves to a wholly upcoming GW11, run `capture` before its official deadline for the first new prospective set. The cumulative Phase 16 chart intentionally starts with snapshots created by this guarded monitor; the original GW10 set remains on `/benchmark`.

## Optional Windows Task Scheduler setup

No scheduled task is created by this project. If you choose to configure one, set **Program/script** to the absolute path of `.venv\Scripts\python.exe`, **Start in** to the absolute repository directory, and **Add arguments** to `-m analysis.prospective_monitor capture` (optionally `--include-phase15`). Schedule it well before the official deadline and configure Task Scheduler to avoid overlapping instances. A separate task can run `-m analysis.prospective_monitor evaluate --gameweek N` after matches finish; an incomplete week exits safely as `not_ready`. The capture command also uses a local file lock to serialize overlapping Windows launches.

## Provenance limits

The authenticated fixture response supplies the gameweek ID, deadline, kickoff and fixture IDs. The stored source records the fixture URL and retrieval time plus the local player retrieval time. Source and model parameters are kept with immutable records. The system labels a local pre-deadline capture `locally_recorded_pre_deadline_not_verified`; independent verification requires a trustworthy external timestamp receipt that is currently absent. It does not relabel earlier GW10 records. Historical Phase 15 model fitting uses retrospectively recovered position evidence, separately identified in its model parameters, so experimental forecasts must be interpreted with that limitation.
