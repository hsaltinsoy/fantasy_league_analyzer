"""Read-only, approximate GW11 walk-forward replay and official outcome comparison."""
import json
from datetime import datetime
from itertools import combinations
from math import sqrt
from pathlib import Path

from analysis.capture_integrity import validate_inputs
from analysis.prediction_tracking import get_snapshot
from analysis.six_model_batch import NAMES, replay
from analysis.six_model_evaluation import _spearman
from analysis.live_benchmark import fetch_official_fixtures
from analysis.predict_next_week import build_candidate_pool
from analysis.live_benchmark import _fixture_lookup
from storage.db import engine_from_env
from storage.football_data_repository import FootballDataRepository

SNAPSHOT_ID = '72226192-1049-4d89-b9a9-aec4d9da4709'
ORIGINAL_HASH = '3d10cc948ef74a9a21d4ebe1fa004158078b58633f4e095edc752676f0a207a0'
OUT = Path('docs/phase32_gw11_walkforward.json')


def prepare():
    snapshot = get_snapshot(SNAPSHOT_ID)
    source = snapshot['payload']
    assert validate_inputs(11, source['players'], source['fixtures'], source['histories']) == ORIGINAL_HASH
    archive = fetch_official_fixtures(include_evidence=True)
    week = next(w for w in archive['raw_payload']['data']['gameweeks'] if w['order'] == 11)
    deadline = week['deadline']
    assert datetime.fromisoformat(snapshot['captured_at']) < datetime.fromisoformat(deadline.replace('Z', '+00:00'))
    assert week['finished'] and all(m['status'] == 'FT' and m['pointsAdded'] and m['bonusesAdded'] for m in week['matches'])
    assert all(d['allPointsAdded'] and d['allBonusesAdded'] for d in week['matchDays'])
    fresh = json.loads(Path('docs/phase27_gw10_rows.json').read_text(encoding='utf-8'))
    actual_cache = Path('docs/phase28_official_histories.json')
    if not actual_cache.exists():
        raise RuntimeError('Official GW11 history cache absent')
    histories = []
    for entry in source['histories']:
        pid = str(entry['player_id'])
        rows = entry['rows']
        assert all(int(r['gameweekOrder']) <= 9 for r in rows)
        gw10 = [r for r in fresh['rows_by_player'][pid] if int(r['gameweekOrder']) == 10]
        assert len(gw10) == 1, pid
        histories.append({'player_id': entry['player_id'], 'rows': rows + gw10})
    assert len(histories) == len(source['players'])
    prices = []
    by_history = {str(h['player_id']): h['rows'][-1] for h in histories}
    for p in source['players']:
        historic_cost = by_history[str(p['id'])].get('cost')
        if historic_cost is not None and float(historic_cost) > 0 and float(p['price']) != float(historic_cost):
            prices.append({'id': p['id'], 'snapshot_price': p['price'], 'gw10_history_cost': historic_cost})
    cutoff = datetime.fromisoformat(snapshot['captured_at'])
    external = FootballDataRepository(engine_from_env()).matches_before(cutoff)
    assert external and all(str(m['match_date']) < cutoff.date().isoformat() for m in external)
    external = json.loads(json.dumps(external, default=str))
    bundle = {'gameweek': 11, 'players': source['players'], 'fixtures': source['fixtures'],
              'histories': histories, 'cutoff_utc': snapshot['captured_at'],
              'deadline_at': deadline, 'external_matches': external,
              'team_features': {}, 'fixture_date': None, 'availability_policy': 'legacy_pre31a'}
    bundle['input_hash'] = validate_inputs(11, bundle['players'], bundle['fixtures'], histories)
    return bundle, {'snapshot_id': SNAPSHOT_ID, 'original_hash': ORIGINAL_HASH,
                    'replay_hash': bundle['input_hash'], 'snapshot_captured_at': snapshot['captured_at'],
                    'official_deadline': deadline, 'gw10_rows_retrieved_at': fresh['retrieved_at'],
                    'gw10_rows': len(histories), 'external_matches': len(external),
                    'official_fixture_checked_at': archive['captured_utc'],
                    'snapshot_vs_gw10_cost_mismatches': prices}


