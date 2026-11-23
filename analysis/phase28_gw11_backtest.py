"""Read-only official GW11 audit of immutable pre-deadline predictions."""
import json
from datetime import datetime
from pathlib import Path
from math import sqrt

from analysis.live_benchmark import fetch_official_fixtures
from analysis.prediction_tracking import get_snapshot, get_prediction, _postgres, DEFAULT_DB
from analysis.capture_integrity import validate_inputs
from analysis.benchmark_evaluation import _fixture_check, _actual_check, PLAYER_HISTORY_URL
from analysis.six_model_evaluation import _spearman
from analysis.history_freshness import audit, require_capture_ready
from data_sources.tff_official import fetch_player_histories


def prepare_gw12(snapshot, histories):
    from analysis.predict_next_week import predict
    from analysis.live_benchmark import _fixture_lookup
    from analysis.football_data_live import make_adjuster_from_matches
    from analysis.multisource_experimental import rest_days_adjustment
    from analysis.six_model_batch import NAMES
    from analysis.capture_integrity import digest
    payload = snapshot['payload']
    players = payload['players']
    records = [(p, [r for r in histories[str(p['id'])] if int(r['gameweekOrder']) < 12]) for p in players]
    lookup = {12: _fixture_lookup({'matches': payload['fixtures']})}
    archive = {'weeks': {'12': {'matches': payload['fixtures']}}}
    cutoff = datetime.fromisoformat(snapshot['captured_at'])
    evidence = payload['feature_evidence']['football_data_matches']
    output = {}
    for name in NAMES:
        model = name if name in NAMES[:3] else 'short_form_3w'
        adjuster = None
        if name in ('uniform_xg', 'position_aware_xg'):
            adjuster, _ = make_adjuster_from_matches(evidence, archive, 12, cutoff, name, .4)
        elif name == 'rest_days_control':
            adjuster = lambda pool: [rest_days_adjustment(p, {}, None, 0) for p in pool]
        output[name] = predict(12, players, records, lookup, {}, model=model,
                               pool_adjuster=adjuster)
    return {'classification':'retrospective_gw12_refresh_not_saved_prediction',
            'original_snapshot_id':snapshot['id'],
            'input_hash':digest({'players':players,'fixtures':payload['fixtures'],
                'histories':[{'player_id':p['id'],'rows':h} for p,h in records]}),
            'history_through':11,'frozen_nonhistory_capture':snapshot['captured_at'],
            'models':output}


