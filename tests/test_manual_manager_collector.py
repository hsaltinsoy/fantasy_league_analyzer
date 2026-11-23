import json
import uuid
from datetime import datetime, timezone

import pytest

from analysis.manual_manager_collector import catalogue, dashboard, export_csv, read_records, safe_export_rows, save_record, validate


def players():
    positions = ['GK'] * 2 + ['DEF'] * 5 + ['MID'] * 5 + ['FWD'] * 3
    return {i + 1: {'id': i + 1, 'name': f'Player {i+1}', 'position': p, 'club': str(i % 5)}
            for i, p in enumerate(positions)}


def payload():
    return {'gameweek': 12, 'manager_key': str(uuid.uuid4()), 'rank_at_capture': 7,
            'rank_basis_gameweek': 11,
            'starting_xi_ids': [1, 3, 4, 5, 8, 9, 10, 11, 13, 14, 15],
            'bench_ids': [2, 6, 7, 12], 'captain_id': 13, 'vice_captain_id': 8,
            'formation': '3-4-3', 'captured_at_utc': '2026-11-10T12:00:00Z',
            'deadline_at_utc': '2026-11-15T12:00:00Z',
            'observation_kind': 'retrospective_screenshot', 'manager_card': 'unknown',
            'provenance_note': 'Manually transcribed from UI'}


def test_validation_rejects_missing_duplicate_and_wrong_captain():
    p = payload()
    assert validate(p, players())['formation'] == '3-4-3'
    p['starting_xi_ids'][0] = 999
    with pytest.raises(ValueError, match='Unknown'):
        validate(p, players())
    p = payload()
    p['bench_ids'][0] = p['starting_xi_ids'][0]
    with pytest.raises(ValueError, match='distinct'):
        validate(p, players())
    p = payload()
    p['captain_id'] = 2
    with pytest.raises(ValueError, match='captain'):
        validate(p, players())


def test_attack_card_allows_extra_xi_shape_but_not_different_squad_distribution():
    p = payload()
    p['starting_xi_ids'] = [1, 3, 4, 8, 9, 10, 11, 12, 13, 14, 15]
    p['bench_ids'] = [2, 5, 6, 7]
    p['formation'] = '2-5-3'
    p['manager_card'] = 'attack'
    with pytest.raises(ValueError, match='Confirm the displayed squad'):
        validate(p, players())
    p['attack_rules_unverified_confirmed'] = True
    result = validate(p, players())
    assert result['formation'] == '2-5-3'
    assert result['manager_card'] == 'attack'
    assert result['rules_status'] == 'rules_unverified'
    assert not result['feature_eligible']
    p['manager_card'] = 'none'
    with pytest.raises(ValueError, match='formation invalid'):
        validate(p, players())
    p['manager_card'] = 'attack'
    bad_players = players()
    bad_players[15]['position'] = 'MID'
    p['formation'] = '2-6-2'
    observed = validate(p, bad_players)
    assert observed['rules_status'] == 'rules_unverified'
    assert observed['position_counts'] == {'GK': 2, 'DEF': 5, 'MID': 6, 'FWD': 2}


def test_attack_card_observed_two_three_five_five_stays_unverified():
    pool = players()
    pool[6]['position'] = 'FWD'
    pool[7]['position'] = 'FWD'
    p = payload()
    p.update(starting_xi_ids=[1, 3, 4, 8, 9, 10, 13, 14, 15, 6, 7],
             bench_ids=[2, 5, 11, 12], formation='2-3-5', manager_card='attack',
             observation_kind='pre_deadline_observed')
    with pytest.raises(ValueError, match='rules are undocumented'):
        validate(p, pool, now=datetime(2026, 11, 12, tzinfo=timezone.utc))
    p['attack_rules_unverified_confirmed'] = True
    row = validate(p, pool, now=datetime(2026, 11, 12, tzinfo=timezone.utc))
    assert row['position_counts'] == {'GK': 2, 'DEF': 3, 'MID': 5, 'FWD': 5}
    assert row['rules_status'] == 'rules_unverified'
    assert row['attack_rules_unverified_confirmed']
    assert not row['feature_eligible']
    p['starting_xi_ids'][0] = 3
    with pytest.raises(ValueError, match='distinct'):
        validate(p, pool)
    p['starting_xi_ids'][0] = 1
    p['captain_id'] = 2
    with pytest.raises(ValueError, match='captain'):
        validate(p, pool)
    p['captain_id'] = 13
    p['bench_ids'][0] = 999
    with pytest.raises(ValueError, match='Unknown'):
        validate(p, pool)


