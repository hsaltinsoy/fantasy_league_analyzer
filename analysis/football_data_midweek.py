"""Opt-in midweek sensitivity report; never writes tracking predictions."""
import json
from datetime import datetime, timezone

from analysis.live_benchmark import fetch_official_fixtures
from analysis.predict_next_week import build_candidate_pool
from analysis.football_data_team_features import team_features, fixture_features
from analysis.optimizer import optimize
from analysis.prediction_tracking import parse_time
from storage.db import engine_from_env
from storage.runtime_repository import RuntimeRepository
from storage.football_data_repository import FootballDataRepository


def unstarted(matches, now):
    return [m for m in matches if parse_time(m.get('kickoffAt')) and
            parse_time(m['kickoffAt']) > now and
            str(m.get('status')).upper() in ('SCHEDULED', 'NOT_STARTED', 'NS') and
            m.get('homeScore') is None and m.get('awayScore') is None]


def adjustment(features, team, opponent, strength):
    evidence = fixture_features(features, team, opponent)
    if evidence is None or evidence['team']['xg_for'] is None or evidence['opponent_defensive_xg_conceded'] is None:
        return 0.0, evidence
    # One xG signal: attack minus opponent defence, centered on league xG.
    league = sum(v['xg_for'] for v in features.values() if v['xg_for'] is not None) / sum(
        v['xg_for'] is not None for v in features.values())
    signal = ((evidence['team']['xg_for'] + evidence['opponent_defensive_xg_conceded']) / 2 - league) / league
    return max(-.15, min(.15, strength * signal)), evidence


def run():
    engine = engine_from_env()
    try:
        repo = RuntimeRepository(engine)
        official = fetch_official_fixtures()
        now = parse_time(official['captured_utc'])
        all_matches = official['weeks']['10']['matches']
        remaining = unstarted(all_matches, now)
        if not remaining:
            raise ValueError('No confirmed unstarted GW10 fixtures')
        lookup = {}
        for match in remaining:
            home, away = str(match['homeClubId']), str(match['awayClubId'])
            lookup[home], lookup[away] = away, home
        players = repo.current_player_pool()
        histories = repo.historical_records(before_week=10)
        records = [(p, histories.get(str(p['id']), [])) for p in players]
        baseline, excluded = build_candidate_pool(10, players, records, {10: lookup})
        features = team_features(FootballDataRepository(engine).matches_before(now))
        report = {'type': 'midweek_exploratory_not_official_lineup',
                  'captured_utc': now.isoformat(), 'fixture_source': official['source_url'],
                  'fixture_source_retrieved_at': official['captured_utc'],
                  'remaining_fixtures': remaining,
                  'finished_or_started': [m for m in all_matches if m not in remaining],
                  'eligible_players': len(baseline), 'excluded': excluded,
                  'scenarios': {}, 'limitations': [
                      'Current player states are after the GW10 deadline.',
                      'Player history original retrieval timestamps are unknown.',
                      'Scenario strengths are untrained sensitivity settings.',
                      'This does not modify the actual GW10 squad or tracking records.']}
        frozen = repo.latest_lineup(10)
        frozen_ids = {int(p['id']) for p in frozen.get('starting_xi', [])} if frozen else set()
        for label, strength in [('baseline', 0.0), ('small', .05), ('medium', .10), ('large', .15)]:
            pool = []
            for p in baseline:
                delta, evidence = adjustment(features, p['team'], p['opponent'], strength)
                pool.append({**p, 'baseline_xpts': p['xpts'], 'xpts': round(max(.1, p['xpts'] * (1 + delta)), 3),
                             'adjustment_fraction': delta, 'football_data': evidence})
            solution = optimize(pool)
            if 'error' in solution:
                report['scenarios'][label] = {'error': solution['error']}
                continue
            report['scenarios'][label] = {
                'strength': strength, 'expected_points': solution['expected_points'],
                'formation': solution['formation'], 'captain': solution['captain']['name'],
                'starting_xi': solution['starting_xi'],
                'bench': [p for p in solution['squad'] if p['id'] not in
                          {q['id'] for q in solution['starting_xi']}],
                'top20': sorted(pool, key=lambda p: -p['xpts'])[:20],
                'top_positive': sorted(pool, key=lambda p: -(p['xpts'] - p['baseline_xpts']))[:20],
                'top_negative': sorted(pool, key=lambda p: p['xpts'] - p['baseline_xpts'])[:20],
                'feature_coverage': sum(p['football_data'] is not None for p in pool)}
            report['scenarios'][label]['frozen_squad_remaining'] = [
                {'id': p['id'], 'name': p['name'], 'baseline_xpts': p['baseline_xpts'],
                 'experimental_xpts': p['xpts']}
                for p in pool if p['id'] in frozen_ids]
        report['report_id'] = repo.save_generated_report('football_data_midweek_gw10', report)
        return report
    finally:
        engine.dispose()


if __name__ == '__main__':
    print(json.dumps(run(), ensure_ascii=True, indent=2))
