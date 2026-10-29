"""Transform API responses into the application's existing analysis inputs."""
from datetime import datetime, timezone
from data_sources.api_football import APIFootball, APIError
from analysis.fixture_difficulty import calculate
from analysis.player_prediction import predict


def sync(season=2026, include_players=False, client=None):
    client = client or APIFootball()
    league = client.league(season)
    league_id = league['league']['id']
    coverage = league.get('seasons', [{}])[-1].get('coverage', {})
    fixtures = client.fixtures(league_id, season)
    now = datetime.now(timezone.utc)
    finished, upcoming = [], []
    for f in fixtures:
        home, away = f['teams']['home']['name'], f['teams']['away']['name']
        date = f['fixture']['date'][:10]
        status = f['fixture']['status']['short']
        if status in ('FT', 'AET', 'PEN') and f['goals']['home'] is not None and f['goals']['away'] is not None:
            finished.append({'date': date, 'home': home, 'away': away,
                             'home_goals': f['goals']['home'], 'away_goals': f['goals']['away']})
        elif status in ('NS', 'TBD') and datetime.fromisoformat(f['fixture']['date'].replace('Z', '+00:00')) >= now:
            upcoming.append({'date': date, 'home': home, 'away': away})
    upcoming.sort(key=lambda f: f['date'])
    if not upcoming:
        raise APIError('Gelecek maç bulunamadı; API sezon erişimini kontrol edin.')
    start = datetime.fromisoformat(upcoming[0]['date']).date()
    from datetime import date
    matchweek = [f for f in upcoming if (date.fromisoformat(f['date']) - start).days <= 6]
    analysis = calculate(finished, matchweek)
    result = {'league_id': league_id, 'season': season, 'fixtures': analysis,
              'matches_loaded': len(finished), 'coverage': coverage,
              'warnings': ['FDR geçici bir form modelidir; resmî fantasy tahmini değildir.']}
    if include_players:
        raw = client.players(league_id, season)
        players = []
        for record in raw:
            player = record.get('player', {})
            stats = next((s for s in record.get('statistics', []) if s.get('league', {}).get('id') == league_id), None)
            if not stats:
                continue
            games = stats.get('games', {})
            goals = stats.get('goals', {})
            shots = stats.get('shots', {})
            players.append({'id': player.get('id'), 'name': player.get('name'),
                            'team': stats['team']['name'], 'position': games.get('position'),
                            'appearances': games.get('appearences') or 0,
                            'minutes': games.get('minutes') or 0,
                            'goals': goals.get('total') or 0, 'assists': goals.get('assists') or 0,
                            'shots_on_target': shots.get('on') or 0,
                            'price': None, 'expected_points': None,
                            'data_status': 'fantasy_price_missing'})
        result['players'] = players
        result['warnings'].append('Oyuncu fiyatları API-FOOTBALL üzerinden gelmez; gerçek fantasy fiyatları olmadan kadro optimize edilmez.')
    return result
