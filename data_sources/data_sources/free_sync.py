"""Keyless personal-use match feed; missing statistics are never fabricated."""
import csv
import io
from datetime import date, datetime, timedelta
import requests
from analysis.fixture_difficulty import calculate
from data_sources.team_names import normalize_team
from collections import Counter
from data_sources.fixture_supplement import supplement

BASE = 'https://raw.githubusercontent.com/oladeeayo/open-matchday/master/data/TUR_1_super-lig'

class FeedError(Exception):
    pass

def _read_csv(url, get=requests.get):
    try:
        response = get(url, timeout=18, headers={'User-Agent': 'PersonalFantasyOptimizer/0.6'})
        response.raise_for_status()
        rows = list(csv.DictReader(io.StringIO(response.content.decode('utf-8-sig'))))
        if not rows or not {'date', 'home', 'away'}.issubset(rows[0]):
            raise FeedError('Kaynak dosya boş veya beklenmeyen CSV formatında')
        return rows
    except requests.RequestException as e:
        raise FeedError(f'Kaynağa erişilemedi: {e}') from e

def sync(today=None, get=requests.get):
    today = today or date.today()
    season_start = today.year if today.month >= 7 else today.year - 1
    season = f'{season_start % 100:02d}{(season_start + 1) % 100:02d}'
    result_rows = _read_csv(f'{BASE}/results_{season}.csv', get)
    fixture_rows = _read_csv(f'{BASE}/fixtures_{season}.csv', get)
    finished = []
    for r in result_rows:
        try:
            match_date = date.fromisoformat(r['date'][:10])
            if match_date >= today:
                continue
            finished.append({'date': match_date.isoformat(), 'home': r['home'], 'away': r['away'],
                             'home_goals': int(r['ft_home']), 'away_goals': int(r['ft_away'])})
        except (ValueError, KeyError, TypeError):
            continue
    future = []
    for r in fixture_rows:
        try:
            match_date = date.fromisoformat(r['date'][:10])
            if match_date >= today and r['home'] and r['away']:
                future.append({'date': match_date.isoformat(), 'home': r['home'], 'away': r['away'],
                               'gw': r.get('gw')})
        except (ValueError, KeyError, TypeError):
            continue
    future.sort(key=lambda f: f['date'])
    if not future:
        raise FeedError('Gelecek fikstür bulunamadı. Kaynağın sezon kapsamını kontrol edin.')
    first = date.fromisoformat(future[0]['date'])
    # Prefer provider gameweek if available, otherwise group first 7 days.
    gw = future[0].get('gw')
    # Skip an almost-completed round (e.g. Monday's remaining fixtures).
    if gw and sum(f.get('gw') == gw for f in future) < 5 and any(
        r.get('gw') == gw and r.get('date', '')[:10] == today.isoformat() for r in fixture_rows):
        later = next((f.get('gw') for f in future if f.get('gw') != gw), None)
        if later:
            gw = later
    selected = [f for f in future if (f.get('gw') == gw if gw else
                date.fromisoformat(f['date']) < first + timedelta(days=7))]
    if len(selected) > 12 or not selected:
        selected = [f for f in future if date.fromisoformat(f['date']) < first + timedelta(days=7)]
    selected, supplement_warnings = supplement(selected, season, get)
    team_matches = Counter()
    for match in finished:
        team_matches[normalize_team(match['home'])] += 1
        team_matches[normalize_team(match['away'])] += 1
    return {'team_matches': dict(team_matches), 'source': 'open-matchday', 'season': season, 'matches_loaded': len(finished),
            'fixtures': calculate(finished, selected, as_of=today),
            'fixture_count': len(selected), 'players': [],
            'warnings': supplement_warnings + ['Oyuncu istatistikleri ve TFF Fantasy fiyatları bu kaynaktan gelmez.',
                         'FDR yalnızca son 5 maç ve ev/deplasman etkisine dayanan geçici bir ölçümdür.',
                         'Kaynak: github.com/oladeeayo/open-matchday (kişisel, ticari olmayan kullanım).']}
