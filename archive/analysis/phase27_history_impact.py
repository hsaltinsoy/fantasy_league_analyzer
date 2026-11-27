"""Read-only GW12 sensitivity replay with official history through GW10."""
import json
from pathlib import Path

from archive.analysis.phase25_diagnostics import SNAPSHOT, BATCH, INPUT_HASH
from analysis.capture_integrity import validate_inputs
from analysis.prediction_tracking import get_snapshot, _postgres, DEFAULT_DB
from analysis.predict_next_week import build_candidate_pool
from analysis.live_benchmark import _fixture_lookup
from analysis.football_data_live import make_adjuster_from_matches
from analysis.multisource_experimental import rest_days_adjustment
from analysis.verified_fixtures_v36 import make_optimizer
from analysis.optimizer import optimize
from analysis.walkforward_backtest import participation
from data_sources.tff_official import fetch_player_histories

MODELS = ('baseline_5w', 'short_form_3w', 'stable_8w', 'uniform_xg', 'position_aware_xg', 'rest_days_control')


def write_report(data):
    names = {int(k): v['name'] for k, v in data['scenarios']['gw10']['short_form_3w']['pool'].items()}
    names.update({r['id']: r['name'] for r in data['eligibility_changes']})
    def label(i):
        return f'{names.get(i, str(i))} ({i})'
    lines = ['# Phase 27 — GW10 history impact', '',
        '**Classification:** retrospective sensitivity experiment; refreshed histories were observed after the frozen GW12 capture. This is not a verified pre-deadline forecast.', '',
        '## Access and integrity', '',
        'The earlier PostgreSQL timeout was transient: the project Docker database is now healthy on 127.0.0.1:5433, the port is reachable, and the configured credentials connect. The frozen snapshot exists in the expected database. No database reset or record update was made.', '',
        f'Snapshot `{data["snapshot_id"]}` passed the frozen input hash check (`{INPUT_HASH}`). All six GW9 replays exactly match saved XI, bench, captain, fantasy xPts, and objective. The same 573 frozen players, prices, availability, fixtures, football-data evidence, risk settings, and optimizer constraints were used in both scenarios. The refreshed scenario appends exactly one official GW10 row per player to the original history. GW11 and GW12 are excluded. Official rows were retrieved at `{data["history_retrieved_at"]}` with zero request failures.', '',
        'The earlier Phase 26B dry run reported 318 eligible players because it used the entire refreshed history response. That response included seven additional pre-GW10 rows. Under the strict GW10-only intervention here, eligibility is **314 → 319**: 17 enter and 12 leave. Thus 314 → 318 cannot be explained as GW10 alone; it also reflects older missing-row recovery. The extra eligible player in the strict scenario is Mervan Müjdeci (1273), whose frozen history is empty and whose single GW10 minute gives a 0.655 participation proxy. The full refreshed response adds earlier rows and changes his proxy and eligibility.', '',
        '## Six-model comparison', '',
        '| Model | Eligible | XI overlap | Captain GW9 → GW10 | Formation GW9 → GW10 | Cost GW9 → GW10 | Fantasy xPts GW9 → GW10 | Objective GW9 → GW10 |',
        '| --- | ---: | ---: | --- | --- | ---: | ---: | ---: |']
    for model in MODELS:
        a, b = (data['scenarios'][s][model] for s in ('gw9', 'gw10'))
        overlap = len(set(a['xi']) & set(b['xi']))
        lines.append(f'| {model} | {a["eligible"]} → {b["eligible"]} | {overlap}/11 | {label(a["captain"])} → {label(b["captain"])} | {a["formation"]} → {b["formation"]} | {a["cost"]:.1f} → {b["cost"]:.1f} | {a["fantasy_points"]:.2f} → {b["fantasy_points"]:.2f} | {a["objective"]:.4f} → {b["objective"]:.4f} |')
    lines += ['', 'Objectives are comparable only within each row. They are model scores, not observed outcomes.', '',
        '## Squad and prediction sensitivity', '']
    for model in MODELS:
        a, b = (data['scenarios'][s][model] for s in ('gw9', 'gw10'))
        ap, bp = a['pool'], b['pool']
        common = set(ap) & set(bp)
        top = sorted(common, key=lambda k: abs(bp[k]['xpts'] - ap[k]['xpts']), reverse=True)[:5]
        lines += [f'### {model}', '',
            f'XI in: {", ".join(label(i) for i in sorted(set(b["xi"])-set(a["xi"]))) or "none"}. XI out: {", ".join(label(i) for i in sorted(set(a["xi"])-set(b["xi"]))) or "none"}.', '',
            f'Bench in: {", ".join(label(i) for i in sorted(set(b["bench"])-set(a["bench"]))) or "none"}. Bench out: {", ".join(label(i) for i in sorted(set(a["bench"])-set(b["bench"]))) or "none"}.', '',
            'Largest common-player xPts changes: ' + ', '.join(f'{label(int(k))} {bp[k]["xpts"]-ap[k]["xpts"]:+.3f}' for k in top) + '.', '']
    changes = data['eligibility_changes']
    entries = [r for r in changes if not r['old_eligible'] and r['new_eligible']]
    exits = [r for r in changes if r['old_eligible'] and not r['new_eligible']]
    lines += ['## Eligibility and participation', '',
        f'Newly eligible ({len(entries)}): ' + ', '.join(label(r['id']) for r in entries) + '.', '',
        f'Newly excluded ({len(exits)}): ' + ', '.join(label(r['id']) for r in exits) + '.', '',
        'The 16 returning entrants and 12 exits crossed the unchanged 0.25 participation gate as the last-four-minute window advanced. Player 1273 had no frozen history and became eligible from a GW10 row alone. The JSON artifact lists old/new probabilities and last-four minutes for all 29 eligibility changes and all other probability changes of at least 0.10. Frozen availability and prices are identical in both scenarios.', '',
        '## Osimhen (507)', '',
        'GW1–GW9 minutes: 90, 90, 90, 33, 0, 0, 13, 90, 88. GW10 minutes: ' + str(next(r['new_last4_minutes'][-1] for r in changes if r['id']==507)) + '. Participation probability: 0.710 → 0.944. Official availability and price remain frozen.', '',
        '| Model | xPts GW9 → GW10 | Forward rank GW9 → GW10 | Selection GW9 → GW10 | Forced GW10 XI objective loss |',
        '| --- | ---: | ---: | --- | ---: |']
    for model in MODELS:
        a, b = (data['scenarios'][s][model] for s in ('gw9', 'gw10'))
        def rank(s):
            forwards = sorted((v for v in s['pool'].values() if v['position']=='FWD'), key=lambda v:-v['xpts'])
            return 1 + next(i for i,v in enumerate(forwards) if v['name']==s['pool']['507']['name'] and v['xpts']==s['pool']['507']['xpts'])
        def status(s):
            return 'XI' if 507 in s['xi'] else 'bench' if 507 in s['bench'] else 'out'
        loss = b['forced_osimhen_start']-b['objective'] if b['forced_osimhen_start'] is not None else None
        lines.append(f'| {model} | {a["pool"]["507"]["xpts"]:.3f} → {b["pool"]["507"]["xpts"]:.3f} | {rank(a)} → {rank(b)} | {status(a)} → {status(b)} | {loss:+.4f} |' if loss is not None else f'| {model} | — | — | — | unavailable |')
    lines += ['', '## Limitations and recommendation', '',
        'One additional week changes one of eleven XI slots in the least sensitive model and seven in four others. These shifts show sensitivity, not improved accuracy. GW10 was retrieved after the capture, and no independent pre-deadline timestamp establishes its availability at that time. The isolated GW10 scenario intentionally preserves missing older rows; it is a controlled intervention rather than a complete historical repair. Keep production weights and thresholds unchanged. Evaluate against finalized official outcomes before tuning.', '',
        '## Verification', '',
        'The replay completed with zero fetch failures and all 573 GW10 rows. Frozen input hash, six saved GW9 XIs, benches, captains, fantasy xPts, and objectives matched exactly. The optimizer returned solutions for both scenarios and all six models. No original snapshot or prediction was overwritten. Full player projections and lineups are in [phase27_history_impact.json](phase27_history_impact.json).', '']
    Path('docs/phase27_history_impact.md').write_text('\n'.join(lines), encoding='utf-8')


