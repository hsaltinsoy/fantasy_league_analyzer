# Phase 24 capture and evaluation status

The repository already has an append-only `snapshots` / `predictions` / `evaluation_runs` store, a prospective capture workflow (`analysis.prospective_monitor`), and official-result validation (`analysis.benchmark_evaluation`). Phase 24 adds a deterministic `input_sha256` to new snapshot payloads and requires complete candidate identities, prices, fixture rows and past-only histories when a capture requests pre-deadline status. Earlier immutable snapshots are untouched.

The hash covers gameweek, complete players, fixtures, histories, source metadata and deadline evidence. It excludes the local insertion time. The stored payload still includes all raw players and histories; it is not limited to the selected 15. Source observation times belong in the source metadata and are distinct from capture time. `analysis.capture_integrity.classify` rejects future observation times. An official deadline plus a local timestamp is classified as **locally recorded, unverified**; only independently verified captures should enter a primary evaluation.

Existing prospective workflow commands, from the repository root with the configured Python interpreter:

```powershell
.venv\Scripts\python.exe -m analysis.prospective_monitor capture
.venv\Scripts\python.exe -m analysis.prospective_monitor evaluate --gameweek 12
.venv\Scripts\python.exe -m analysis.prospective_monitor status
```

Capture requires a fresh official fixture deadline and current TFF player data, uses a lock to avoid duplicate gameweek captures, and records failures through its workflow. Evaluation requires finalized official fixtures and player results; missing actuals remain missing. No Task Scheduler job was installed or verified in Phase 24. To schedule locally, create separate Windows Task Scheduler tasks for `capture` before expected deadlines and `evaluate` after finalization, set the working directory to this repository, and use the configured interpreter. Review `status` and task history after each run. Do not point database tests at the production database.

The existing benchmark capture runs the production form models on one frozen input. Uniform xG, position-aware xG and rest adjustments are **not yet part of that atomic multi-model capture**, so a six-model comparison and its feature ablations remain unavailable. No earlier gameweek was reconstructed from current data. The dashboard currently shows saved benchmark and prospective reports; a dedicated Phase 24 performance panel awaits complete comparable snapshots.
