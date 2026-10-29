"""Small, source-attributed position cross-check from publicly displayed examples.

Not a scraper or a complete player feed. Values are deliberately scoped to
unambiguous full-name + club matches and are not presented as an official TFF API.
"""
from data_sources.team_names import normalize_team

# Positions cross-checked against the Fantasy Super Lig public landing page
# on 2026-10-27; NOT guaranteed to remain current.
VERIFIED = {
    ('eldor shomurodov', 'basaksehir'): 'FWD',
    ('gift orban', 'amedspor'): 'FWD',
    ('adrian benedyczak', 'kasimpasa'): 'FWD',
}

def verified_position(name, team):
    return VERIFIED.get((str(name or '').strip().casefold(), normalize_team(team)))
