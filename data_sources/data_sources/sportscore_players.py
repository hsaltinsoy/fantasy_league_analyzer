"""SportScore documented public API adapter. Never invent unavailable statistics."""
import re
import requests
from data_sources.team_names import normalize_team

BASE = 'https://sportscore.com/api/widget'

class PlayerFeedError(Exception):
    pass

def _records(payload):
    if isinstance(payload, list):
        return payload
    if not isinstance(payload, dict):
        return []
    for key in ('players', 'topscorers', 'scorers', 'data', 'results', 'items'):
        value = payload.get(key)
        if isinstance(value, list):
            return value
        if isinstance(value, dict):
            nested = _records(value)
            if nested:
                return nested
    return []

def _number(value):
    try:
        return float(value) if value is not None and value != '' else None
    except (ValueError, TypeError):
        return None

def _label(value):
    return value.get('name') or value.get('title') or '' if isinstance(value, dict) else str(value or '')

def _player_id(record):
    obj = record.get('player') if isinstance(record.get('player'), dict) else record
    return str(obj.get('id') or obj.get('slug') or obj.get('name') or '')

def normalize_record(record, stat):
    obj = record.get('player') if isinstance(record.get('player'), dict) else record
    name = _label(obj) or _label(record.get('name'))
    team = _label(record.get('team') or obj.get('team') or record.get('club'))
    value = _number(record.get(stat))
    if value is None:
        value = _number(record.get('value'))
    if value is None and isinstance(record.get('statistics'), dict):
        value = _number(record['statistics'].get(stat))
    return {'source_id': _player_id(record), 'name': name, 'team': team,
            'goals' if stat == 'goals' else 'assists': value}

def fetch_players(competition_slug='super-lig', get=None):
    get = get or requests.get
    by_id = {}
    for stat in ('goals', 'assists'):
        try:
            response = get(f'{BASE}/topscorers/', params={'sport':'football','slug':competition_slug,
                       'limit':50,'stat':stat}, timeout=18)
            response.raise_for_status()
            payload = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise PlayerFeedError(f'SportScore {stat} endpoint unavailable: {exc}') from exc
        for item in _records(payload):
            if not isinstance(item, dict):
                continue
            row = normalize_record(item, stat)
            if not row['name']:
                continue
            key = row['source_id'] or (row['name'].casefold() + '|' + normalize_team(row['team']))
            existing = by_id.setdefault(key, {'source_id':key, 'name':row['name'], 'team':row['team'],
                                              'goals':None, 'assists':None})
            if row['team'] and not existing['team']:
                existing['team'] = row['team']
            existing[stat] = row[stat]
    players = list(by_id.values())
    return {'source':'SportScore', 'competition_slug':competition_slug,
            'players':players, 'count':len(players),
            'coverage':'Top-50 goals/assists lists only; NOT a complete squad or match-by-match player dataset.',
            'missing':['fantasy_price','fantasy_position','last5_minutes','last5_xg','last5_xa','starting_probability'],
            'warnings':(['No player rows returned. Confirm that this competition slug is supported by SportScore.']
                        if not players else ['Unlisted players are not necessarily on zero goals/assists. Missing statistics are null.'])}
