"""Read-only frozen production comparison with uncalibrated team features."""
import argparse
import json
from datetime import datetime, timezone

from analysis.football_data_team_features import team_features, fixture_features
from analysis.live_benchmark import next_gameweek, _fixture_lookup
from analysis.predict_next_week import predict, build_candidate_pool
from analysis.prediction_tracking import parse_time
from sqlalchemy import select
from storage import models as m
from storage.db import engine_from_env
from storage.football_data_repository import FootballDataRepository
from storage.runtime_repository import RuntimeRepository


def compare(engine, cutoff):
    if cutoff.tzinfo is None:
        raise ValueError('Timezone-aware cutoff required')
    runtime = RuntimeRepository(engine)
    with engine.connect() as db:
        player_retrieved = db.execute(select(m.source_payloads.c.retrieved_at).where(
            m.source_payloads.c.evidence_quality == 'current_official_api',
            m.source_payloads.c.id.like('tff-current-%')).order_by(
            m.source_payloads.c.retrieved_at.desc()).limit(1)).scalar_one_or_none()
    if player_retrieved is None or player_retrieved > cutoff:
        raise ValueError('Current player pool was not available at the requested cutoff')
    archive = runtime.fixture_archive()
    archive_retrieved = parse_time(archive.get('captured_utc'))
    if archive_retrieved is None or archive_retrieved > cutoff:
        raise ValueError('Official fixture evidence was not available at the requested cutoff')
    week, entry = next_gameweek(archive, cutoff)
    deadline = parse_time(entry.get('deadline'))
    if deadline is None or cutoff >= deadline:
        raise ValueError('Prediction cutoff must precede the official deadline')
    players = runtime.current_player_pool()
    histories = runtime.historical_records(before_week=week)
    with engine.connect() as db:
        staged_paths = set(db.execute(select(m.source_artifacts.c.source_path).where(
            m.source_artifacts.c.imported_at <= cutoff,
            m.source_artifacts.c.source_path.like('historical_data/player_%.json'))).scalars())
    unstaged = [pid for pid in histories
                if f'historical_data/player_{pid}.json' not in staged_paths]
    if unstaged:
        raise ValueError(f'{len(unstaged)} player histories were not staged by cutoff')
    records = [(player, histories.get(str(player['id']), [])) for player in players]
    fixtures = {week: _fixture_lookup(entry)}
    baseline = predict(week, players, records, fixtures, {}, fixture_archive=archive)
    pool, _ = build_candidate_pool(week, players, records, fixtures)
    external = FootballDataRepository(engine)
    matches = external.matches_before(cutoff)
    features = team_features(matches)
    coverage = sum(fixture_features(features, player['team'], player['opponent']) is not None
                   for player in baseline['starting_xi'])
    # No calibrated player-point coefficients exist for this new source. The
    # experimental run carries features while retaining production xPts exactly.
    experimental = predict(week, players, records, fixtures, {}, fixture_archive=archive)
    if _summary(baseline) != _summary(experimental):
        raise AssertionError('Frozen production rerun changed unexpectedly')
    player_features = {str(p['id']): fixture_features(features, p['team'], p['opponent'])
                       for p in pool}
    return {
        'cutoff': cutoff.isoformat(), 'gameweek': week,
        'configuration': {'team_feature_weight': 0.0,
                          'status': 'uncalibrated_features_only'},
        'history_evidence_quality': 'staged_before_prospective_cutoff_original_retrieval_unknown',
        'external_matches_before_cutoff': len(matches),
        'source_hashes': sorted({row['import_id'].removeprefix('football-data:')
                                 for row in matches}),
        'teams_with_features': len(features),
        'starting_xi_feature_coverage': coverage,
        'eligible_player_feature_coverage': sum(value is not None
                                                 for value in player_features.values()),
        'production': _summary(baseline), 'experimental': _summary(experimental),
        'candidate_feature_sets': {
            'team_xg': ['xg_for', 'xg_against'],
            'team_form': ['last3_points', 'last5_points'],
            'combined': ['last5_xg_for', 'last5_points',
                         'opponent_defensive_xg_conceded'],
        },
        'coefficient_status': 'not_estimated_no_valid_predeadline_player_training_snapshots',
        'player_predictions': {str(p['id']): {'baseline_xpts': p['xpts'],
                                             'experimental_xpts': p['xpts'],
                                             'features': player_features[str(p['id'])]}
                               for p in pool},
        'actual_fantasy_point_comparison': None,
        'limitation': 'No calibrated weights or chronological pre-deadline validation; '
                      'team features do not modify expected points.',
    }


def _summary(result):
    return {'expected_points': result['expected_points'], 'formation': result['formation'],
            'captain': result['captain'], 'cost': result['cost'],
            'squad_ids': sorted([p['id'] for p in result['starting_xi'] + result['bench']]),
            'starting_xi': [{'id': p['id'], 'name': p['name'], 'xpts': p['xpts']}
                            for p in result['starting_xi']],
            'bench': [{'id': p['id'], 'name': p['name'], 'xpts': p['xpts']}
                      for p in result['bench']]}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--cutoff', help='Timezone-aware ISO cutoff; defaults to now')
    args = parser.parse_args()
    cutoff = parse_time(args.cutoff) if args.cutoff else datetime.now(timezone.utc)
    if cutoff is None:
        parser.error('--cutoff requires a timezone')
    engine = engine_from_env()
    try:
        report = compare(engine, cutoff)
        report['report_id'] = RuntimeRepository(engine).save_generated_report(
            'football_data_comparison', report)
        print(json.dumps(report, ensure_ascii=True, indent=2))
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
