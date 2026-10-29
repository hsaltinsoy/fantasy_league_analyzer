"""Database-side quality and source-to-row reconciliation for Phase 18."""
import argparse
import json
import re
from collections import Counter

from sqlalchemy import select, func

from storage.db import engine_from_env
from storage import models as m
from storage.normalize_history import artifact, parsed, digest, HISTORY, ROOT, RECOVERED


def report(engine):
    with engine.connect() as db:
        tables = (m.teams, m.players, m.gameweeks, m.fixtures, m.match_results,
                  m.player_gameweek_stats, m.player_state, m.player_identity_mappings,
                  m.identity_reviews, m.fixture_observations, m.stat_observations,
                  m.source_payloads, m.source_artifacts)
        counts = {table.name: db.execute(select(func.count()).select_from(table)).scalar_one()
                  for table in tables}
        stats = [dict(row) for row in db.execute(select(m.player_gameweek_stats)).mappings()]
        state = [dict(row) for row in db.execute(select(m.player_state)).mappings()]
        identity = Counter(row[0] for row in db.execute(select(m.player_identity_mappings.c.provider)))
        duplicates = db.execute(select(func.count()).select_from(
            select(m.player_gameweek_stats.c.player_id,
                   m.player_gameweek_stats.c.gameweek_id,
                   m.player_gameweek_stats.c.fixture_id)
            .group_by(m.player_gameweek_stats.c.player_id,
                      m.player_gameweek_stats.c.gameweek_id,
                      m.player_gameweek_stats.c.fixture_id)
            .having(func.count() > 1).subquery())).scalar_one()
        source_hashes = db.execute(select(m.source_artifacts.c.content_sha256,
                                          func.count().label('n'))
                                   .group_by(m.source_artifacts.c.content_sha256)
                                   .having(func.count() > 1)).all()
        position_coverage = {}
        for week in range(1, 10):
            observed = {row['player_id'] for row in state if row['position'] is not None
                        and row['effective_gameweek'] is not None
                        and row['effective_gameweek'] < week}
            position_coverage[str(week)] = {
                'retrospective_prior_position_players': len(observed),
                'missing_from_572_player_roster': counts['players'] - len(observed),
                'independently_predeadline_verified': 0}
        provenance_missing = {
            'fixtures': db.execute(select(func.count()).select_from(m.fixtures).where(
                m.fixtures.c.source_payload_id.is_(None))).scalar_one(),
            'player_gameweek_stats': db.execute(select(func.count()).select_from(m.player_gameweek_stats).where(
                m.player_gameweek_stats.c.source_payload_id.is_(None))).scalar_one(),
            'player_state': db.execute(select(func.count()).select_from(m.player_state).where(
                m.player_state.c.source_payload_id.is_(None))).scalar_one(),
        }
        position_tiers = dict(Counter(row['evidence_quality'] for row in state
            if row['metadata'].get('state_kind') == 'position_evidence'))
    return {'counts': counts, 'identity_provider_counts': dict(identity),
            'unresolved_external_identity_reviews': counts['identity_reviews'],
            'position_coverage_by_target_week': position_coverage,
            'position_evidence_tiers': position_tiers,
            'postmatch_price_observations': sum(row['price'] is not None and
                row['metadata'].get('state_kind') == 'postmatch_history' for row in state),
            'historical_deadline_price_verified': 0,
            'historical_deadline_availability_verified': 0,
            'explicit_zero_minute_results': sum(row['minutes'] == 0 for row in stats),
            'missing_points_in_observed_results': sum(row['fantasy_points'] is None for row in stats),
            'xg_xa_measurements_imported': 0,
            'rows_without_source_payload': provenance_missing,
            'duplicate_player_week_fixture_rows': duplicates,
            'identical_content_across_artifact_paths': len(source_hashes),
            'classification': 'retrospective_historical_normalization_not_predeadline_verified'}


