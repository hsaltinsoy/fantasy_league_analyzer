# Phase 40D - manual Türkiye manager squad collector

## Use

Start the existing local app as described in [README](../README.md), then open `http://127.0.0.1:5000/manager-collector`. The new page is linked from the app navigation. It makes **no TFF manager API requests**. It uses the existing local TFF player catalogue in `historical_data/players.json` for official ID lookup and validation. If that catalogue is absent, the page reports that imports are unavailable; it does not fetch a replacement automatically.

For one manager-week, generate or reuse a UUIDv4 pseudonym, enter the gameweek, rank at capture, the last gameweek included in that rank, 11 starting player IDs, four bench IDs, captain and vice captain IDs, formation, capture time, observation type, and a provenance note. Enter a verified deadline when claiming a pre-deadline observation. Use **Validate and preview**, inspect the complete record, then **Confirm and save**. The server repeats validation on save. Names, email addresses, profile URLs and raw manager account IDs are rejected as fields. Keep a private pseudonym mapping outside this dataset only if longitudinal tracking is needed.

The collector checks 15 distinct known player IDs, one starting GK, and distinct captain and vice captain in the XI. Standard squads must have 2 GK / 5 DEF / 5 MID / 3 FWD and a standard formation. An Attack Card observation with a different composition or formation requires explicit manual confirmation and is saved as `rules_unverified`, excluded from feature eligibility and historical comparison. It checks timezone-aware capture/deadline times and that the rank basis predates the target week. Current club and price metadata are **not** used to assert historical affordability or club-limit compliance.

Rows are written atomically to the separate ignored `experimental_data/manual_manager_squads.json` file. Configure a test or alternate location with Flask `MANAGER_COLLECTOR_STORE`; no production table, saved prediction or frozen snapshot is touched. The page offers JSON and CSV downloads. The dashboard shows top-10/25/50 selection and captain shares among **observed rows**, plus XI overlap and actual XI-plus-captain points versus the archived Phase 36 baseline for GW6-11 where official history exists. It does not model manager cards or automatic substitutions; the archived baseline is retrospective. With one manager-week, a 100% share means one observation, not population consensus. General-player popularity remains unavailable because no same-cutoff all-manager dataset was imported.

## Screenshot assistance

An optional PNG/JPEG/WebP upload (4 MB maximum) is processed in memory and discarded. If Pillow, pytesseract and a local Tesseract executable are available, the app returns **exact-name player-ID suggestions only**. OCR cannot reliably establish a complete XI, captain badges or fantasy points here, so it does not auto-fill or save them. Missing players and fields must be entered manually. If OCR is unavailable, the page says so and manual entry remains usable. Every record still requires preview and explicit confirmation.

## Timing and permissions

Manual entry does not establish a right to bulk reuse another person's selections. Respect TFF's applicable terms and use the page only for observations you are permitted to record. The [official rules](https://tfffantezilig.com/yardim) specify the country league and squad lock one hour before the first match. A retrospective screenshot remains retrospective even if it shows an earlier week. A row is marked `feature_eligible` only when explicitly labelled pre-deadline, **both the claimed capture time and this local server's receipt time precede the entered deadline**, and its card rules are verified. Manually confirmed alternative Attack Card squads are always `rules_unverified` and feature-ineligible. The server receipt prevents a screenshot imported after the match from becoming a target-week prediction feature by backdating its claimed capture time. It is still local evidence, not independent proof of the site's visibility state or deadline accuracy. No collector row is currently passed to production prediction logic.

## Verification

Focused tests: `tests/test_manual_manager_collector.py` (four passed). They cover invalid IDs/duplicates/captains, pre-deadline versus late receipt, local persistence and exports, consensus counts, and the Flask preview/confirm flow. Production model weights, optimizer rules and historical reports were unchanged.
