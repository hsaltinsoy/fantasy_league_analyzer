"""Replay a saved midweek report from pre-capture PostgreSQL evidence."""
import hashlib
import json
from datetime import datetime

from sqlalchemy import select
from storage import models as m
from storage.db import engine_from_env
from storage.runtime_repository import RuntimeRepository
from storage.football_data_repository import FootballDataRepository
from data_sources.tff_official import _extract
from analysis.predict_next_week import build_candidate_pool
from analysis.football_data_team_features import team_features
from analysis.football_data_midweek import adjustment
from analysis.optimizer import optimize

ORIGINAL = '980597dc-0abb-4098-921d-dea08dbd6f25'
STRENGTHS = [('baseline', 0), ('small', .05), ('medium', .10), ('large', .15),
             ('20%', .20), ('25%', .25), ('30%', .30), ('40%', .40), ('50%', .50)]


def run(engine, report_id=ORIGINAL):
    with engine.connect() as db:
        old = db.execute(select(m.historical_reports.c.content).where(
            m.historical_reports.c.id == report_id)).scalar_one()
        cutoff = datetime.fromisoformat(old['captured_utc'])
        source = db.execute(select(m.source_payloads.c.raw_payload, m.source_payloads.c.retrieved_at,
            m.source_payloads.c.content_sha256).where(
            m.source_payloads.c.id.like('tff-current-%'),
            m.source_payloads.c.retrieved_at <= cutoff).order_by(
            m.source_payloads.c.retrieved_at.desc()).limit(1)).first()
        history_max = db.execute(select(m.source_artifacts.c.imported_at).where(
            m.source_artifacts.c.source_path.like('historical_data/player_%.json')).order_by(
            m.source_artifacts.c.imported_at.desc()).limit(1)).scalar_one()
    if source is None or history_max > cutoff:
        raise ValueError('Original player or history evidence cannot be frozen safely')
    players = _extract(source.raw_payload)
    repo = RuntimeRepository(engine)
    histories = repo.historical_records(before_week=10)
    records = [(p, histories.get(str(p['id']), [])) for p in players]
    lookup = {}
    for match in old['remaining_fixtures']:
        home, away = str(match['homeClubId']), str(match['awayClubId'])
        lookup[home], lookup[away] = away, home
    base, _ = build_candidate_pool(10, players, records, {10: lookup})
    if len(base) != old['eligible_players']:
        raise ValueError(f'Eligible pool mismatch: {len(base)} vs {old["eligible_players"]}')
    features = team_features(FootballDataRepository(engine).matches_before(cutoff))
    scenarios = {}
    for label, strength in STRENGTHS:
        pool = []
        for p in base:
            delta, evidence = adjustment(features, p['team'], p['opponent'], strength)
            pool.append({**p, 'baseline_xpts': p['xpts'],
                         'xpts': round(max(.1, p['xpts'] * (1 + delta)), 3),
                         'adjustment_fraction': delta, 'football_data': evidence})
        solution = optimize(pool)
        if 'error' in solution:
            raise ValueError(solution['error'])
        scenarios[label] = {'strength': strength, 'expected_points': solution['expected_points'],
            'formation': solution['formation'], 'captain': solution['captain']['name'],
            'starting_xi': solution['starting_xi'],
            'bench': [p for p in solution['squad'] if p['id'] not in
                      {q['id'] for q in solution['starting_xi']}],
            'squad': solution['squad'], 'pool': pool}
        if label in old['scenarios']:
            saved = old['scenarios'][label]
            fresh = scenarios[label]
            for key in ('expected_points', 'formation', 'captain'):
                if fresh[key] != saved[key]:
                    raise ValueError(f'Original {label} {key} mismatch: {fresh[key]} vs {saved[key]}')
            for key in ('starting_xi', 'bench'):
                if {p['id'] for p in fresh[key]} != {p['id'] for p in saved[key]}:
                    raise ValueError(f'Original {label} {key} identity mismatch')
            for key in ('top20', 'top_positive', 'top_negative'):
                for saved_player in saved[key]:
                    match = next((p for p in pool if p['id'] == saved_player['id']), None)
                    if match is None or match['xpts'] != saved_player['xpts']:
                        raise ValueError(f'Original {label} player projection mismatch: {saved_player["id"]}')
    raw = json.dumps([{'id': p['id'], 'team': p['team'], 'position': p['position'],
                       'price': p['price'], 'xpts': p['xpts']} for p in base],
                     sort_keys=True, separators=(',', ':'))
    result = {'schema_version': 2, 'original_report_id': report_id,
              'captured_utc': old['captured_utc'], 'source_player_retrieved_at': source.retrieved_at.isoformat(),
              'source_player_sha256': source.content_sha256,
              'input_snapshot_sha256': hashlib.sha256(raw.encode()).hexdigest(),
              'reproduction': 'passed', 'eligible_players': len(base),
              'remaining_fixtures': old['remaining_fixtures'], 'scenarios': scenarios,
              'optimizer': {'budget': 100, 'max_per_team': 3, 'risk_profile': 'balanced'},
              'limitations': ['Original live fixture API payload was not retained; fixture rows are from original report.',
                              'Player-history original retrieval timestamps are unknown; PostgreSQL staging predates capture.']}
    result['report_id'] = repo.save_generated_report('football_data_frozen_extension_gw10', result)
    return result


if __name__ == '__main__':
    engine = engine_from_env()
    try:
        print(json.dumps(run(engine), ensure_ascii=True, default=str))
    finally:
        engine.dispose()
