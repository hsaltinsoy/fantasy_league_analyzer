# Phase 26 — history freshness and capture integrity

## GW12 root cause and evidence

The frozen GW12 snapshot `ceddd5ae-a154-411b-9581-31a484c87f5f` has 573 players. All 572 players with archived weekly rows stop at GW9; one player has no history. The 572 PostgreSQL `historical_data/player_*.json` source payloads also stop at GW9 and have **null retrieval timestamps**. `RuntimeRepository.historical_records(before_week=12)` reads those archived payloads without refreshing the official history API. `live_benchmark.generate()` filters to weeks `<12` and saved those same rows. The parser did not discard GW10/11 rows; none were present in the selected archived payloads. The historical ingest was a one-time staged local archive, not a rolling update.

The official fixture payload retrieved **2026-11-07 12:46:10 UTC**, before the GW12 snapshot at **13:23:23 UTC**, showed **GW10 9/9 FT** and **GW11 2 FT / 7 scheduled**. A read-only authenticated official history probe at **13:47:50–13:47:52 UTC**, after the capture, found GW10 rows for sampled IDs 12, 216 and 507, and no GW11 rows for those IDs. Sample comparison:

| Player ID | Frozen latest week | Later official GW10 points / minutes | Later official GW11 row |
| --- | ---: | ---: | --- |
| 12 | 9 | 3 / 90 | absent |
| 216 | 9 | 0 / 40 | absent |
| 507 | 9 | 6 / 61 | absent |

This confirms GW10 is available **now** and missing from storage and the frozen model inputs. It does **not** prove the player-history API had published GW10 by 13:23:23 UTC; the archived source payloads have no observation timestamp and the probe ran later. GW11 was only partially complete and must not have been required or used. The original GW12 snapshot and its 12 linked predictions remain unchanged.

## New prospective freshness gate

`analysis.history_freshness.audit` compares the target week, completed fixtures in an official dated feed, latest stored and model-input history weeks, individual player coverage, partial weeks, and observed official history availability. It reports missing weeks, retrieval timestamps, percentages, status and reasons. Target-week rows and rows from a partial gameweek are rejected.

`prospective_monitor.capture` now checks that audit **before saving**. If completed fixtures are newer than stored history, it probes the official player-history API. When the probe confirms availability, it fetches all candidate histories in one authenticated browser session, keeps only weeks through the latest completed week and below the target week, and uses that one refreshed set for all model runs. The observation timestamp and freshness report are saved with the immutable snapshot. A partial refresh, unverified source availability, or an ingestion failure blocks capture. If the official history API demonstrably has no rows for the completed week, `--allow-source-unavailable` permits a documented exception; it never permits target-week or partial-week outcomes. The strict `live_benchmark.generate` path independently enforces the gate.

The PostgreSQL `/api/lineup/generate` route also checks freshness before saving a prediction. Unlike the prospective monitor, that route does not auto-refresh histories; it returns a freshness error when stored rows lag completed fixtures. The prospective capture is the supported refreshed-history path.

The capture code uses an explicitly configured 90% player coverage floor for a newly completed week. This is an operational completeness check, **not** a model eligibility threshold. A player with no individual history is counted and reported; it does not by itself block a 573-player capture. A source-unavailable override requires a dated full-pool fetch showing no rows for the completed week; an empty five-player sample is insufficient. The threshold may need revision if the official API legitimately omits many inactive players. The legacy archive's null retrieval timestamps cannot establish what was legitimately available at the old GW12 cutoff; fresh API observations are required for future captures.

## Limitations and next checks

- The later GW10 probe is a **retrospective source-availability comparison**, not a new pre-deadline GW12 forecast. No GW12 re-optimization or backfill was performed.
- The full 573-player official-history refresh path was not executed against the live API in this phase; it is tested with controlled inputs. Authentication, throughput and coverage must be verified before relying on the next automated capture.
- Fixture `FT` is used as completion evidence for the history freshness gate, but fantasy-point finalization is a separate official process. The evaluation engine still requires finalized official results.
- A source-unavailable override is explicit and records the dated official probe. It should be reviewed before scheduling unattended captures.
