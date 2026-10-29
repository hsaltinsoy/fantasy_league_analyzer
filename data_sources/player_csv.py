"""Import user-supplied player statistics; no FotMob automated retrieval."""
import csv
import io

REQUIRED = {'name', 'team', 'position', 'price', 'minutes_last5', 'goals_last5', 'assists_last5'}

def parse_players(text):
    reader = csv.DictReader(io.StringIO(text.lstrip('\ufeff')))
    if not reader.fieldnames or not REQUIRED.issubset(set(reader.fieldnames)):
        raise ValueError('Player CSV missing columns: ' + ', '.join(sorted(REQUIRED - set(reader.fieldnames or []))))
    players = []
    for number, row in enumerate(reader, 2):
        try:
            item = {'name': row['name'].strip(), 'team': row['team'].strip(), 'position': row['position'].strip().upper(), 'price': float(row['price']), 'minutes_last5': float(row['minutes_last5']), 'goals_last5': float(row['goals_last5']), 'assists_last5': float(row['assists_last5'])}
            for key in ('xg_last5', 'xa_last5'):
                item[key] = float(row[key]) if row.get(key) not in (None, '') else None
            if not item['name'] or not item['team'] or item['price'] <= 0 or item['minutes_last5'] < 0 or item['position'] not in {'GK','DEF','MID','FWD'}:
                raise ValueError('invalid name/team/position/price/minutes')
            players.append(item)
        except (TypeError, ValueError) as exc:
            raise ValueError(f'Invalid player CSV row {number}: {exc}') from exc
    return players
