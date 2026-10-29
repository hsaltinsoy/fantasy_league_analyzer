"""Read xgEdge's labelled season-total table, refusing ambiguous data.

No guessed offsets: a changed table layout must fail rather than silently
mislabel statistics. The live website is not accessible from this build host.
"""
import re
import time
from urllib.parse import urljoin, urlparse
from urllib.robotparser import RobotFileParser

import requests
from bs4 import BeautifulSoup

BASE = 'https://www.xg-edge.com'
PATH = '/super-lig/players'
AGENT = 'TFFFantasyOptimizer/1.0 (personal research)'

class PlayerFeedError(Exception):
    pass


def _key(s):
    return re.sub(r'[^a-z0-9]', '', s.casefold())


def _number(value, field, name, optional=False):
    raw = value.strip().replace('\u00a0', '').replace(',', '')
    if raw in ('', '-', '—', 'N/A', 'n/a', '–', 'null'):
        if optional:
            return None
        raise PlayerFeedError(f'{name}: {field} eksik; yanlış veri göstermemek için durduruldu.')
    try:
        number = float(raw)
    except ValueError as exc:
        raise PlayerFeedError(f'{name}: {field} sayı değil: {value!r}') from exc
    if not 0 <= number <= 100000:
        raise PlayerFeedError(f'{name}: {field} aralık dışında: {number}')
    return number


def parse_page(html):
    soup = BeautifulSoup(html, 'html.parser')
    table = next((t for t in soup.select('table') if t.select_one('thead') and
                  'player' in _key(t.select_one('thead').get_text(' ', strip=True)) and
                  'xg' in _key(t.select_one('thead').get_text(' ', strip=True))), None)
    if table is None:
        raise PlayerFeedError('Oyuncu istatistik tablosu bulunamadı.')

    header_rows = table.select('thead tr')
    # Multiple header rows/merged headers are ambiguous: do not shift columns.
    if len(header_rows) != 1 or any(int(h.get('colspan', 1)) != 1 or int(h.get('rowspan', 1)) != 1
                                    for h in header_rows[0].find_all(['th', 'td'], recursive=False)):
        raise PlayerFeedError('Birleştirilmiş/çok satırlı tablo başlığı var; güvenli sütun eşleştirmesi yapılamıyor.')
    headers = [_key(h.get_text(' ', strip=True)) for h in header_rows[0].find_all(['th', 'td'], recursive=False)]
    aliases = {
        'name': ('player', 'playername'), 'team': ('club', 'team'),
        'minutes': ('minutes', 'mins', 'min', 'minutesplayed'),
        'goals': ('goals', 'g'), 'assists': ('assists', 'a'),
        'xg': ('xg', 'expectedgoals'), 'xa': ('xa', 'expectedassists'),
        'provider_position': ('pos', 'position'),
    }
    columns = {}
    for field, choices in aliases.items():
        matches = [i for i, h in enumerate(headers) if h in choices]
        if len(matches) > 1:
            raise PlayerFeedError(f'{field} sütunu birden fazla kez bulunuyor: {headers}')
        columns[field] = matches[0] if matches else None
    mandatory = ('name', 'team', 'minutes', 'goals', 'assists')
    missing = [f for f in mandatory if columns[f] is None]
    if missing:
        raise PlayerFeedError(f'Sezon toplamı sütunları eksik: {missing}; bulunan başlıklar: {headers}. Per-90 veya maç sayısı değerleri kullanılmaz.')

    output = []
    for tr in table.select('tbody tr'):
        cells = tr.find_all(['td', 'th'], recursive=False)
        if not cells:
            continue
        if len(cells) != len(headers) or any(int(c.get('colspan', 1)) != 1 for c in cells):
            raise PlayerFeedError(f'Satırda {len(cells)} hücre, başlıkta {len(headers)} sütun var; veri kaydedilmedi.')
        def cell(field):
            idx = columns[field]
            return cells[idx] if idx is not None else None
        def value(field):
            el = cell(field)
            return el.get_text(' ', strip=True) if el is not None else None
        name = value('name')
        team = value('team')
        if not name or not team:
            raise PlayerFeedError('Oyuncu veya takım adı boş; veri kaydedilmedi.')
        # Links are a cross-check, not a reason to shift numeric columns.
        player_link = tr.select_one('a[href^="/players/"]')
        team_link = tr.select_one('a[href^="/super-lig/"]')
        if player_link is not None and player_link not in [cell('name'), *cell('name').descendants]:
            raise PlayerFeedError(f'{name}: oyuncu linki Player sütununda değil.')
        if team_link is not None and team_link not in [cell('team'), *cell('team').descendants]:
            raise PlayerFeedError(f'{name}: takım linki Club/Team sütununda değil.')
        if _key(name) == _key(team):
            raise PlayerFeedError('Oyuncu adı takım adıyla aynı görünüyor; veri kaydedilmedi.')
        nums = {f: _number(value(f), f, name) for f in ('minutes','goals','assists')}
        nums['xg'] = _number(value('xg') or '', 'xg', name, optional=True)
        nums['xa'] = _number(value('xa') or '', 'xa', name, optional=True)
        if not nums['minutes'].is_integer() or not nums['goals'].is_integer() or not nums['assists'].is_integer():
            raise PlayerFeedError(f'{name}: dakika/gol/asist tam sayı değil; sütun kayması veya oran istatistiği olabilir.')
        if nums['minutes'] < 0 or nums['minutes'] > 4500 or nums['goals'] > 50 or nums['assists'] > 50:
            raise PlayerFeedError(f'{name}: sezon toplamları mantıksız; veri kaydedilmedi.')
        if nums['goals'] > nums['minutes'] / 10 + 1 or nums['assists'] > nums['minutes'] / 10 + 1:
            raise PlayerFeedError(f'{name}: dakika ile gol/asist uyumsuz; sütun kayması olabilir.')
        # If a matches/appearances column exists, minutes cannot be less than
        # the number of games played (helps catch 8 matches misread as minutes).
        games_idx = next((i for i, h in enumerate(headers) if h in ('apps','appearances','matches','mp','played')), None)
        if games_idx is not None:
            games = _number(cells[games_idx].get_text(' ', strip=True), 'matches', name)
            if nums['minutes'] < games or (games >= 3 and nums['minutes'] < games * 5):
                raise PlayerFeedError(f'{name}: dakika ({nums["minutes"]}) maç sayısıyla ({games}) uyumsuz.')
        output.append({
            'name': name, 'team': team,
            **{f: int(nums[f]) if f in ('minutes','goals','assists') else nums[f] for f in nums},
            'provider_position': value('provider_position'),
            'profile_url': urljoin(BASE, player_link.get('href')) if player_link is not None else None,
            'price': None, 'position': None,
            'status': 'missing_fantasy_price_and_position',
            'missing_stats': [f for f in ('xg', 'xa') if nums[f] is None],
            'source': 'xgEdge_season_totals',
        })
    return output, soup