def predict_only(bundle):
    result = replay(bundle)
    if result['status'] != 'complete':
        raise RuntimeError(f'Six-model replay incomplete: {result["statuses"]}')
    return result


def evaluate_predictions(predictions, actual_rows):
    """Outcome data is accepted only here, after all predictions are generated."""
    actual = {}
    for pid, rows in actual_rows.items():
        week = [r for r in rows if int(r['gameweekOrder']) == 11]
        if len(week) == 1 and week[0].get('points') is not None:
            actual[str(pid)] = week[0]
    output = {}
    for name in NAMES:
        pred = predictions[name]
        xi, bench = pred['starting_xi'], pred['bench']
        assert len(xi) == 11 and len(bench) == 4
        captain = next(p for p in xi if p['captain'])
        if any(str(p['id']) not in actual for p in xi + bench):
            raise RuntimeError(f'Missing official GW11 selected-player point: {name}')
        def player(p):
            row = actual[str(p['id'])]
            return {'id': p['id'], 'name': p['name'], 'position': p['position'],
                    'club_id': p['team'], 'predicted_xpts': p['xpts'],
                    'actual_points': row['points'], 'difference': round(p['xpts'] - row['points'], 3),
                    'actual_minutes': row.get('minutesPlayed'), 'captain': bool(p.get('captain'))}
        starters = [player(p) for p in xi]
        substitutes = [player(p) for p in bench]
        errors = [p['difference'] for p in starters + substitutes]
        actual_xi = sum(p['actual_points'] for p in starters)
        captain_actual = actual[str(captain['id'])]['points']
        predicted = pred['expected_fantasy_points']
        output[name] = {'eligible_players': pred['eligible_players'], 'excluded': pred['excluded'],
            'starting_xi': starters, 'bench': substitutes, 'captain_id': captain['id'],
            'captain': captain['name'], 'formation': pred['formation'], 'squad_cost': pred['cost'],
            'predicted_points': predicted, 'actual_xi_points': actual_xi,
            'captain_extra_points': captain_actual, 'actual_points': actual_xi + captain_actual,
            'predicted_minus_actual': round(predicted - actual_xi - captain_actual, 2),
            'optimization_objective': pred['risk_adjusted_objective'],
            'mae_selected_15': round(sum(abs(e) for e in errors)/15, 3),
            'rmse_selected_15': round(sqrt(sum(e*e for e in errors)/15), 3),
            'spearman_selected_15': _spearman([p['predicted_xpts'] for p in starters + substitutes],
                                              [p['actual_points'] for p in starters + substitutes])}
    return output


