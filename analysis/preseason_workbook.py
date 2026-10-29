"""Strict, read-only extraction of a public preseason workbook without Excel dependencies."""
import re
import unicodedata
import zipfile
from collections import Counter
from xml.etree import ElementTree as ET

NS = {'m': 'http://schemas.openxmlformats.org/spreadsheetml/2006/main'}


def normalized(value):
    text = str(value or '').replace('ı', 'i').replace('İ', 'I')
    text = ''.join(ch for ch in unicodedata.normalize('NFKD', text)
                   if not unicodedata.combining(ch))
    return re.sub('[^a-z0-9]', '', text.casefold())


def read_players(path):
    """The workbook has custom PLY IDs; they are never treated as TFF IDs."""
    with zipfile.ZipFile(path) as archive:
        root = ET.fromstring(archive.read('xl/worksheets/sheet1.xml'))
    entries = []
    for row in root.findall('.//m:sheetData/m:row', NS):
        cells = {}
        for cell in row.findall('m:c', NS):
            column = cell.get('r', '').rstrip('0123456789')
            value = cell.find('m:v', NS)
            cells[column] = (value.text if value is not None else
                             ''.join(part.text or '' for part in cell.findall('.//m:t', NS)))
        if not str(cells.get('A') or '').startswith('PLY'):
            continue
        position = str(cells.get('C') or '').split(' ', 1)[0]
        if position not in ('GK', 'DEF', 'MID', 'FWD') or not cells.get('B') or not cells.get('D'):
            continue
        entries.append({'workbook_id': cells['A'], 'name': cells['B'],
                        'position': position, 'club_name': cells['D'],
                        'preseason_price_tl': cells.get('F')})
    ids = [row['workbook_id'] for row in entries]
    if len(ids) != len(set(ids)):
        raise ValueError('Duplicate workbook player ID')
    return entries


def uniquely_named(rows, key):
    counts = Counter(normalized(row[key]) for row in rows)
    return {normalized(row[key]): row for row in rows
            if normalized(row[key]) and counts[normalized(row[key])] == 1}
