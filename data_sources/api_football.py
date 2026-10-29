"""API-FOOTBALL adapter; no key is stored in source control."""
import os
import requests

BASE = 'https://v3.football.api-sports.io'

class APIError(RuntimeError):
    pass

class APIFootball:
    def __init__(self, key=None, session=None):
        self.key = key or os.getenv('API_FOOTBALL_KEY', '')
        if not self.key:
            raise APIError('API_FOOTBALL_KEY eksik. .env.example dosyasına bakın.')
        self.session = session or requests.Session()

    def get(self, endpoint, **params):
        try:
            response = self.session.get(f'{BASE}/{endpoint}', params=params,
                headers={'x-apisports-key': self.key}, timeout=25)
            response.raise_for_status()
            body = response.json()
        except (requests.RequestException, ValueError) as exc:
            raise APIError(f'API bağlantısı başarısız: {exc}') from exc
        if body.get('errors'):
            raise APIError(f'API hatası: {body["errors"]}')
        return body

    def league(self, season=2026):
        data = self.get('leagues', country='Turkey', name='Super Lig', season=season)
        rows = data.get('response', [])
        if not rows:
            raise APIError('Bu sezon için Süper Lig bulunamadı. Ücretsiz planda güncel sezon erişimi olmayabilir.')
        return rows[0]

    def fixtures(self, league_id, season):
        return self.get('fixtures', league=league_id, season=season)['response']

    def players(self, league_id, season, max_pages=30):
        output = []
        for page in range(1, max_pages + 1):
            data = self.get('players', league=league_id, season=season, page=page)
            output.extend(data.get('response', []))
            if page >= data.get('paging', {}).get('total', 1):
                break
        return output