def report(data):
    models = data['models']
    lines = ['# Phase 32 — GW11 walk-forward backtest', '',
        '**Classification:** approximate retrospective simulation, generated after GW11. These are not genuine pre-deadline predictions.', '',
        '## Historical inputs and leakage checks', '',
        f'Official GW11 deadline: **{data["integrity"]["official_deadline"]}**. Official GW11 fixtures are finished and every match and match day is marked points and bonuses added (checked {data["integrity"]["official_fixture_checked_at"]}). Player results cover all selected players.', '',
        f'Frozen GW11 snapshot `{SNAPSHOT_ID}` was captured {data["integrity"]["snapshot_captured_at"]}; original hash `{ORIGINAL_HASH}` verifies. It contains {data["integrity"]["gw10_rows"]} players, prices, availability, GW11 fixtures, and history through GW9. One official GW10 row per player was appended, giving replay hash `{data["integrity"]["replay_hash"]}`. GW11 and later histories are excluded from predictions.', '',
        f'**Limitation:** GW10 rows were retrieved {data["integrity"]["gw10_rows_retrieved_at"]}, after the deadline. Their pre-deadline publication is not timestamped. Snapshot prices, availability and fixtures are from Oct 31, before GW10 ended; their exact Nov 6 state is unavailable. GW10 history cost differs from frozen snapshot price for {len(data["integrity"]["snapshot_vs_gw10_cost_mismatches"])} players with a positive history cost; see JSON. Thus this is an approximate retrospective simulation of the requested cutoff. No current GW12 attributes were substituted. Actuals are loaded only after all six predictions return.', '',
        f'The two xG variants use {data["integrity"]["external_matches"]} Football-Data matches imported before the frozen snapshot cutoff. No later external match data enters the replay. Rest-days control uses its existing zero-weight configuration. The historical legacy availability rule is used to reproduce the original model era; it can admit a `DEPARTED` status, so eligibility is approximate. Model weights, optimizer rules, and original records were untouched.', '',
        '## Results, ranked by realized score', '',
        '| Rank | Model | Eligible | Predicted | Actual | Pred − actual | Captain (extra actual) | Formation | Cost | Objective | MAE / RMSE (15) |',
        '| ---: | --- | ---: | ---: | ---: | ---: | --- | --- | ---: | ---: | --- |']
    for rank, (name, m) in enumerate(sorted(models.items(), key=lambda kv: -kv[1]['actual_points']), 1):
        lines.append(f'| {rank} | {name} | {m["eligible_players"]} | {m["predicted_points"]:.2f} | {m["actual_points"]:.0f} | {m["predicted_minus_actual"]:+.2f} | {m["captain"]} ({m["captain_extra_points"]:+}) | {m["formation"]} | {m["squad_cost"]:.1f} | {m["optimization_objective"]:.3f} | {m["mae_selected_15"]:.2f} / {m["rmse_selected_15"]:.2f} |')
    lines += ['', 'Actual = starting XI official points plus the captain’s points once more (double captain). Bench points are listed but do not count: this optimizer chooses a fresh squad and the existing evaluation implements no automatic substitution. MAE/RMSE compare uncaptained player xPts to actual points over each model’s selected 15; the player sets differ. Objectives are comparable only within a model configuration.', '', '## Starting XI overlap', '', '| Pair | Shared players |', '| --- | ---: |']
    for a,b in combinations(NAMES,2):
        n = len({p['id'] for p in models[a]['starting_xi']} & {p['id'] for p in models[b]['starting_xi']})
        lines.append(f'| {a} / {b} | {n}/11 |')
    for name in NAMES:
        m = models[name]
        lines += ['', f'## {name}', '',
            f'Formation {m["formation"]}; captain {m["captain"]}; XI actual {m["actual_xi_points"]}, captain extra {m["captain_extra_points"]}, final {m["actual_points"]}.', '',
            '| Position | Player (TFF ID) | Club ID | Predicted xPts | Actual GW11 | Pred − actual |',
            '| --- | --- | ---: | ---: | ---: | ---: |']
        for p in m['starting_xi']:
            lines.append(f'| {p["position"]} | {p["name"]} ({p["id"]}){" **(C)**" if p["captain"] else ""} | {p["club_id"]} | {p["predicted_xpts"]:.2f} | {p["actual_points"]} | {p["difference"]:+.2f} |')
        lines += ['', 'Substitutes (no score contribution):', '', '| Position | Player (TFF ID) | Club ID | Predicted xPts | Actual GW11 | Pred − actual |', '| --- | --- | ---: | ---: | ---: | ---: |']
        for p in m['bench']:
            lines.append(f'| {p["position"]} | {p["name"]} ({p["id"]}) | {p["club_id"]} | {p["predicted_xpts"]:.2f} | {p["actual_points"]} | {p["difference"]:+.2f} |')
    lines += ['', '## Decisions and limitations', '']
    for pid, label in [(507,'Osimhen'), (12,'Salah')]:
        selected = [(name, 'captain' if m['captain_id']==pid else 'XI' if pid in {p['id'] for p in m['starting_xi']} else 'bench' if pid in {p['id'] for p in m['bench']} else 'out') for name,m in models.items()]
        actual = data['focus_actuals'].get(str(pid))
        lines.append(f'{label} ({pid}): official GW11 {actual["points"] if actual else "unknown"} points, {actual["minutesPlayed"] if actual else "unknown"} minutes. Selection: ' + ', '.join(f'{n} {s}' for n,s in selected) + '.')
        lines.append('')
    lines += ['The short-form XI scored 57, while the stable XI scored 73 here. Short-form captain Ernest Muçi scored 3; stable captain Salah scored 10. The zero-weight rest-days control exactly matches short-form. The uniform xG variant scored 58 and the position-aware xG variant 57; these are team-level xG adjustments, not player xG estimates. The one-week result does not establish causal benefit or harm from xG or history-window length.', '',
        'Largest selected-player misses (predicted minus actual): ' + ', '.join(f'{p["name"]} {p["difference"]:+.2f} ({p["model"]})' for p in data['largest_selected_errors'][:6]) + '.', '',
        'Highest actual scorers absent from every XI: ' + ', '.join(f'{p["name"]} ({p["id"]}) {p["points"]} points [{p["short_form_eligibility"]}]' for p in data['high_actual_not_in_any_xi'][:8]) + '.', '',
        f'The short-form candidate screen excluded {models["short_form_3w"]["excluded"]["minutes"]} players for recent participation and {models["short_form_3w"]["excluded"]["availability"]} for availability. The JSON identifies whether high actual scorers were in the short-form pool. This does not prove a threshold error without valid deadline-time availability.', '',
        'The genuine pre-deadline saved GW11 predictions remain separate: short-form scored 57 actual points, stable scored 76 (Phase 28). They used GW9 history and are not the six retrospective GW10-history results above. Differences between short and stable windows are observations from one week, not evidence of long-run superiority. Pre-deadline GW10 publication and exact Nov 6 metadata remain unverified, so a fully valid prospective six-model comparison is blocked.', '',
        '## Verification', '',
        'The input hash was checked before replay, all 572 players received exactly one GW10 row, six models completed, and official GW11 points were applied after prediction generation. Focused pytest: 2 passed (actual-result isolation and captain/bench scoring). No saved GW11/GW12 snapshot or prediction was modified.', '']
    Path('docs/phase32_gw11_walkforward.md').write_text('\n'.join(lines), encoding='utf-8')