def run():
    archive = fetch_official_fixtures(include_evidence=True)
    week = next(w for w in archive['raw_payload']['data']['gameweeks'] if w['order'] == 11)
    if not (week.get('finished') is True and all(m.get('status') == 'FT' and
        m.get('pointsAdded') is True and m.get('bonusesAdded') is True for m in week['matches']) and
        all(d.get('allPointsAdded') is True and d.get('allBonusesAdded') is True for d in week['matchDays'])):
        raise RuntimeError('GW11 official points/bonuses are not marked complete')
    from sqlalchemy import text
    from storage.db import engine_from_env
    with engine_from_env().connect() as conn:
        ids = [r[0] for r in conn.execute(text('select id from snapshots where gameweek=11 order by captured_at'))]
    snapshots = [get_snapshot(i) for i in ids]
    cutoff = datetime.fromisoformat(week['deadline'].replace('Z', '+00:00'))
    snapshots = [s for s in snapshots if datetime.fromisoformat(s['captured_at']) < cutoff]
    if not snapshots:
        raise RuntimeError('No pre-deadline GW11 snapshots')
    predictions = []
    pg = _postgres(DEFAULT_DB)
    for s in snapshots:
        for pid in pg.prediction_ids(s['id']):
            predictions.append((s, get_prediction(pid)))
    from analysis.phase27_history_impact import SNAPSHOT
    gw12 = get_snapshot(SNAPSHOT)
    player_ids = sorted({str(p['id']) for p in gw12['payload']['players']} |
                        {str(p['id']) for s in snapshots for p in s['payload']['players']}, key=int)
    cache = Path('docs/phase28_official_histories.json')
    if cache.exists():
        fetched = json.loads(cache.read_text(encoding='utf-8'))
    else:
        fetched = fetch_player_histories(player_ids, completed_through=11, target_week=12,
            min_interval_seconds=.2, max_retries=2, continue_on_error=True, include_metrics=True)
        if fetched['metrics']['errors']:
            raise RuntimeError('Incomplete official history fetch')
        cache.write_text(json.dumps(fetched, ensure_ascii=False), encoding='utf-8')
    rows = fetched['rows_by_player']
    results = []
    for s, pred in predictions:
        p = s['payload']
        digest = validate_inputs(11, p['players'], p['fixtures'], p['histories'])
        if digest != '3d10cc948ef74a9a21d4ebe1fa004158078b58633f4e095edc752676f0a207a0':
            raise RuntimeError('Unexpected frozen GW11 input hash')
        if datetime.fromisoformat(pred['created_at']) >= cutoff:
            raise RuntimeError('Post-deadline prediction in GW11 set')
        entry, fixture_issues = _fixture_check(s, archive)
        selected = {str(q['id']) for q in pred['payload']['starting_xi'] + pred['payload']['bench']}
        actual, player_issues = _actual_check(s, entry,
            {'rows_by_player': {pid: [r for r in rows[pid] if int(r['gameweekOrder']) == 11] for pid in selected},
             'retrieved_at': fetched['retrieved_at'], 'source_url': PLAYER_HISTORY_URL}, selected)
        lineup = pred['payload']['starting_xi']
        captain = next(q for q in lineup if q.get('captain'))
        paired = [(q, actual[str(q['id'])]) for q in lineup + pred['payload']['bench'] if str(q['id']) in actual]
        errors = [q['xpts']-a for q,a in paired]
        xi_actual = sum(actual[str(q['id'])] for q in lineup) if all(str(q['id']) in actual for q in lineup) else None
        results.append({'snapshot_id': s['id'], 'prediction_id': pred['id'], 'model': pred['model'],
            'captured_at': s['captured_at'], 'deadline_at': s['deadline_at'], 'input_hash': digest,
            'latest_history_week': max(int(r['gameweekOrder']) for h in p['histories'] for r in h['rows']),
            'players': len(p['players']), 'fixture_issues': fixture_issues, 'player_issues': player_issues,
            'actual_coverage': len(actual), 'selected_count': len(selected),
            'predicted_fantasy_points': pred['payload'].get('expected_fantasy_points',
                round(sum(q['xpts'] for q in lineup) + captain['xpts'], 2)),
            'actual_xi': xi_actual, 'captain_id': captain['id'], 'captain_name': captain['name'],
            'captain_actual': actual.get(str(captain['id'])),
            'actual_total': xi_actual + actual[str(captain['id'])] if xi_actual is not None and str(captain['id']) in actual else None,
            'formation': pred['payload']['formation'],
            'mae_selected_15': sum(abs(e) for e in errors)/len(errors) if errors else None,
            'rmse_selected_15': sqrt(sum(e*e for e in errors)/len(errors)) if errors else None,
            'spearman_selected_15': _spearman([q['xpts'] for q,a in paired], [a for q,a in paired]),
            'player_errors': [{'id': q['id'], 'name': q['name'], 'predicted': q['xpts'],
                'actual': a, 'error': q['xpts']-a} for q,a in paired],
            'xi_ids': [q['id'] for q in lineup]})
    gw12_players = gw12['payload']['players']
    subset = {str(p['id']): rows[str(p['id'])] for p in gw12_players}
    probe = {'source':'official_tff_history_api','retrieved_at':fetched['retrieved_at'],
        'source_url':fetched['source_url'],'gameweek':11,
        'available_player_ids':[pid for pid,h in subset.items() if any(int(r['gameweekOrder'])==11 for r in h)],
        'sampled_player_count':len(gw12_players),'status':'available'}
    freshness = audit(12, gw12_players, subset, archive, source_probe=probe)
    try:
        require_capture_ready(freshness)
        freshness['gate'] = 'passed'
    except ValueError as exc:
        freshness['gate'] = str(exc)
    refreshed = prepare_gw12(gw12, subset)
    Path('docs/phase28_gw12_refreshed.json').write_text(
        json.dumps(refreshed, ensure_ascii=False, indent=2), encoding='utf-8')
    return {'fixture_retrieved_at':archive['captured_utc'], 'official_finished':True,
        'all_points_added':True,'all_bonuses_added':True,'history_retrieved_at':fetched['retrieved_at'],
        'history_metrics':fetched['metrics'],'gw11_snapshots':results,'gw12_freshness':freshness,
        'gw12_player_gw11_coverage':len(probe['available_player_ids'])}


if __name__ == '__main__':
    path = Path('docs/phase28_gw11_backtest.json')
    path.write_text(json.dumps(run(), ensure_ascii=False, indent=2), encoding='utf-8')
    print(path)
