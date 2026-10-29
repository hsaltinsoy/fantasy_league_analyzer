"""Normalize common Turkish and Football-Data club naming differences."""
import re
import unicodedata

ALIASES = {
    'corum fk':'corum', 'arca corum fk':'corum', 'corumspor':'corum', 'corum':'corum',
    'erzurumspor':'erzurumspor', 'erzurumspor fk':'erzurumspor', 'erzurumspor futbol kulubu':'erzurumspor',
    'galatasaray':'galatasaray', 'fenerbahce':'fenerbahce',
    'besiktas':'besiktas', 'besiktas jk':'besiktas',
    'trabzonspor':'trabzonspor', 'trabzon':'trabzonspor',
    'basaksehir':'basaksehir', 'basaksehir fk':'basaksehir', 'istanbul basaksehir':'basaksehir', 'istanbul basaksehir fk':'basaksehir', 'buyuksehir belediye erzurumspor':'erzurumspor',
    'gaziantep':'gaziantep', 'gaziantep fk':'gaziantep',
    'goztepe':'goztepe', 'goztepe sk':'goztepe',
    'kasimpasa':'kasimpasa', 'kasimpasa sk':'kasimpasa',
    'antalyaspor':'antalyaspor', 'antalyaspor as':'antalyaspor',
    'samsunspor':'samsunspor', 'samsun':'samsunspor',
    'konyaspor':'konyaspor', 'konya':'konyaspor',
    'kayserispor':'kayserispor', 'kayseri':'kayserispor',
    'alanyaspor':'alanyaspor', 'alanya':'alanyaspor',
    'rizespor':'rizespor', 'caykur rizespor':'rizespor', 'rizespor':'rizespor',
    'eyupspor':'eyupspor', 'eyup':'eyupspor',
    'genclerbirligi':'genclerbirligi', 'genclerbirligi sk':'genclerbirligi',
    'fatih karagumruk':'karagumruk', 'karagumruk':'karagumruk',
    'kocaelispor':'kocaelispor', 'kocaeli':'kocaelispor',
    'amed sportif faaliyetler':'amedspor', 'amedspor':'amedspor',
}

def normalize_team(name):
    value = str(name or '').strip().casefold().replace('ı', 'i')
    value = ''.join(c for c in unicodedata.normalize('NFKD', value) if not unicodedata.combining(c))
    value = re.sub(r'[^a-z0-9]+', ' ', value).strip()
    return ALIASES.get(value, value)
