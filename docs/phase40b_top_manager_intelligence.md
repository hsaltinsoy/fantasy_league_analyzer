# Phase 40B - Türkiye Ligi top-manager intelligence

**Audit time:** 2026-11-13 10:03:57 UTC. **Result:** manager selection collection and predictive evaluation are blocked by unverified access rights and absent historical evidence. No authenticated manager endpoint was called, no manager identity was stored, and no production data was changed.

## Access and permission findings

The [official rules](https://tfffantezilig.com/yardim) say that users automatically join a country league, that its classic standings use cumulative season points, and that squads lock one hour before the first match. The [public home page](https://tfffantezilig.com/) shows login and registration links, not a public manager-selection archive. The existing [TFF client](../data_sources/tff_official.py) accesses authenticated *player* statistics and weekly player histories; it has no manager-ranking, lineup, captain, bench, card or historical-rank method. A repository search found no archived Türkiye Ligi manager selections or rank snapshots.

The public rules establish that a country league exists. They do **not** establish that the top 50, their weekly selections, or an automated bulk-access right are available. The [privacy notice](https://tfffantezilig.com/yardim?tab=kisisel-verilerin-islenmesine-dair-aydinlatma-metni-ve-gizlilik-politikasi) treats account and ranking information as user data. No clear permission for collecting other managers' selections for this analysis was verified. Following the requested access safeguard, automated collection stopped here. No guessed endpoint, browser-session reuse for manager data, or access-control probe was attempted.

| Requested field | Verified coverage in workspace/public interface |
| --- | --- |
| Top 50 ranks and manager IDs | None; country-league ranking rule only |
| Weekly squads, XI, captain, vice captain, bench, cards | None |
| Weekly scores and historical ranks | None for managers |
| Pre-deadline capture time or rank snapshot | None |

## Selection analysis and predictive test

There are **0 manager-week records**. Top-10/25/50 popularity, captain consensus, weekly changes, optimizer agreement, and an all-manager popularity comparator are therefore **not estimable**. No numerical lift versus the Phase 40 baseline is claimed.

Current top managers cannot be used as if they were top-ranked in GW6-11: country-league rank is based on accumulated points and may change as results finalize. Likewise, a lineup retrieved after a deadline does not prove it was visible beforehand. A valid prospective evaluation would need a permitted snapshot captured before each target deadline with rank *as of then*, selection visibility time, gameweek, pseudonymous manager key, player IDs, XI/bench/captain, card status, and provenance. Historical points would be joined only after the week finalized.

## Recommendation

Do not add a manager-consensus feature yet. If TFF explicitly permits collection and exposes the needed fields, capture small, rate-limited, pseudonymous **prospective** snapshots. Compare lagged top-manager consensus with all-manager popularity and the unchanged Phase 40 baseline on identical candidate pools, budgets, formation policy, and XI-plus-captain scoring. Report coverage and manager-card effects separately. Avoid promoting any retrospective manager snapshot into a leakage-safe result.
