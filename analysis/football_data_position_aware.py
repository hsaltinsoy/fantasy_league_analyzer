"""Frozen, opt-in position-aware xG sensitivity; never edits tracking."""
import hashlib
import json
from datetime import datetime, timezone
from statistics import mean, median

from sqlalchemy import select
from storage import models as m
from storage.db import engine_from_env
from storage.runtime_repository import RuntimeRepository
from analysis.optimizer import optimize

SOURCE_ID = '4bed3c93-be7c-4e5c-81ff-d745462ebe92'
SOURCE_HASH = 'db585be703b1d32d61ddab98cc7f15627200784cbff319a9eb1818a6bdeb2f14'
WEIGHTS = (0, .1, .2, .3, .4, .5)


def clamp(value, limit=1.0):
    return max(-limit, min(limit, value))


def relative(value, reference):
    return 0.0 if value is None or not reference else clamp((float(value) - reference) / reference)


def signal(player, reference):
    evidence = player.get('football_data')
    if not evidence:
        return 0.0, {'missing': True}
    team = evidence['team']
    position = player['position']
    opponent_xg = evidence.get('opponent_attacking_strength')
    clean = evidence.get('expected_clean_sheet_indicator')
    attack = mean([relative(team.get('xg_for'), reference['xg']),
                   relative(evidence.get('opponent_defensive_xg_conceded'), reference['xg'])])
    recent = relative(team.get('last3_xg_for'), team.get('last5_xg_for'))
    venue = ('home' if player.get('home') else 'away')
    venue_attack = relative(team.get(f'{venue}_xg_for'), team.get('xg_for'))
    if position == 'FWD':
        raw = .7 * attack + .2 * recent + .1 * venue_attack
        drivers = {'attack': attack, 'recent_xg': recent, 'venue_attack': venue_attack}
    elif position == 'MID':
        shots = relative(team.get('last3_shots_on_target'), team.get('last5_shots_on_target'))
        raw = .65 * attack + .2 * recent + .15 * shots
        drivers = {'attack': attack, 'recent_xg': recent, 'shot_trend': shots}
    elif position == 'DEF':
        defence = -mean([relative(team.get('xg_against'), reference['xg']),
                         relative(opponent_xg, reference['xg'])])
        venue_defence = -relative(team.get(f'{venue}_xg_against'), team.get('xg_against'))
        raw = .8 * defence + .2 * venue_defence
        drivers = {'defence': defence, 'venue_defence': venue_defence,
                   'clean_sheet_indicator': clean}
    elif position == 'GK':
        defence = -mean([relative(team.get('xg_against'), reference['xg']),
                         relative(opponent_xg, reference['xg'])])
        save_volume = relative(evidence.get('opponent_shots_on_target'), reference['sot'])
        # A high shot count helps only when the opponent's xG is below league average.
        gated_saves = max(0.0, save_volume) * max(0.0, -relative(opponent_xg, reference['xg']))
        raw = .85 * defence + .15 * gated_saves
        drivers = {'defence': defence, 'gated_save_volume': gated_saves,
                   'clean_sheet_indicator': clean}
    else:
        raise ValueError(f'Unknown position: {position}')
    return clamp(raw), drivers


def run(engine):
    with engine.connect() as db:
        source = db.execute(select(m.historical_reports.c.content).where(
            m.historical_reports.c.id == SOURCE_ID)).scalar_one()
    if source.get('input_snapshot_sha256') != SOURCE_HASH or source.get('reproduction') != 'passed':
        raise ValueError('Frozen input verification failed')
    base = source['scenarios']['baseline']['pool']
    raw = json.dumps([{'id': p['id'], 'team': p['team'], 'position': p['position'],
                       'price': p['price'], 'xpts': p['baseline_xpts']} for p in base],
                     sort_keys=True, separators=(',', ':'))
    if hashlib.sha256(raw.encode()).hexdigest() != SOURCE_HASH or len(base) != 179:
        raise ValueError('Frozen player pool hash or count mismatch')
    replay = optimize(base)
    saved = source['scenarios']['baseline']
    if replay['expected_points'] != 67.92 or replay['expected_points'] != saved['expected_points'] or \
       {p['id'] for p in replay['starting_xi']} != {p['id'] for p in saved['starting_xi']}:
        raise ValueError('Frozen baseline optimization mismatch')
    teams = {p['team']: p['football_data']['team'] for p in base if p.get('football_data')}
    home_teams = {str(match['homeClubId']) for match in source['remaining_fixtures']}
    reference = {'xg': mean(v['xg_for'] for v in teams.values() if v['xg_for'] is not None),
                 'sot': mean(v['shots_on_target_per_match'] for v in teams.values()
                             if v['shots_on_target_per_match'] is not None)}
    scenarios = {}
    for weight in WEIGHTS:
        pool = []
        for p in base:
            evidence = dict(p['football_data']) if p.get('football_data') else None
            if evidence is not None:
                opponent = teams.get(p['opponent'])
                evidence['opponent_shots_on_target'] = (opponent or {}).get('shots_on_target_per_match')
            s, drivers = signal({**p, 'home': p['team'] in home_teams,
                                 'football_data': evidence}, reference)
            delta = clamp(weight * s, .15)
            pool.append({**p, 'xpts': round(max(.1, p['baseline_xpts'] * (1 + delta)), 3),
                         'position_signal': s, 'position_drivers': drivers,
                         'adjustment_fraction': delta})
        selection = optimize(pool)
        if 'error' in selection:
            raise ValueError(selection['error'])
        scenarios[str(int(weight * 100))] = {'weight': weight, 'pool': pool,
            'expected_points': selection['expected_points'], 'formation': selection['formation'],
            'captain': selection['captain']['name'], 'starting_xi': selection['starting_xi'],
            'bench': [p for p in selection['squad'] if p['id'] not in
                      {q['id'] for q in selection['starting_xi']}], 'squad': selection['squad']}
    stats = {}
    for position in ('GK', 'DEF', 'MID', 'FWD'):
        rows = [p for p in scenarios['50']['pool'] if p['position'] == position]
        changes = [p['xpts'] - p['baseline_xpts'] for p in rows]
        stats[position] = {'count': len(rows), 'mean_delta': mean(changes),
            'median_delta': median(changes), 'max_positive': max(changes),
            'max_negative': min(changes)}
    result = {'schema_version': 1, 'model_version': 'position_aware_xg_sensitivity_v1',
        'source_report_id': SOURCE_ID, 'input_snapshot_sha256': SOURCE_HASH,
        'original_capture_utc': source['captured_utc'],
        'evaluated_utc': datetime.now(timezone.utc).isoformat(),
        'reference': reference, 'scenarios': scenarios, 'position_stats': stats,
        'uniform_reference': {k: source['scenarios'][k] for k in ('medium', '30%', '50%')},
        'source_provenance': source.get('limitations'),
        'optimizer': source['optimizer'],
        'limitations': ['Sensitivity strengths are untrained and do not establish forecast accuracy.']}
    result['report_id'] = RuntimeRepository(engine).save_generated_report('football_data_position_aware_gw10', result)
    return result


if __name__ == '__main__':
    engine = engine_from_env()
    try:
        print(json.dumps(run(engine), ensure_ascii=True))
    finally:
        engine.dispose()
