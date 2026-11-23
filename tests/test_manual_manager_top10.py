import json
import uuid

import pytest

from analysis.manual_manager_collector import (catalogue, preview_named_batch, read_records, resolve_name,
                                               save_batch, validate_named_batch)


def batch(players):
    by_pos = {pos: [p for p in players.values() if p['position'] == pos][:n]
              for pos, n in [('GK', 2), ('DEF', 5), ('MID', 5), ('FWD', 3)]}
    xi = by_pos['GK'][:1] + by_pos['DEF'][:3] + by_pos['MID'][:4] + by_pos['FWD']
    bench = by_pos['GK'][1:] + by_pos['DEF'][3:] + by_pos['MID'][4:]
    return [dict(gameweek=12, manager_key=str(uuid.uuid4()), rank_at_capture=rank,
                 rank_basis_gameweek=11, starting_xi_names=[p['label'] for p in xi],
                 bench_names=[p['label'] for p in bench], captain_name=xi[-1]['label'],
                 vice_captain_name=xi[-2]['label'], formation='3-4-3',
                 captured_at_utc='2026-11-10T12:00:00Z',
                 deadline_at_utc='2026-11-15T12:00:00Z',
                 observation_kind='retrospective_screenshot', manager_card='unknown',
                 provenance_note='Manual transcription', weekly_points=70 + rank)
            for rank in range(1, 11)]


def test_exact_name_resolution_and_ambiguity():
    players = catalogue()
    sample = next(iter(players.values()))
    assert resolve_name(sample['label'], players) == sample['id']
    assert resolve_name(sample['name'], players) == sample['id']
    duplicates = {1: {'id': 1, 'name': 'Same Name', 'match_name': '', 'label': 'Same Name (ID 1)'},
                  2: {'id': 2, 'name': 'Same Name', 'match_name': '', 'label': 'Same Name (ID 2)'}}
    with pytest.raises(ValueError, match='Ambiguous'):
        resolve_name('Same Name', duplicates)


def test_batch_rejects_missing_name_before_any_save(tmp_path):
    players = catalogue()
    items = batch(players)
    items[7]['bench_names'][2] = 'Unknown Footballer'
    with pytest.raises(ValueError, match='Manager 8'):
        validate_named_batch(items, players)
    assert read_records(tmp_path / 'squads.json') == []


def test_batch_preview_preserves_attack_card_and_all_player_ids():
    players = catalogue()
    items = batch(players)
    manager = items[0]
    manager['starting_xi_names'][3], manager['bench_names'][-1] = (
        manager['bench_names'][-1], manager['starting_xi_names'][3])
    manager['formation'] = '2-5-3'
    manager['manager_card'] = 'attack'
    manager['attack_rules_unverified_confirmed'] = True
    records = validate_named_batch(items, players)
    assert records[0]['manager_card'] == 'attack'
    assert records[0]['formation'] == '2-5-3'
    assert records[0]['rules_status'] == 'rules_unverified'
    assert len(set(records[0]['starting_xi_ids'] + records[0]['bench_ids'])) == 15
    assert records[0]['captain_id'] in records[0]['starting_xi_ids']


def test_preview_requires_confirmation_without_hiding_other_nine_squads():
    players = catalogue()
    items = batch(players)
    manager = items[0]
    manager['starting_xi_names'][3], manager['bench_names'][-1] = (
        manager['bench_names'][-1], manager['starting_xi_names'][3])
    manager['formation'] = '2-5-3'
    manager['manager_card'] = 'attack'
    preview = preview_named_batch(items, players)
    assert not preview['can_save']
    assert preview['managers'][0]['status'] == 'needs_confirmation'
    assert preview['managers'][0]['record']['manual_confirmation'] is False
    assert all(r['status'] == 'valid' for r in preview['managers'][1:])
    manager['attack_rules_unverified_confirmed'] = True
    assert preview_named_batch(items, players)['can_save']


