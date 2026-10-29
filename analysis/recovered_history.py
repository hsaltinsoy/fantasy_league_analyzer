"""Build auditable retrospective player-week evidence from official archives."""
import argparse
import hashlib
import json
from collections import Counter, defaultdict
from datetime import datetime, timezone
from pathlib import Path

from data_sources.historical_recovery import OUTPUT
from data_sources.team_of_week import parse as parse_dream
from analysis.player_level_walkforward import _fixture_teams
from analysis.preseason_workbook import normalized, read_players, uniquely_named

STORE = Path('historical_data')
POSITIONS = {'GK', 'DEF', 'MID', 'FWD'}
PLAYER_HISTORY_URL = 'https://tfffantezilig.com/api/backend/projection/stats/players/{player_id}/history?league-id=1'
THIRD_PARTY_URL = 'https://github.com/holashawty/tfffantezilig/blob/f1368196/oyuncu_veritabani.xlsx'


def _read_verified(output, manifest, label):
    entry = manifest['entries'][label]
    path = Path(output) / entry['relative_path']
    raw = path.read_bytes()
    if hashlib.sha256(raw).hexdigest() != entry['sha256']:
        raise ValueError(f'Raw source digest mismatch: {label}')
    return json.loads(raw)


def _persist_content(output, subdir, label, payload):
    raw = json.dumps(payload, ensure_ascii=False, sort_keys=True, indent=2).encode('utf-8')
    digest = hashlib.sha256(raw).hexdigest()
    path = Path(output) / subdir / f'{label}_{digest[:16]}.json'
    path.parent.mkdir(parents=True, exist_ok=True)
    if not path.exists():
        path.write_bytes(raw)
    return {'path': str(path.relative_to(output)).replace('\\', '/'), 'sha256': digest}


