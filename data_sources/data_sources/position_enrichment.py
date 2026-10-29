"""Conservative optional player-profile position enrichment; no guessing."""
import re
import time
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
import requests
from bs4 import BeautifulSoup

POSITIONS = {
    'g':'GK', 'goalkeeper':'GK', 'keeper':'GK', 'kaleci':'GK', 'gk':'GK',
    'd':'DEF', 'defender':'DEF', 'defence':'DEF', 'defense':'DEF', 'defans':'DEF', 'def':'DEF',
    'centre-back':'DEF', 'center-back':'DEF', 'left-back':'DEF', 'right-back':'DEF',
    'm':'MID', 'midfielder':'MID', 'midfield':'MID', 'orta saha':'MID', 'mid':'MID',
    'central midfield':'MID', 'attacking midfield':'MID', 'defensive midfield':'MID',
    'f':'FWD', 'forward':'FWD', 'striker':'FWD', 'attacker':'FWD', 'santrfor':'FWD',
    'centre-forward':'FWD', 'center-forward':'FWD', 'left winger':'FWD', 'right winger':'FWD',
    'winger':'FWD', 'fwd':'FWD',
}

def classify(raw):
    value = re.sub(r'\s+', ' ', str(raw or '').strip().casefold())
    return POSITIONS.get(value)

def parse_profile_position(html):
    soup = BeautifulSoup(html, 'html.parser')
    # Explicit structured property is preferred to surrounding text.
    for el in soup.select('[itemprop="position"], [data-position], meta[name="position"], meta[property="athlete:position"]'):
        value = el.get('content') or el.get('data-position') or el.get_text(' ', strip=True)
        if classify(value):
            return classify(value)
    for el in soup.select('tr, dt, li'):
        text = el.get_text(' ', strip=True)
        match = re.fullmatch(r'(?:Position|Pozisyon)\s*[:：]?\s*(.{2,40})', text, re.I)
        if match and classify(match.group(1)):
            return classify(match.group(1))
        if el.name == 'dt' and text.casefold() in ('position', 'pozisyon'):
            sibling = el.find_next_sibling('dd')
            if sibling and classify(sibling.get_text(' ', strip=True)):
                return classify(sibling.get_text(' ', strip=True))
    return None

def enrich(players, *, session=None, max_profiles=60, delay=1.0):
    """Check only player-specific xgEdge profiles; do not bypass access controls.

    Bounded to avoid hundreds of requests; returns diagnostics for unresolved players.
    """
    session = session or requests.Session()
    headers = {'User-Agent':'TFFFantasyOptimizer/1.2 (personal research)'}
    try:
        robots_response = session.get('https://www.xg-edge.com/robots.txt', timeout=12, headers=headers)
    except requests.RequestException:
        return {'players':players, 'resolved':0, 'checked':0, 'warning':'Profil kaynağına ulaşılamadı; mevcut oyuncu verileri korundu.'}
    if robots_response.status_code != 200:
        return {'players':players, 'resolved':0, 'checked':0, 'warning':'Profil erişim kuralları doğrulanamadı; pozisyon taraması yapılmadı.'}
    robots = RobotFileParser()
    robots.parse(robots_response.text.splitlines())
    resolved = checked = eligible = 0
    failures = 0
    for player in players:
        if classify(player.get('provider_position')):
            player['provider_position'] = classify(player['provider_position'])
            resolved += 1
            continue
        url = player.get('profile_url')
        if not url:
            continue
        parsed = urlparse(url)
        if parsed.scheme != 'https' or parsed.netloc not in ('www.xg-edge.com','xg-edge.com') or not parsed.path.startswith('/players/'):
            continue
        if not robots.can_fetch(headers['User-Agent'], url):
            continue
        eligible += 1
        if checked >= max_profiles:
            continue
        try:
            response = session.get(url, timeout=12, headers=headers)
            if response.status_code in (401,403,429):
                break
            checked += 1
            if response.status_code != 200:
                failures += 1
                continue
            position = parse_profile_position(response.text)
            if position:
                player['provider_position'] = position
                player['position_source'] = 'xgEdge_profile'
                resolved += 1
            if delay:
                time.sleep(max(1.0,delay))
        except requests.RequestException:
            checked += 1
            failures += 1
            continue
    return {'players':players, 'resolved':resolved, 'checked':checked, 'eligible_profiles':eligible, 'failed_requests':failures,
            'warning':f'Profil bağlantısı bulunan: {eligible}; kontrol edilen: {checked}; çözümlenen: {resolved}. Kaynakta pozisyon alanı yoksa boş kalır.'}