def test_legacy_attack_records_are_not_exported_as_feature_eligible():
    old = {'gameweek': 11, 'manager_card': 'attack', 'feature_eligible': True,
           'starting_xi_ids': list(range(1, 12)), 'bench_ids': [12, 13, 14, 15],
           'captain_id': 1, 'rank_at_capture': 1, 'manager_key': 'legacy'}
    exported = safe_export_rows([old])
    assert exported[0]['rules_status'] == 'rules_unverified'
    assert not exported[0]['feature_eligible']
    assert old['feature_eligible']  # source record is preserved
    report = dashboard([old], players(), week=11)
    assert report['rules_unverified_count'] == 1
    assert report['pre_deadline_count'] == 0
    assert report['weekly_comparisons'] == []


def test_postdeadline_manual_receipt_cannot_be_feature_eligible():
    p = payload()
    p['observation_kind'] = 'pre_deadline_observed'
    late = validate(p, players(), now=datetime(2026, 11, 16, tzinfo=timezone.utc))
    early = validate(p, players(), now=datetime(2026, 11, 12, tzinfo=timezone.utc))
    assert not late['feature_eligible']
    assert early['feature_eligible']


def test_isolated_store_export_and_consensus(tmp_path):
    path = tmp_path / 'manager_squads.json'
    record = validate(payload(), players())
    save_record(record, path)
    assert len(read_records(path)) == 1
    with pytest.raises(ValueError, match='already'):
        save_record(record, path)
    report = dashboard(read_records(path), players(), week=12)
    assert report['tiers']['10']['manager_weeks'] == 1
    assert report['tiers']['10']['captains'][0]['id'] == 13
    assert 'manager_key' in export_csv(read_records(path))


def test_flask_preview_save_export(tmp_path):
    from app import create_app
    app = create_app()
    app.config['TESTING'] = True
    app.config['MANAGER_COLLECTOR_STORE'] = tmp_path / 'squads.json'
    client = app.test_client()
    assert client.get('/manager-collector').status_code == 200
    assert client.get('/manager-collector', environ_overrides={'REMOTE_ADDR': '192.0.2.10'}).status_code == 403
    # Route validates against the project's local official-ID catalogue.
    from analysis.manual_manager_collector import catalogue
    real = catalogue()
    by_position = {pos: [p['id'] for p in real.values() if p['position'] == pos][:n]
                   for pos, n in [('GK', 2), ('DEF', 5), ('MID', 5), ('FWD', 3)]}
    p = payload()
    p['starting_xi_ids'] = by_position['GK'][:1] + by_position['DEF'][:3] + by_position['MID'][:4] + by_position['FWD']
    p['bench_ids'] = by_position['GK'][1:] + by_position['DEF'][3:] + by_position['MID'][4:]
    p['captain_id'] = by_position['FWD'][0]
    p['vice_captain_id'] = by_position['MID'][0]
    assert client.post('/api/manager-collector/preview', json=p).status_code == 200
    assert client.post('/api/manager-collector/save', json=p).status_code == 400
    assert client.post('/api/manager-collector/save', json={**p, 'confirmed': True}).status_code == 201
    exported = json.loads(client.get('/api/manager-collector/export.json').data)
    assert len(exported) == 1
    assert exported[0]['manager_key'] == p['manager_key']
    assert client.get('/api/manager-collector/dashboard?week=12').json['tiers']['10']['manager_weeks'] == 1


def test_archived_gw11_comparison_uses_xi_plus_captain_only():
    from pathlib import Path
    human = json.loads(Path('docs/phase33b_human_vs_ai.json').read_text(encoding='utf-8'))
    p = payload()
    p.update(gameweek=11, rank_basis_gameweek=10, starting_xi_ids=human['xi_ids'],
             bench_ids=human['bench_ids'], captain_id=human['captain_id'],
             vice_captain_id=human['vice_captain_id'], captured_at_utc='2026-11-10T12:00:00Z')
    row = validate(p, catalogue())
    comparison = dashboard([row], catalogue(), week=11)['weekly_comparisons'][0]
    assert comparison['xi_plus_captain_actual'] == 100
    assert comparison['optimizer_xi_plus_captain_actual'] == 70
    assert not comparison['feature_eligible']
