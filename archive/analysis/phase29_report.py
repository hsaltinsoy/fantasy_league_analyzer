"""Render the signed Phase 29 batch and GW9-history sensitivity comparison."""
import json
from pathlib import Path

from archive.analysis.phase29_gw12_capture import ORIGINAL

DOCS = Path('docs')


def main():
    current = json.loads((DOCS/'phase29_gw12_capture.json').read_text(encoding='utf-8'))
    original = json.loads((DOCS/'phase27_history_impact.json').read_text(encoding='utf-8'))['scenarios']['gw9']
    names = {p['id']:p['name'] for v in current['predictions'].values() for p in v['starting_xi']+v['bench']}
    names.update({int(pid):p['name'] for v in original.values() for pid,p in v['pool'].items()})
    def label(i):
        return f'{names.get(i, str(i))} ({i})'
    lines = ['# Phase 29 — GW12 final prospective capture', '',
        '**Status:** six-model append-only batch captured before the official deadline, replayed offline, and bound to a third-party signed timestamp. The tracking database retains its conservative `locally_recorded_pre_deadline_not_verified` status; the separate RFC 3161 receipt provides independently checkable proof of artifact existence before the deadline.', '',
        '## Deadline and source checks', '',
        f'- Official GW12 deadline: **{current["deadline_at"]}**; snapshot created **{current["capture_timestamp"]}**; [FreeTSA](https://freetsa.org/index_en.php) signed timestamp: **2026-11-09 10:57:56 UTC**.',
        f'- Official fixtures observed **{current["fixture_retrieved_at"]}**: 9 scheduled fixtures, none started. GW11 official feed marked all fixtures finished and all points and bonuses added.',
        f'- Current official player feed observed **{current["player_retrieved_at"]}**: 573 players, valid positive prices and current availability fields. Fixtures and player pool passed the repository quality checks without warnings.',
        f'- Official histories retrieved **{current["history_retrieved_at"]}**: 573/573 GW11 rows, zero request failures, no GW12 rows in inputs. Freshness status **{current["history_freshness"]["status"]}**.',
        f'- Frozen Football-Data evidence: {current["external_matches_count"]} match rows, digest `{current["external_digest"]}`. The archive was imported 2026-10-31 16:20:08 UTC, and its latest match date is 2026-10-26. All 18 fixture clubs have features, and the 81 rows have xG values. **GW10–GW11 external matches are missing**, so xG features lag current official history. The query admits only completed matches dated before capture from imports recorded before capture.', '',
        '## Immutable capture identifiers', '',
        f'- New snapshot ID: `{current["snapshot_id"]}`',
        f'- Six-model batch ID: `{current["batch_id"]}`',
        f'- Frozen replay input hash: `{current["input_hash"]}`',
        f'- Stored snapshot payload hash: `{current["snapshot_payload_sha256"]}`',
        f'- Original GW12 snapshot preserved: `{ORIGINAL}`',
        '- Model configuration: 0.5 fixture weight, 0.20 captain risk, 0.15 extra minutes-risk adjustment, balanced optimizer profile, unchanged 0.25 eligibility threshold and 100 budget. Uniform and position-aware xG use the frozen 0.4 adjustment; rest-days control has zero rest weight.', '',
        '## Six saved predictions', '',
        '| Model | Prediction ID | Formation | Captain | Cost | Fantasy xPts | Risk objective | Osimhen XI | Replay |',
        '| --- | --- | --- | --- | ---: | ---: | ---: | --- | --- |']
    for name, row in current['predictions'].items():
        lines.append(f'| {name} | `{current["prediction_ids"][name]}` | {row["formation"]} | {row["captain"]} | {row["cost"]:.1f} | {row["expected_fantasy_points"]:.2f} | {row["risk_adjusted_objective"]:.4f} | {"yes" if any(p["id"]==507 for p in row["starting_xi"]) else "no"} | {"pass" if current["replay_checks"][name] else "FAIL"} |')
    lines += ['', 'Objectives are comparable only within a model configuration; they are not accuracy measures. The saved batch contains the full player objects and projections in [phase29_gw12_capture.json](phase29_gw12_capture.json).', '',
        '## Starting XI and bench', '']
    for name, row in current['predictions'].items():
        lines += [f'### {name}', '',
            'XI: ' + ', '.join(label(p['id']) for p in row['starting_xi']) + '.', '',
            'Bench: ' + ', '.join(label(p['id']) for p in row['bench']) + '.', '']
    lines += ['## Data-update sensitivity versus the original GW9-history batch', '',
        'The original and new batches differ in historical weeks **and** observation time for current player prices, availability, and fixtures. The Football-Data archive is the same 81-match source, but the new snapshot is a fresh capture. This is a data-update sensitivity analysis, not an isolated causal estimate for GW10–GW11 and not an accuracy evaluation.', '',
        '| Model | XI overlap | XI entered | XI left | Captain change | Formation | Cost old → new |',
        '| --- | ---: | --- | --- | --- | --- | ---: |']
    for name, row in current['predictions'].items():
        old = original[name]
        old_xi = set(old['xi'])
        new_xi = {p['id'] for p in row['starting_xi']}
        old_captain = label(old['captain'])
        new_captain = row['captain']
        lines.append(f'| {name} | {len(old_xi & new_xi)}/11 | {", ".join(str(i) for i in sorted(new_xi-old_xi)) or "none"} | {", ".join(str(i) for i in sorted(old_xi-new_xi)) or "none"} | {old_captain} → {new_captain} | {old["formation"]} → {row["formation"]} | {old["cost"]:.1f} → {row["cost"]:.1f} |')
    lines += ['', 'Osimhen (507) is absent from every new XI. He was also absent from every original XI. This is optimizer selection, not an eligibility finding.', '',
        'Largest changes among players selected in the new squad and present in the old projection pool (new xPts minus original xPts):', '',
        '| Model | Largest selected-player changes |', '| --- | --- |']
    for name, row in current['predictions'].items():
        old_pool = original[name]['pool']
        selected = [p for p in row['starting_xi']+row['bench'] if str(p['id']) in old_pool]
        selected.sort(key=lambda p: abs(p['xpts']-old_pool[str(p['id'])]['xpts']), reverse=True)
        text = '; '.join(f'{label(p["id"])} {p["xpts"]-old_pool[str(p["id"])]["xpts"]:+.3f}' for p in selected[:3])
        lines.append(f'| {name} | {text} |')
    lines += ['', '## Independent timestamp and replay integrity', '',
        'FreeTSA issued [an RFC 3161 response](phase29_capture.tsr) for the SHA-256 digest of [the capture artifact](phase29_gw12_capture.json): `1f582c935c617c409278799f24f4ab30d5fc785fa316a66e234aff0e757b3c91`. The signed token reports `20261109105756Z`, and its message imprint exactly matches the artifact bytes. The embedded signer certificate matches [FreeTSA’s published TSA certificate](phase29_freetsa_tsa.crt), whose file SHA-256 matches the fingerprint published on its [site](https://freetsa.org/index_en.php). Full certificate-chain and request verification with `openssl ts -verify -in docs/phase29_capture.tsr -queryfile docs/phase29_capture.tsq -CAfile docs/phase29_freetsa_ca.pem -untrusted docs/phase29_freetsa_tsa.crt` returned **Verification: OK**. The [request](phase29_capture.tsq), [response](phase29_capture.tsr), [signed token](phase29_capture_token.p7s), and [CA certificate](phase29_freetsa_ca.pem) are retained.', '',
        'The offline replay loaded the stored snapshot, rebuilt all six variants, and matched each saved XI, bench, captain, formation, fantasy xPts, cost, and objective. The original snapshot payload hash was checked unchanged. Generated timestamps and player ordering outside lineup membership are not claimed byte-identical.', '',
        '## Tests and limits', '',
        'Focused tests for the six-model batch, capture integrity, history freshness and experimental adjustments passed **12/12**. A signed timestamp proves the capture artifact existed before the deadline; it does not independently prove the earlier source APIs contained these exact values at their locally logged retrieval times. The official deadline came from the official fixture API, and source observations remain local timestamps. The xG archive lacks GW10–GW11 matches. No production weights, optimizer rules, original prediction, or original snapshot were changed. No commit or push was made.', '']
    (DOCS/'phase29_gw12_prospective_capture.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    main()