def build(store=STORE, output=OUTPUT):
    store, output = Path(store), Path(output)
    manifest = json.loads((output / 'official_collection_manifest.json').read_text(encoding='utf-8'))
    current = _read_verified(output, manifest, 'player_stats_current')
    current_rows = current.get('data') or []
    if not isinstance(current_rows, list):
        raise ValueError('Current official roster response is malformed')
    current_by_id = {str(row['playerId']): row for row in current_rows if isinstance(row, dict)
                     and isinstance(row.get('playerId'), int)}
    if len(current_by_id) != len(current_rows):
        raise ValueError('Duplicate current official player ID')
    fixture_raw = _read_verified(output, manifest, 'fixtures_current')
    fixture_weeks = {int(entry['order']): entry for entry in fixture_raw['data']['gameweeks']
                     if isinstance(entry, dict) and isinstance(entry.get('order'), int)}
    dream = {}
    for week in range(1, 10):
        label = f'dream_team_gw{week}'
        if label not in manifest['entries']:
            continue
        dream[week] = parse_dream(_read_verified(output, manifest, label), week)
        if dream[week]['source_gameweek_id'] != fixture_weeks[week]['id']:
            raise ValueError(f'GW{week}: dream-team and fixture IDs disagree')
    observed = defaultdict(list)
    for week, entry in sorted(dream.items()):
        for player in entry['players']:
            pid, position = str(player['player_id']), player['position']
            if position not in POSITIONS or player.get('club_id') is None:
                continue
            observed[pid].append({'effective_gameweek': week, 'position': position,
                'club_id': player['club_id'], 'source_url': manifest['entries'][f'dream_team_gw{week}']['url'],
                'retrieved_at': manifest['entries'][f'dream_team_gw{week}']['retrieved_at'],
                'quality': 'official_historical_dream_team_retrospective_not_predeadline_verified'})
    official_dream_team_ids = len(observed)
    records = {}
    for path in store.glob('player_*.json'):
        pid = path.stem.removeprefix('player_')
        if pid.isdigit():
            value = json.loads(path.read_text(encoding='utf-8'))
            records[pid] = value if isinstance(value, list) else []
    workbook = output / 'raw' / 'third_party' / 'oyuncu_veritabani_f1368196.xlsx'
    workbook_matches = {}
    workbook_exclusions = Counter()
    if workbook.exists() and 'clubs_current' in manifest['entries']:
        clubs_raw = _read_verified(output, manifest, 'clubs_current')
        club_names = {str(row['id']): normalized(row.get('name')) for row in clubs_raw.get('data', [])
                      if isinstance(row, dict) and row.get('id') is not None}
        first_week_teams = _fixture_teams({'matches': fixture_weeks[1]['matches']})
        current_names = uniquely_named([dict(row, full_name=' '.join(filter(None,
                         (row.get('name'), row.get('surname'))))) for row in current_rows], 'full_name')
        workbook_rows = read_players(workbook)
        unique_workbook = uniquely_named(workbook_rows, 'name')
        for row in workbook_rows:
            key = normalized(row['name'])
            if key not in unique_workbook:
                workbook_exclusions['duplicate_workbook_name'] += 1
                continue
            current_player = current_names.get(key)
            if current_player is None:
                workbook_exclusions['missing_or_duplicate_tff_name'] += 1
                continue
            pid = str(current_player['playerId'])
            target = [r for r in records.get(pid, []) if isinstance(r, dict)
                      and r.get('gameweekOrder') == 1]
            if len(target) != 1:
                workbook_exclusions['missing_gw1_identity_check'] += 1
                continue
            club = first_week_teams.get((str(target[0].get('opponentClubId')),
                                         target[0].get('homeAway'))) if first_week_teams else None
            if club is None or normalized(row['club_name']) != club_names.get(str(club)):
                workbook_exclusions['club_name_mismatch'] += 1
                continue
            if pid in workbook_matches:
                workbook_exclusions['duplicate_tff_player_id'] += 1
                continue
            workbook_matches[pid] = row
            observed[pid].insert(0, {'effective_gameweek': 0,
                'position': row['position'], 'club_id': club,
                'source_url': THIRD_PARTY_URL,
                'retrieved_at': datetime.fromtimestamp(workbook.stat().st_mtime, timezone.utc).isoformat(),
                'claimed_commit_date': '2026-08-12T21:05:41Z',
                'quality': 'third_party_preseason_workbook_unique_name_and_gw1_club_corrob_unverified_push_time'})
    position_conflicts = {pid: sorted({r['position'] for r in rows}) for pid, rows in observed.items()
                          if len({r['position'] for r in rows}) > 1}
    current_disagreements = [pid for pid, rows in observed.items() if pid in current_by_id and
                             current_by_id[pid].get('position') not in {r['position'] for r in rows}]
    snapshots, coverage, by_club = {}, [], defaultdict(list)
    for week in range(1, 10):
        fixture = fixture_weeks.get(week)
        if not fixture:
            raise ValueError(f'GW{week}: official fixture entry missing')
        fixture_entry = {'matches': fixture.get('matches') or []}
        teams = _fixture_teams(fixture_entry)
        if teams is None:
            raise ValueError(f'GW{week}: fixture identity or completion invalid')
        rows = []
        counts = Counter()
        for pid, history in sorted(records.items(), key=lambda item: int(item[0])):
            target = [row for row in history if isinstance(row, dict) and row.get('gameweekOrder') == week]
            if len(target) != 1:
                counts['missing_or_duplicate_result'] += 1
                continue
            row = target[0]
            prior = [r for r in observed.get(pid, []) if r['effective_gameweek'] < week]
            positions = {r['position'] for r in prior}
            prior_evidence = prior[-1] if len(positions) == 1 else None
            if prior_evidence:
                counts['prior_position_any'] += 1
                counts['prior_official_position' if prior_evidence['quality'].startswith('official_')
                       else 'prior_workbook_position'] += 1
            elif len(positions) > 1:
                counts['prior_position_conflict'] += 1
            club = teams.get((str(row.get('opponentClubId')), row.get('homeAway')))
            if club is not None:
                counts['postmatch_club_inferred'] += 1
                by_club[pid].append((week, club))
            price = row.get('cost')
            if isinstance(price, (int, float)) and not isinstance(price, bool) and price > 0:
                counts['positive_postmatch_price'] += 1
            else:
                price = None
            rows.append({'player_id': int(pid),
                'position_for_prediction': prior_evidence['position'] if prior_evidence else None,
                'position_observed_gameweek': prior_evidence['effective_gameweek'] if prior_evidence else None,
                'position_source_url': prior_evidence['source_url'] if prior_evidence else None,
                'position_retrieved_at': prior_evidence['retrieved_at'] if prior_evidence else None,
                'position_quality': prior_evidence['quality'] if prior_evidence else 'unavailable',
                'club_id_postmatch': club,
                'club_quality': 'postmatch_result_and_official_fixture_inference' if club else 'unavailable',
                'price_postmatch': price,
                'price_quality': 'official_player_history_postmatch_not_deadline_price' if price is not None else 'unavailable',
                'availability_at_deadline': None, 'eligibility_at_deadline': None,
                'player_history_url': PLAYER_HISTORY_URL.format(player_id=pid)})
        payload = {'gameweek': week, 'classification': 'retrospective_reconstruction_not_predeadline_verified',
            'official_gameweek_id': fixture['id'], 'official_deadline': fixture.get('deadline'),
            'deadline_timezone': 'UTC' if str(fixture.get('deadline') or '').endswith('Z') else 'offset_or_unknown',
            'deadline_source_url': manifest['entries']['fixtures_current']['url'],
            'deadline_retrieved_at': manifest['entries']['fixtures_current']['retrieved_at'],
            'players': rows, 'missing_fields': ['availability_at_deadline', 'eligibility_at_deadline',
                                               'deadline_price', 'complete_predeadline_position_pool']}
        snapshots[str(week)] = _persist_content(output, 'snapshots', f'gw{week}', payload)
        coverage.append({'gameweek': week, 'historical_player_results': len(rows),
            'prior_position_any': counts['prior_position_any'],
            'prior_official_position': counts['prior_official_position'],
            'prior_workbook_position': counts['prior_workbook_position'],
            'prior_position_conflict': counts['prior_position_conflict'],
            'postmatch_club_inferred': counts['postmatch_club_inferred'],
            'positive_postmatch_price': counts['positive_postmatch_price'],
            'deadline_availability': 0, 'deadline_eligibility': 0,
            'deadline_price_verified': 0, 'official_fixtures': len(fixture_entry['matches']),
            'official_deadline': fixture.get('deadline'),
            'full_xi_feasible': False,
            'classification': 'retrospective_reconstruction_not_predeadline_verified'})
    transfers = {pid: [{'from_week': earlier[0], 'to_week': later[0],
                        'from_club_id': earlier[1], 'to_club_id': later[1]}
                       for earlier, later in zip(values, values[1:]) if earlier[1] != later[1]]
                 for pid, values in by_club.items()}
    transfers = {pid: changes for pid, changes in transfers.items() if changes}
    position_file = _persist_content(output, 'derived', 'position_evidence',
        {'classification': 'official_historical_dream_team_retrospective_not_predeadline_verified',
         'players': observed, 'conflicts': position_conflicts,
         'current_position_disagreements': current_disagreements,
         'source_manifest': 'official_collection_manifest.json'})
    transfer_file = _persist_content(output, 'derived', 'transfer_events',
        {'classification': 'postmatch_club_inference_not_predeadline_roster',
         'events': transfers})
    report = {'classification': 'retrospective_recovery_audit', 'generated_at':
              datetime.now(timezone.utc).isoformat(), 'sources': {
                  'official_manifest': 'official_collection_manifest.json',
                  'third_party_workbook': {'url': THIRD_PARTY_URL,
                      'commit_date': '2026-08-12T21:05:41Z',
                      'local_file_observed_at': (datetime.fromtimestamp(workbook.stat().st_mtime, timezone.utc).isoformat()
                                                 if workbook.exists() else None),
                      'sha256': hashlib.sha256(workbook.read_bytes()).hexdigest() if workbook.exists() else None,
                      'quality': 'lower-confidence position evidence only after unique-name and official GW1 club corroboration; PLY IDs are not TFF IDs'}},
              'position_unique_player_ids': len(observed),
              'official_dream_team_unique_ids': official_dream_team_ids,
              'preseason_workbook_matched_ids': len(workbook_matches),
              'preseason_workbook_exclusions': dict(workbook_exclusions),
              'position_conflicts': position_conflicts,
              'current_position_disagreements': current_disagreements,
              'transfer_player_count': len(transfers), 'transfer_events': sum(map(len, transfers.values())),
              'weeks': coverage, 'snapshots': snapshots,
              'position_evidence': position_file, 'transfer_evidence': transfer_file,
              'limitations': ['Prior-week dream-team membership selects players with earlier strong outcomes; sample is not representative.',
                              'Dream-team retrieval occurred after GW1-GW9 deadlines; position use is retrospective only.',
                              'The public workbook commit author date does not independently prove when its contents were pushed.',
                              'Third-party workbook mapping uses unique normalized names and official GW1 club corroboration; identity remains weaker than stable-ID matching.',
                              'Postmatch club and price fields must not be used as deadline-time lineup inputs.',
                              'No official historical injury, suspension or complete eligibility snapshots were recovered.']}
    (output / 'coverage_report.json').write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    return report


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Derive retrospective GW1-GW9 TFF evidence')
    parser.add_argument('--store', type=Path, default=STORE)
    parser.add_argument('--output', type=Path, default=OUTPUT)
    args = parser.parse_args()
    result = build(args.store, args.output)
    print(json.dumps({'position_ids': result['position_unique_player_ids'],
                      'position_conflicts': len(result['position_conflicts']),
                      'transfer_players': result['transfer_player_count'],
                      'weeks': result['weeks']}, indent=2))
