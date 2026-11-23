# Phase 31A — data quality and multi-source foundation

## Availability root cause and fix

The official player parser copies `availabilityStatus` into `availability` without changing it. The current Phase 29 player pool contains **492 `AVAILABLE`, 74 `DEPARTED`, and 7 `SUSPENDED`** players. [availability.py](../analysis/availability.py) normalized case but omitted `DEPARTED` from `BLOCKED`, so Seyfettin Anıl Yaşar (TFF ID **355**) passed the participation and availability gates. He was in the candidate pool but in no saved Phase 29 XI.

`DEPARTED` is now blocked with factor zero. Status normalization trims whitespace and handles case, spaces and hyphens; the raw captured status remains unchanged. The current Phase 29 input pool would have **321** eligible players under the new rule, down from 322. Blocked statuses now include `UNAVAILABLE`, `SUSPENDED`, `INJURED`, `OUT`, `BANNED`, and `DEPARTED`; doubtful aliases remain downweighted. The observed official statuses are the three listed above. Unknown statuses still follow the existing fallback policy and should be reviewed separately if the official vocabulary expands.

Historical predictions remain immutable. Frozen pre-31A replays use an explicit `legacy_pre31a` availability policy; new predictions default to `current`. [Replay verification](phase31a_replay_verification.json) reproduced all **12 saved GW12 model outputs** across the original and Phase 29 snapshots: XI, bench, captain, formation, fantasy xPts, objective **and original eligible counts** (314 and 322 respectively). Without that explicit legacy policy, the new eligibility rule removes ID 355 from both old candidate pools; it does not change their saved optimal lineups. The compatibility flag is confined to replay and analysis code, not the default capture path.

## Official xG/xA quality

The [official GW1–GW11 history audit](phase31a_official_expected_quality.json) inspected **6,199 rows**. Both `xG` and `xA` are numeric in 6,199/6,199 rows and nonzero in **0/6,199**. The same population has 3,104 positive-minute rows, 252 goal rows and 190 assist rows. The API does not supply a field-level quality flag or documentation here establishing that these zeros are measured xG/xA. The observed distribution strongly suggests unpopulated placeholder fields; it does **not** prove that every individual zero is false.

The new [quality classifier](../data_sources/official_history_quality.py) records source URL, retrieval timestamp, row digest, numeric/nonzero counts and a `suspected_unpopulated` state. In that state, the evidence adapter returns `value=None` with `missing_reason=unpopulated_field`; it preserves all raw zeros in the source rows. If a later, quality-checked population has nonzero values, genuine zero observations remain zero. No replacement values were invented, and the six production models still use no official player xG/xA.

## Football-Data completeness and cause

The archive holds **81** completed 2026–27 matches. A bounded, read-only probe of the current [Turkey CSV](https://www.football-data.co.uk/mmz4281/2627/T1.csv) found **99** rows. All 18 missing archive fixtures are present in the current CSV with matching official date, clubs and full-time score; all 18 have both xG fields. [The reconciliation artifact](phase31a_football_data_audit.json) records IDs, dates, teams and checks. The source file SHA-256 is `86af3b956c49ea86c5e1a58c8ac45237ba0b7bd52e46e5874e9697f09336bf08`.

| GW | Missing official fixture IDs | Count | Current CSV match |
| ---: | --- | ---: | --- |
| 10 | 217, 218, 219, 220, 221, 222, 223, 224, 225 | 9 | 9/9 date, club, score and xG complete |
| 11 | 208, 209, 210, 211, 212, 213, 214, 215, 216 | 9 | 9/9 date, club, score and xG complete |

The existing import was recorded **2026-10-31 16:20 UTC**, before GW10 finished; its last match date is 2026-10-26. The current [source listing](https://football-data.co.uk/turkeym.php) says updated 2026-11-09 and the current file includes both weeks. Thus the *current* 18-match gap is a stale ingestion, not failed fixture matching or permanent source noncoverage. The exact publication time of each missing row is unknown, so historical pre-deadline availability is not inferred.

The [source fair-use policy](https://football-data.co.uk/contact.php) permits only light personal/academic automated download, at most twice weekly, and restricts commercial/heavy training use. This audit made **two** CSV GETs on 2026-11-09 and will not poll again this week. No CSV row was imported; no duplicate or existing frozen external evidence was changed. A future permitted import can reuse the repository's immutable source hash and match identity checks, but must retain its actual retrieval time and must never backfill the Phase 29 frozen xG bundle.

## Provider adapter foundation

[provider_evidence.py](../data_sources/provider_evidence.py) defines a provider-neutral `ProviderAdapter` protocol for player statistics, team statistics, fixtures, availability and expected metrics. Its immutable batch and record types require provider identity, endpoint, retrieved time, source SHA-256, competition/season, event time, optional published time, explicit completeness and missing reason, field provenance, and reviewed high-confidence entity mapping before a canonical TFF ID is assigned. A batch fails closed when incomplete, lacks the requested record kind, or was retrieved/published after the prediction cutoff. Observed player/team statistics from the target event or later are rejected; a future fixture schedule is allowed only when it was observed before the cutoff. Missing values cannot silently become numeric zero.

These are contracts and quality helpers only. API-Football, Yuvron, Sportmonks and other unverified providers are **not** wired into production predictions. Provider-specific licensing, player/club crosswalks, failure handling, historical revisions and point-in-time coverage need measured samples before an adapter can be enabled.

## Verification and next step

Focused regression tests cover blocked and doubtful statuses, the new candidate gate and legacy replay, explicit missing values, invalid provider responses, cutoff leakage, future fixture schedules and all-zero xG/xA handling. **29/29 passed.** The read-only replay verification passed for both frozen GW12 six-model batches. The archive reconciliation matched all 18 missing fixtures to the current CSV with zero score mismatches.

Next, schedule one license-compliant Football-Data refresh after the source updates, verify the import's source hash and 99 fixture links, and evaluate its effect only in a **new** timestamped experiment. Before any new production capture, confirm whether `DEPARTED` status has other semantics and test the new gate against live official statuses. Do not assign new xG/xA weights until a player-level source has measured coverage and leak-free historical evidence.

No production model weight or optimizer rule was changed. No GW12 snapshot or saved prediction was overwritten, and nothing was committed or pushed.