def fetch_players(max_pages=9, delay=1.5, session=None):
    if not 1 <= max_pages <= 12:
        raise ValueError('max_pages must be 1..12')
    session = session or requests.Session()
    try:
        rr = session.get(BASE + '/robots.txt', timeout=12, headers={'User-Agent': AGENT})
        if rr.status_code != 200:
            raise PlayerFeedError('robots.txt doğrulanamadı; işlem durduruldu.')
        robots = RobotFileParser()
        robots.parse(rr.text.splitlines())
        if not robots.can_fetch(AGENT, BASE + PATH):
            raise PlayerFeedError('robots.txt otomatik erişime izin vermiyor.')
        players_by_key, visited = {}, set()
        truncated = False
        url = BASE + PATH
        for page in range(max_pages):
            if url in visited or not robots.can_fetch(AGENT, url):
                break
            visited.add(url)
            response = session.get(url, timeout=20, headers={'User-Agent': AGENT, 'Accept': 'text/html'})
            if response.status_code in (401, 403, 429):
                raise PlayerFeedError(f'Site erişimi sınırladı (HTTP {response.status_code}).')
            response.raise_for_status()
            batch, soup = parse_page(response.text)
            if not batch:
                raise PlayerFeedError('Oyuncu tablosu boş; eksik veri kaydedilmedi.')
            for p in batch:
                players_by_key[(p['name'].casefold(), p['team'].casefold())] = p
            next_link = soup.select_one('a[rel="next"]')
            if next_link is None:
                next_link = next((a for a in soup.select('a[href]') if a.get_text(' ', strip=True).lower() in ('next','next →','sonraki','›')), None)
            if next_link is None:
                break
            if page == max_pages - 1:
                truncated = True
                break
            candidate = urljoin(url, next_link.get('href', ''))
            if urlparse(candidate).netloc not in ('www.xg-edge.com', 'xg-edge.com') or not urlparse(candidate).path.startswith(PATH):
                break
            url = candidate
            if page < max_pages - 1:
                time.sleep(max(delay, 1.0))
        missing_xg = sum(p['xg'] is None for p in players_by_key.values())
        missing_xa = sum(p['xa'] is None for p in players_by_key.values())
        return {'players': list(players_by_key.values()), 'count': len(players_by_key),
                'missing_xg_count': missing_xg, 'missing_xa_count': missing_xa,
                'pages_fetched': len(visited), 'truncated': truncated,
                'warning': 'Eksik xG/xA değerleri null olarak bırakılır; sıfır kabul edilmez. Sezon toplamlarıdır. Canlı site HTML yapısı bu ortamda doğrulanamadı.'}
    except requests.RequestException as exc:
        raise PlayerFeedError(f'xgEdge bağlantı hatası: {exc}') from exc