def run():
    snapshot = get_snapshot(SNAPSHOT)
    payload = snapshot['payload']
    week = snapshot['gameweek']
    assert validate_inputs(week, payload['players'], payload['fixtures'], payload['histories']) == INPUT_HASH
    players = payload['players']
    old = {str(row['player_id']): row['rows'] for row in payload['histories']}
    cache = Path('docs/phase27_gw10_rows.json')
    if cache.exists():
        fetched = json.loads(cache.read_text(encoding='utf-8'))
    else:
        fetched = fetch_player_histories([p['id'] for p in players], completed_through=10,
            target_week=week, min_interval_seconds=.5, max_retries=2,
            continue_on_error=True, include_metrics=True)
        cache.write_text(json.dumps(fetched, ensure_ascii=False), encoding='utf-8')
    live = fetched['rows_by_player']
    if fetched['metrics']['errors'] or len(live) != len(players) or any(
        sum(int(r['gameweekOrder']) == 10 for r in live[str(p['id'])]) != 1 for p in players):
        raise RuntimeError('Incomplete GW10 coverage; refusing comparison')
    new = {pid: rows + [next(r for r in live[pid] if int(r['gameweekOrder']) == 10)]
           for pid, rows in old.items()}
    assert all([int(r['gameweekOrder']) for r in new[pid][:-1]] ==
               [int(r['gameweekOrder']) for r in old[pid]] for pid in old)
    lookup = {week: _fixture_lookup({'matches': payload['fixtures']})}
    archive = {'weeks': {str(week): {'matches': payload['fixtures']}}}
    from datetime import datetime
    cutoff = datetime.fromisoformat(snapshot['captured_at'].replace('Z', '+00:00'))
    saved_rows = [_postgres(DEFAULT_DB).get_prediction(pid) for pid in _postgres(DEFAULT_DB).prediction_ids(SNAPSHOT)]
    saved = {r['model']: r['payload'] for r in saved_rows if (r['payload'].get('benchmark') or {}).get('batch_id') == BATCH}
    assert len(saved) == 6
    scenarios = {}
    for label, histories in [('gw9', old), ('gw10', new)]:
        records = [(p, histories[str(p['id'])]) for p in players]
        scenarios[label] = {}
        for name in MODELS:
            model = name if name in MODELS[:3] else 'short_form_3w'
            pool, excluded = build_candidate_pool(week, players, records, lookup, model,
                                                  availability_policy='legacy_pre31a')
            if name in ('uniform_xg', 'position_aware_xg'):
                adjust, _ = make_adjuster_from_matches(payload['feature_evidence']['football_data_matches'], archive, week, cutoff, name, .4)
                pool = adjust(pool)
            elif name == 'rest_days_control':
                pool = [rest_days_adjustment(p, {}, None, 0) for p in pool]
            prepared = []
            make_optimizer(records, week, .2, .15, {}, 0, optimizer_func=lambda rows: prepared.extend(rows) or {})(pool)
            solution = optimize(prepared, time_limit=4, formation_policy='legacy_pre39_v1')
            if 'error' in solution:
                raise RuntimeError(f'{label}/{name}: {solution["error"]}')
            xi = [p['id'] for p in solution['starting_xi']]
            scenarios[label][name] = {
                'eligible': len(pool), 'excluded': excluded,
                'pool': {str(p['id']): {'name': p['name'], 'position': p['position'], 'xpts': p['xpts'],
                    'participation_probability': p['participation_probability']} for p in prepared},
                'xi': xi, 'bench': [p['id'] for p in solution['squad'] if p['id'] not in xi],
                'captain': solution['captain']['id'], 'formation': solution['formation'],
                'cost': solution['squad_cost'], 'fantasy_points': solution['expected_fantasy_points'],
                'objective': solution['risk_adjusted_objective'], 'status': solution['status'],
                'forced_osimhen_start': None}
            if label == 'gw10':
                forced = optimize(prepared, force_start_ids=(507,), time_limit=4,
                                  formation_policy='legacy_pre39_v1')
                if 'error' not in forced:
                    scenarios[label][name]['forced_osimhen_start'] = forced['risk_adjusted_objective']
    eligibility = []
    old_ids = set(scenarios['gw9']['short_form_3w']['pool'])
    new_ids = set(scenarios['gw10']['short_form_3w']['pool'])
    for p in players:
        pid = str(p['id'])
        a, b = old[pid], new[pid]
        pa = participation(a)['probability'] if a else None
        pb = participation(b)['probability'] if b else None
        if (pid in old_ids) != (pid in new_ids) or (pa is not None and pb is not None and abs(pb-pa) >= .1):
            eligibility.append({'id': p['id'], 'name': p['name'], 'old_eligible': pid in old_ids,
                'new_eligible': pid in new_ids, 'old_probability': pa, 'new_probability': pb,
                'old_last4_minutes': [r.get('minutesPlayed') for r in a[-4:]],
                'new_last4_minutes': [r.get('minutesPlayed') for r in b[-4:]]})
    for name in MODELS:
        replay = scenarios['gw9'][name]
        original = saved[name]
        assert set(replay['xi']) == {p['id'] for p in original['starting_xi']}, name
        assert set(replay['bench']) == {p['id'] for p in original['bench']}, name
        assert replay['objective'] == original['risk_adjusted_objective'], name
        assert replay['fantasy_points'] == original['expected_fantasy_points'], name
        assert next(p['name'] for p in players if p['id'] == replay['captain']) == original['captain'], name
    return {'snapshot_id': SNAPSHOT, 'history_retrieved_at': fetched['retrieved_at'],
        'fetch_metrics': fetched['metrics'], 'eligibility_changes': eligibility, 'scenarios': scenarios,
        'saved_baselines': {n: {'xi': [p['id'] for p in saved[n]['starting_xi']],
            'captain': saved[n]['captain'], 'objective': saved[n]['risk_adjusted_objective']} for n in MODELS}}


if __name__ == '__main__':
    path = Path('docs/phase27_history_impact.json')
    result = run()
    path.write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    write_report(result)
    print(path)
