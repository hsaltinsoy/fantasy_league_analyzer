"""Import permitted exports of xgEdge-like season statistics; no site scraping."""
import csv
import io
import unicodedata


def key(value):
    return ''.join(c for c in unicodedata.normalize('NFKD', str(value).casefold()) if c.isalnum() and not unicodedata.combining(c))


def rows(text):
    reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    if not reader.fieldnames:
        raise ValueError('CSV has no header')
    return [{key(k): (v or '').strip() for k, v in r.items() if k} for r in reader]


def get(row, *aliases):
    for name in aliases:
        if row.get(key(name)) not in (None, ''):
            return row[key(name)]
    return None


def number(value, label, default=None):
    if value is None:
        return default
    try:
        return float(value.replace(',', '').replace('−', '-'))
    except ValueError as exc:
        raise ValueError(f'Invalid {label}: {value}') from exc


def merge(stat_text, price_text=None):
    prices = {}
    if price_text:
        for r in rows(price_text):
            name, team = get(r, 'name', 'player', 'oyuncu'), get(r, 'team', 'club', 'takim')
            price = number(get(r, 'price', 'fiyat'), 'price')
            position = get(r, 'position', 'pos', 'pozisyon')
            if name and team and price is not None and position:
                prices[(key(name), key(team))] = (price, position.upper())
    players = []
    for i, r in enumerate(rows(stat_text), 2):
        name, team = get(r, 'player', 'name', 'oyuncu'), get(r, 'club', 'team', 'takim')
        if not name or not team:
            raise ValueError(f'Row {i}: player/name and club/team required')
        minutes = number(get(r, 'min', 'minutes', 'mins'), 'minutes')
        goals = number(get(r, 'g', 'goals'), 'goals')
        assists = number(get(r, 'a', 'assists'), 'assists')
        xg = number(get(r, 'xg'), 'xG')
        xa = number(get(r, 'xa'), 'xA')
        price, fantasy_pos = prices.get((key(name), key(team)), (None, None))
        players.append({'name': name, 'team': team, 'minutes': minutes, 'goals': goals, 'assists': assists,
                        'xg': xg, 'xa': xa, 'price': price, 'position': fantasy_pos,
                        'status': 'ready' if price is not None and minutes is not None and goals is not None and assists is not None else 'incomplete',
                        'source': 'user_supplied_export'})
    return {'players': players, 'count': len(players), 'ready': sum(p['status']=='ready' for p in players),
            'warning': 'Season totals, not last-five-match form. Fantasy price/position must come from TFF export. Missing statistics are null, not zero.'}