def test_preview_reports_manager_and_field_for_hard_failures():
    players = catalogue()
    items = batch(players)
    items[0]['starting_xi_names'][0] = ''
    items[1]['bench_names'][0] = items[1]['starting_xi_names'][0]
    items[2]['captain_name'] = items[2]['bench_names'][0]
    preview = preview_named_batch(items, players)
    assert not preview['can_save']
    assert len(preview['managers']) == 10
    assert 'Starting XI slot 1' in preview['managers'][0]['message']
    assert 'starting_xi_ids/bench_ids' in preview['managers'][1]['message']
    assert 'captain_id/vice_captain_id' in preview['managers'][2]['message']
    assert all(r['status'] == 'invalid' for r in preview['managers'][:3])


def test_confirmed_batch_is_atomic_and_reuses_experimental_store(tmp_path):
    players = catalogue()
    records = validate_named_batch(batch(players), players)
    path = tmp_path / 'squads.json'
    save_batch(records, path)
    saved = read_records(path)
    assert len(saved) == 10
    assert saved[0]['weekly_points_displayed'] == 71
    assert all(not r['feature_eligible'] for r in saved)
    with pytest.raises(ValueError, match='already'):
        save_batch(records, path)
    assert len(read_records(path)) == 10


def test_top10_flask_preview_and_confirm(tmp_path):
    from app import create_app
    app = create_app()
    app.config.update(TESTING=True, MANAGER_COLLECTOR_STORE=tmp_path / 'squads.json')
    client = app.test_client()
    items = batch(catalogue())
    assert client.get('/manager-collector/top10').status_code == 200
    preview = client.post('/api/manager-collector/top10/preview', json={'managers': items})
    assert preview.status_code == 200
    assert len(preview.json['records']) == 10
    assert client.post('/api/manager-collector/top10/save', json={'managers': items}).status_code == 400
    assert client.post('/api/manager-collector/top10/save', json={'managers': items, 'confirmed': True}).status_code == 201
    assert len(json.loads(client.get('/api/manager-collector/export.json').data)) == 10
    dashboard = client.get('/api/manager-collector/dashboard?week=12').json
    assert dashboard['tiers']['10']['manager_weeks'] == 10
    assert dashboard['tiers']['10']['players'][0]['share'] == 1


def test_mixed_standard_and_confirmed_attack_batch_saves(tmp_path):
    from app import create_app
    app = create_app()
    app.config.update(TESTING=True, MANAGER_COLLECTOR_STORE=tmp_path / 'mixed.json')
    client = app.test_client()
    items = batch(catalogue())
    attack = items[0]
    attack['starting_xi_names'][3], attack['bench_names'][-1] = (
        attack['bench_names'][-1], attack['starting_xi_names'][3])
    attack['formation'] = '2-5-3'
    attack['manager_card'] = 'attack'
    initial = client.post('/api/manager-collector/top10/preview', json={'managers': items}).json
    assert not initial['can_save']
    assert initial['managers'][0]['status'] == 'needs_confirmation'
    stale = client.post('/api/manager-collector/top10/save', json={'managers': items, 'confirmed': True})
    assert stale.status_code == 409
    assert 'outdated' in stale.json['error']
    assert read_records(tmp_path / 'mixed.json') == []
    attack['attack_rules_unverified_confirmed'] = True
    preview = client.post('/api/manager-collector/top10/preview', json={'managers': items}).json
    assert preview['can_save']
    # Simulate a stale editable form: the explicit preview checkbox still authorizes this manager.
    attack['attack_rules_unverified_confirmed'] = False
    assert client.post('/api/manager-collector/top10/save', json={
        'managers': items, 'manual_confirmed_manager_keys': [attack['manager_key']],
        'confirmed': True}).status_code == 201
    saved = read_records(tmp_path / 'mixed.json')
    assert len(saved) == 10
    assert saved[0]['rules_status'] == 'rules_unverified'
    assert saved[0]['validation_status'] == 'rules_unverified'
    assert saved[0]['manual_confirmation'] is True
    assert saved[0]['manager_card'] == 'attack'
    assert all(r['rules_status'] == 'standard_rules_verified' for r in saved[1:])
