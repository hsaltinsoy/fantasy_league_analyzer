"""Append-only GW12 six-model capture with fresh official histories and frozen xG evidence."""
import copy
import hashlib
import json
import uuid
from datetime import datetime, timezone
from pathlib import Path

from analysis.live_benchmark import fetch_official_fixtures, _fixture_lookup, FIXTURE_ENDPOINT
from analysis.prediction_tracking import get_snapshot, get_prediction, save_snapshot, save_prediction_batch, _postgres, DEFAULT_DB
from analysis.capture_integrity import validate_inputs, digest
from analysis.history_freshness import audit, require_capture_ready
from analysis.six_model_batch import replay, NAMES
from data_sources.fixture_validation import validate_week
from data_sources.tff_official import BASE, fetch_players, fetch_player_histories
from storage.db import engine_from_env
from storage.football_data_repository import FootballDataRepository
from storage.repository import tracking_transaction

ORIGINAL = 'ceddd5ae-a154-411b-9581-31a484c87f5f'
OUT = Path('docs/phase29_gw12_capture.json')


def main():
    if OUT.exists():
        raise RuntimeError('Phase 29 capture artifact already exists; inspect before rerunning')
    engine = engine_from_env()
    original = get_snapshot(ORIGINAL)
    if original is None:
        raise RuntimeError('Original GW12 snapshot missing')
    original_hash = original['payload']['input_sha256']
    archive = fetch_official_fixtures(include_evidence=True)
    entry = archive['weeks']['12']
    raw_week = next(w for w in archive['raw_payload']['data']['gameweeks'] if w['order'] == 12)
    deadline = datetime.fromisoformat(entry['deadline'].replace('Z', '+00:00'))
    now = datetime.now(timezone.utc)
    if now >= deadline or (now-datetime.fromisoformat(archive['captured_utc'])).total_seconds() > 3600:
        raise RuntimeError('Official GW12 deadline passed or fixture evidence stale')
    if len(entry['matches']) != 9 or any(m['status'] != 'SCHEDULED' for m in entry['matches']):
        raise RuntimeError('GW12 fixture set incomplete or started')
    gw11 = next(w for w in archive['raw_payload']['data']['gameweeks'] if w['order']==11)
    if not (gw11.get('finished') and all(m.get('pointsAdded') and m.get('bonusesAdded') for m in gw11['matches'])
            and all(d.get('allPointsAdded') and d.get('allBonusesAdded') for d in gw11['matchDays'])):
        raise RuntimeError('GW11 fantasy results not marked complete')
    player_response = fetch_players(include_evidence=True)
    players = player_response['players']
    player_time = player_response['retrieved_at'].isoformat()
    quality = validate_week(entry, players)
    if quality['warnings']:
        raise RuntimeError(f'Official player/fixture quality warnings: {quality["warnings"]}')
    fetched = fetch_player_histories([p['id'] for p in players], completed_through=11,
        target_week=12, min_interval_seconds=.2, max_retries=2,
        continue_on_error=True, include_metrics=True)
    histories = fetched['rows_by_player']
    if fetched['metrics']['errors'] or len(histories) != len(players):
        raise RuntimeError('Incomplete history fetch')
    probe = {'source':'official_tff_history_api','retrieved_at':fetched['retrieved_at'],
        'source_url':fetched['source_url'],'gameweek':11,
        'available_player_ids':[pid for pid,h in histories.items() if any(int(r['gameweekOrder'])==11 for r in h)],
        'sampled_player_count':len(players),'status':'available'}
    freshness = audit(12, players, histories, archive, source_probe=probe)
    require_capture_ready(freshness)
    if len(probe['available_player_ids']) != len(players):
        raise RuntimeError('GW11 history row missing for one or more current players')
    external = FootballDataRepository(engine).matches_before(datetime.now(timezone.utc))
    external = json.loads(json.dumps(external, default=str))
    if not external:
        raise RuntimeError('No timestamped pre-cutoff external matches')
    from analysis.football_data_team_features import team_features
    features = team_features(external)
    fixture_clubs = set(_fixture_lookup(entry).keys())
    if not fixture_clubs <= set(features):
        raise RuntimeError('Missing external xG features for fixture clubs')
    rows = [{'player_id':p['id'],'rows':copy.deepcopy(histories[str(p['id'])])} for p in players]
    input_hash = validate_inputs(12, players, entry['matches'], rows)
    cutoff = datetime.now(timezone.utc)
    if cutoff >= deadline:
        raise RuntimeError('Deadline passed before replay')
    bundle = {'gameweek':12,'players':players,'fixtures':entry['matches'],'histories':rows,
        'cutoff_utc':cutoff.isoformat(),'deadline_at':entry['deadline'],
        'external_matches':external,'team_features':{},'fixture_date':None,'input_hash':input_hash}
    six = replay(bundle)
    if six['status'] != 'complete':
        raise RuntimeError(f'Six-model replay incomplete: {six["statuses"]}')
    source = {'players':'official_tff_player_api','players_retrieved_at':player_time,
        'fixtures':archive['source_url'],'fixtures_retrieved_at':archive['captured_utc'],
        'histories':'official_tff_history_api','histories_retrieved_at':fetched['retrieved_at'],
        'external_matches':'postgres_frozen_football_data','external_cutoff_utc':cutoff.isoformat(),
        'deadline_source_url':archive['source_url'],'deadline_retrieved_at':archive['captured_utc'],
        'official_gameweek_id':entry['gameweek_id']}
    with tracking_transaction(engine):
        saved_snapshot = save_snapshot(12, copy.deepcopy(players), copy.deepcopy(entry['matches']), rows,
            source, deadline_at=entry['deadline'], deadline_source=BASE+FIXTURE_ENDPOINT,
            require_pre_deadline=True, feature_evidence={'football_data_matches':external},
            data_quality={'fixture_validation':quality,'history_freshness':freshness})
        saved = save_prediction_batch(saved_snapshot['id'], list(six['predictions'].values()),
            model_version='phase29_v1', require_pre_deadline=True)
    frozen = get_snapshot(saved_snapshot['id'])
    replay_bundle = {**bundle,'players':frozen['payload']['players'],
        'fixtures':frozen['payload']['fixtures'],'histories':frozen['payload']['histories'],
        'external_matches':frozen['payload']['feature_evidence']['football_data_matches'],
        'cutoff_utc':frozen['captured_at']}
    verified = replay(replay_bundle)
    if verified['status'] != 'complete' or verified['batch_id'] != six['batch_id']:
        raise RuntimeError('Offline replay failed')
    checks = {}
    for name, saved_row in zip(NAMES, saved):
        actual = get_prediction(saved_row['id'])['payload']
        fresh = verified['predictions'][name]
        fields = ('formation','expected_fantasy_points','risk_adjusted_objective','cost','captain')
        checks[name] = all(actual[k] == fresh[k] for k in fields) and \
            {p['id'] for p in actual['starting_xi']} == {p['id'] for p in fresh['starting_xi']} and \
            {p['id'] for p in actual['bench']} == {p['id'] for p in fresh['bench']}
    if not all(checks.values()):
        raise RuntimeError(f'Offline replay mismatch: {checks}')
    if get_snapshot(ORIGINAL)['payload']['input_sha256'] != original_hash:
        raise RuntimeError('Original snapshot changed')
    report = {'snapshot_id':saved_snapshot['id'],'original_snapshot_id':ORIGINAL,
        'capture_timestamp':saved_snapshot['captured_at'],'status':saved_snapshot['status'],
        'deadline_at':entry['deadline'],'fixture_retrieved_at':archive['captured_utc'],
        'player_retrieved_at':player_time,'history_retrieved_at':fetched['retrieved_at'],
        'input_hash':input_hash,'batch_id':six['batch_id'],
        'snapshot_payload_sha256':frozen['payload']['input_sha256'],
        'external_matches_count':len(external),'external_digest':digest(external),
        'history_freshness':freshness,'history_metrics':fetched['metrics'],
        'prediction_ids':{name:row['id'] for name,row in zip(NAMES,saved)},
        'replay_checks':checks,
        'predictions':{name:{k:p[k] for k in ('formation','captain','cost','expected_fantasy_points','risk_adjusted_objective','starting_xi','bench')}
            for name,p in six['predictions'].items()}}
    OUT.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(OUT)


if __name__ == '__main__':
    main()