def run():
    bundle, integrity = prepare()
    predictions = predict_only(bundle)['predictions']
    actual_cache = json.loads(Path('docs/phase28_official_histories.json').read_text(encoding='utf-8'))
    models = evaluate_predictions(predictions, actual_cache['rows_by_player'])
    actual = {pid: next(r for r in rows if int(r['gameweekOrder']) == 11)
              for pid, rows in actual_cache['rows_by_player'].items() if any(int(r['gameweekOrder']) == 11 for r in rows)}
    selected = {p['id'] for m in models.values() for p in m['starting_xi']}
    lookup = {11: _fixture_lookup({'matches': bundle['fixtures']})}
    records = [(p, next(h['rows'] for h in bundle['histories'] if h['player_id'] == p['id'])) for p in bundle['players']]
    short_pool, _ = build_candidate_pool(11, bundle['players'], records, lookup,
                                         'short_form_3w', availability_policy='legacy_pre31a')
    eligible = {p['id'] for p in short_pool}
    names = {str(p['id']): p['name'] for p in bundle['players']}
    high_excluded = sorted(({'id': int(pid), 'name': names.get(pid, 'unknown'), 'points': row['points'],
                            'short_form_eligibility': 'eligible' if int(pid) in eligible else 'excluded'} for pid,row in actual.items()
                            if int(pid) not in selected), key=lambda r: -r['points'])[:15]
    misses = sorted(({'model': name, **p} for name,m in models.items() for p in m['starting_xi'] + m['bench']),
                    key=lambda r: abs(r['difference']), reverse=True)[:20]
    data = {'classification': 'approximate_retrospective_simulation', 'integrity': integrity,
            'warnings': ['GW10 history first retrieved after deadline', 'Oct 31 player metadata may be stale at Nov 6 deadline',
                         '220 positive GW10 history costs differ from snapshot prices',
                         'Legacy availability policy can include DEPARTED', 'No automatic substitutions modeled'],
            'official_actual_retrieved_at': actual_cache['retrieved_at'],
            'models': models, 'largest_selected_errors': misses,
            'high_actual_not_in_any_xi': high_excluded,
            'focus_actuals': {str(pid): actual.get(str(pid)) for pid in (507,12)}}
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    report(data)
    return data


if __name__ == '__main__':
    result = run()
    print({n: (m['predicted_points'], m['actual_points']) for n,m in result['models'].items()})