def reconcile(engine):
    """Compare staged source-row hashes with normalized roster, fixtures and history."""
    missing, mismatched = [], []
    with engine.connect() as db:
        artifacts = db.execute(select(m.source_artifacts).where(
            m.source_artifacts.c.source_path.like(ROOT + 'player_%.json'))).mappings().all()
        expected = {}
        for row in artifacts:
            if not HISTORY.fullmatch(row['source_path']):
                continue
            pid = HISTORY.fullmatch(row['source_path']).group(1)
            for index, item in enumerate(parsed(row)):
                expected[(pid, item.get('gameweekOrder'))] = digest(item)
        observed = {(row['player_id'], row['gameweek_id']): row['metadata'].get('source_row_sha256')
                    for row in db.execute(select(m.stat_observations)).mappings()}
        for key, expected_hash in expected.items():
            if key not in observed:
                missing.append(key)
            elif observed[key] != expected_hash:
                mismatched.append(key)
        extra = sorted(set(observed) - set(expected))
        manifest = parsed(artifact(db, RECOVERED + 'official_collection_manifest.json'))
        expected_core = {}
        for label, table, id_field in (
            ('clubs_current', m.teams, 'id'),
            ('player_stats_current', m.players, 'playerId')):
            entry = manifest['entries'][label]
            source = artifact(db, RECOVERED + entry['relative_path'], entry['sha256'])
            expected_rows = {str(item[id_field]): digest(item) for item in parsed(source)['data']}
            actual_rows = {row['id']: row['metadata'].get('source_row_sha256')
                           for row in db.execute(select(table)).mappings()}
            expected_core[label] = {'source': len(expected_rows), 'destination': len(actual_rows),
                'missing': sorted(set(expected_rows) - set(actual_rows)),
                'mismatched': sorted(key for key in expected_rows.keys() & actual_rows.keys()
                                     if expected_rows[key] != actual_rows[key]),
                'extra': sorted(set(actual_rows) - set(expected_rows))}
        entry = manifest['entries']['fixtures_current']
        official_source = artifact(db, RECOVERED + entry['relative_path'], entry['sha256'])
        official_expected = {f'official:{item["id"]}:{entry["sha256"][:16]}': digest(item)
            for week in parsed(official_source)['data']['gameweeks'] for item in week['matches']}
        local_source = artifact(db, ROOT + 'tff_fixtures_verified_v5.json')
        local_payload_id = digest(local_source['source_path'] + ':' + local_source['content_sha256'])
        local_expected = {f'local:{item["id"]}:{local_payload_id[:16]}': digest(item)
            for week in parsed(local_source)['weeks'].values() for item in week['matches']}
        fixture_expected = official_expected | local_expected
        fixture_actual = {row['id']: row['metadata'].get('source_row_sha256')
                          for row in db.execute(select(m.fixture_observations)).mappings()}
        fixture_check = {'source': len(fixture_expected), 'destination': len(fixture_actual),
            'missing': sorted(set(fixture_expected) - set(fixture_actual)),
            'mismatched': sorted(key for key in fixture_expected.keys() & fixture_actual.keys()
                                 if fixture_expected[key] != fixture_actual[key]),
            'extra': sorted(set(fixture_actual) - set(fixture_expected))}
    core_issues = any(value['missing'] or value['mismatched'] or value['extra']
                      for value in (*expected_core.values(), fixture_check))
    return {'status': 'passed' if not (missing or mismatched or extra or core_issues) else 'failed',
            'source_player_week_rows': len(expected), 'normalized_observations': len(observed),
            'missing': missing, 'mismatched': mismatched, 'extra': extra,
            'core': expected_core, 'fixture_observations': fixture_check}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('action', choices=('report', 'reconcile'))
    args = parser.parse_args()
    engine = engine_from_env()
    try:
        result = report(engine) if args.action == 'report' else reconcile(engine)
        print(json.dumps(result, indent=2, default=str))
        if result.get('status') == 'failed':
            raise SystemExit(2)
    finally:
        engine.dispose()


if __name__ == '__main__':
    main()
