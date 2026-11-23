# Phase 26B: live history refresh verification

## Scope and provenance

On 2026-11-07 UTC, a read-only verification used the 573 player IDs from frozen GW12 snapshot `ceddd5ae-a154-411b-9581-31a484c87f5f`. The official fixture API response was retrieved at `2026-11-07T14:12:03.365914+00:00`; it identified GW10 as the latest fully completed gameweek and GW11 as partial. The history retrieval ended at `2026-11-07T14:16:51.158728+00:00`. These are **later observations**, not evidence that GW10 histories were published at the original GW12 capture cutoff.

No fetched history was written to PostgreSQL, the frozen snapshot, or saved predictions. The dry run used in-memory inputs only. The local snapshot still exists with 12 linked prediction records after verification.

## Retrieval

The official authenticated player-history API was called sequentially in one browser context, with a minimum 0.5-second interval between request starts. This bounds concurrency to one and throughput to at most two starts per second. A published provider quota was not established, so this conservative cap is an operational choice, not a claimed official limit. Transient transport and HTTP 5xx errors may be retried twice; authorization and HTTP 429 errors stop the run.

| Measure | Result |
| --- | ---: |
| Players requested | 573 |
| HTTP requests | 573 |
| Successful requests | 573 |
| Failed requests | 0 |
| Retries | 0 |
| Elapsed time | 287.782 s |
| Average requests/s | 1.991 |
| Invalid or duplicate rows | 0 |
| Players with no retrieved history | 0 |

Raw player-week coverage, before excluding unfinished weeks:

| GW | Players with a record |
| ---: | ---: |
| 1 | 522 |
| 2 | 543 |
| 3 | 550 |
| 4–10 | 573 each |
| 11 | 125 |

GW10 appeared for all 573 IDs. The 125 GW11 records were omitted from model inputs because GW11 was partial. No GW12 or later record was returned in this run. After filtering, histories contain only GW1–GW10; the target-week leakage count is zero. Early-week gaps require a separate player registration or fixture audit and are not treated as zero fantasy points.

## Staged archive comparison

The existing PostgreSQL archive contained histories for 572 IDs. The refreshed read-only result contained 580 player-week rows absent from staging, zero changed rows for matching player-week keys, and zero previously staged rows missing from the live response. The difference includes 573 GW10 rows; seven other new rows are not classified further by this verification. This comparison does not modify staging.

## Freshness gate and dry run

The refreshed input passed the Phase 26 freshness gate: latest completed fixture week 10, latest observed history week 10, and 573/573 players with GW10 history (100%). The gate rejected the existing staged archive as `confirmed_ingestion_failure` and a deliberately incomplete in-memory history set as `partial_player_coverage`. GW11 was recorded as `partial_gameweeks_not_required`.

An in-memory `short_form_3w` GW12 prediction completed with 318 eligible players, a 3-4-3 formation, and 74.41 projected fantasy points. This is an exploratory retrospective dry run using histories observed after the frozen capture; it is **not** a genuine pre-deadline forecast and was not saved. It does not replace or revise any frozen GW12 prediction.

## Implementation and verification

`fetch_player_histories` now has optional request spacing, bounded transient retries, failure collection, progress reporting, and timing/coverage metrics. Default caller behavior remains unchanged. `analysis.phase26b_refresh_verification` reuses that fetcher and performs read-only archive comparison, freshness checks, and an in-memory prediction. The JSON measurement artifact is `docs/phase26b_refresh_verification.json`.

Focused tests: **19 passed** (`test_tff_official.py`, `test_history_freshness.py`, `test_prospective_monitor.py`). A new test covers retry accounting and exclusion of GW11/GW12 from GW12 model inputs.

## Recommendations and limits

1. Run the rate-limited refresh in the prospective capture workflow when staging is behind a confirmed completed fixture week. Keep the existing freshness gate in place.
2. Record official history retrieval timestamps at ingestion time. The old staged archive lacks them, so historical publication timing cannot be reconstructed.
3. Retain the raw-week coverage metric to detect partial publication and continue excluding unfinished weeks.
4. Investigate the seven other new player-week rows and early-week coverage gaps before making claims about completeness across the entire season.
5. The dry-run gate checks fixture completion and row presence. It does not independently certify that every player-week fantasy score is final; future evaluation should continue to require official outcome finalization evidence.
