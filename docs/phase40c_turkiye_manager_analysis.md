# Phase 40C - Türkiye top-50 manager squad analysis

## Findings and access boundary

The user has observed that **Ligler ve Kupalar → Türkiye → manager** shows an authenticated manager's starting XI, bench, captain, vice captain, player fantasy points and performance information. This is **user-reported UI evidence**, not an independently inspected export or API. Previous-gameweek navigation and whether selections are visible *before* the deadline remain unverified.

The [official rules](https://tfffantezilig.com/yardim) confirm a country league, cumulative league rankings, squad lock one hour before the first match, and manager cards that can change scoring or constraints. The existing [TFF integration](../data_sources/tff_official.py) contains authenticated player-statistics and player-history calls, with no manager-ranking or squad API. The public [home page](https://tfffantezilig.com/) offers login, but no documented manager-data export. The [privacy notice](https://tfffantezilig.com/yardim?tab=kisisel-verilerin-islenmesine-dair-aydinlatma-metni-ve-gizlilik-politikasi) covers account IDs, usage and performance data. I found no verified permission or supported method for automated collection of other managers' squads. No authenticated manager request or collection was made.

| Field | Current evidence | Historical/pre-deadline status |
| --- | --- | --- |
| Top-50 ranks and manager identifiers | Türkiye navigation reported by user; top-50 retrieval unverified | Prior-week ranks absent |
| XI, bench, captain, vice captain | Visible for a selected manager per user | Week navigation and visibility time unverified |
| Player points and manager performance | Visible per user | Finalized points are postmatch outcomes |
| Manager card | Official rules document card effects | Card display and historical use unverified |
| Capture timestamp | No source timestamp identified | Cannot establish pre-deadline view |

## Safe manual-import path

If the user is permitted to inspect and record the displayed data, use a local, isolated table with one row per manager-week. Record `gameweek`, pseudonymous manager key, rank **at capture**, rank's scoring-through week, UTC capture time, source-view time, visibility state (pre-deadline/post-deadline/unknown), XI and bench official player IDs, captain/vice captain IDs, formation, card status, and a provenance note. Record historical points only through the *prior* week in the prediction input; final weekly points belong in a separate evaluation column. Omit names, email, profile URLs and raw account IDs. If stable pseudonyms are needed, keep the mapping privately outside analysis artifacts.

Manual entry still requires respect for site terms and privacy; it is not a substitute for permission if systematic reuse is restricted. Do not infer IDs by names alone. Validate 11 distinct starters, four distinct bench players, captain and vice captain in the XI, official player-ID mapping, and card-specific formation/budget exceptions. Reject incomplete rows rather than filling gaps. Store no manager rows in production tables or frozen snapshots.

## Historical and leakage checks

For each candidate week, manually verify whether the UI offers a previous-week selector and whether it displays the squad as selected at that week's deadline, its final post-substitution lineup, or a later edited view. A historical squad *visible today* is not proof of pre-deadline availability. A current top-50 list cannot stand in for the top 50 before GW6–GW11: cumulative rank can change after every finalized week. For target GW *w*, eligible consensus requires rank and selections observed by a documented cutoff before GW *w*; any post-deadline observation is descriptive only. If the UI hides other managers' picks until lock, same-week consensus cannot be used prospectively; use only earlier weeks' selections.

## Experimental features and evaluation design

With authorized, timestamped observations, calculate selection and captain share separately for contemporaneous top 10, 25 and 50. Compare those shares with general selection popularity from the **same cutoff**; if general popularity is unavailable, report the differential as missing. Measure XI overlap with the unchanged optimizer, and week-to-week selection changes only for stable pseudonyms. Separate cumulative rank from recent weekly scores, and stratify or exclude manager-card weeks because cards alter scoring and sometimes formation/budget rules.

Candidate *experimental* features are top-N selection share, top-N captain share, top-minus-general popularity, and lagged manager decision consistency. None is assigned a production weight. Once multiple prospectively captured weeks exist, compare Phase 40 baseline, baseline plus selection consensus, baseline plus captain consensus, and combined consensus using identical player pools, budgets, optimizer policy and scoring. Freeze inputs before each deadline; join actuals only afterward. Report weekly XI-plus-captain points, rank metrics, XI overlap, captain outcomes, and leave-one-week-out sensitivity. If same-week picks are not visible before lock, shift consensus by one completed week.

## Result and next step

**Zero manager-week records** meet the required permission and timing standard. Top-10/25/50 consensus, optimizer agreement, general-popularity differential and all four model comparisons are therefore **not estimable**. The next useful check is a permitted, manual inspection of historical-week navigation and exact visibility timing, followed by a small prospective capture under clear reuse permission. No Phase 41 work or production change was started.
