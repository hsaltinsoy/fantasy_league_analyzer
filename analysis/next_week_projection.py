"""Exploratory next-match projections using season totals, not official TFF scoring.

Unknown minutes/xG/xA remain missing; no synthetic replacement statistics.
"""
from data_sources.team_names import normalize_team
from data_sources.fantasy_position_reference import verified_position

GOAL_POINTS = {'GK': 6, 'DEF': 6, 'MID': 5, 'FWD': 4}

# Confirmed exception from user feedback; match both name and club.
# Do not treat provider positions as official fantasy classifications.
POSITION_OVERRIDES = {('eldor shomurodov', 'basaksehir'): 'FWD'}
POSITION_MAP = {
    'g': 'GK', 'gk': 'GK', 'goalkeeper': 'GK', 'keeper': 'GK',
    'd': 'DEF', 'df': 'DEF', 'def': 'DEF', 'defender': 'DEF', 'defence': 'DEF', 'defense': 'DEF',
    'm': 'MID', 'mf': 'MID', 'mid': 'MID', 'midfielder': 'MID', 'midfield': 'MID',
    'f': 'FWD', 'fw': 'FWD', 'fwd': 'FWD', 'forward': 'FWD', 'striker': 'FWD', 'attacker': 'FWD',
}


def project(players, fixtures, team_matches):
    by_team = {normalize_team(f['team']): f for f in fixtures}
    fixture_teams = set(by_team)
    output = []
    for p in players:
        row = dict(p)
        team = normalize_team(p.get('team'))
        fixture = by_team.get(team)
        n = team_matches.get(team, 0)
        raw_pos = str(p.get('provider_position') or '').strip().lower()
        verified = verified_position(p.get('name'), p.get('team'))
        override = POSITION_OVERRIDES.get((str(p.get('name') or '').strip().casefold(), team))
        provider_pos = POSITION_MAP.get(raw_pos)
        official = str(p.get('official_position') or '').upper()
        pos = official if official in GOAL_POINTS else verified or override or provider_pos
        row['position_source'] = ('tff_official' if official in GOAL_POINTS else 'public_fantasy_reference_2026_10_27' if verified else
                                  'user_confirmed_override' if override else
                                  'xgedge_provider' if provider_pos else None)
        row['position_conflict'] = bool(verified and provider_pos and verified != provider_pos)
        row.update(opponent=fixture.get('opponent') if fixture else None,
                   venue=fixture.get('venue') if fixture else None,
                   fdr=fixture.get('fdr') if fixture else None,
                   estimated_position=pos, expected_points=None, expected_minutes=None,
                   projection_status=None)
        if not fixture:
            row['projection_status'] = 'fixture_missing'
            row['fixture_note'] = ('Bu takım seçili haftanın fikstüründe yok; takım adı veya sezon/lig kapsamını kontrol edin.')
        elif not n:
            row['projection_status'] = 'team_history_missing'
        elif fixture.get('fdr') is None:
            row['projection_status'] = 'fdr_missing'
        elif pos is None:
            row['projection_status'] = 'position_missing'
        elif any(p.get(field) is None for field in ('minutes', 'xg', 'xa')):
            row['projection_status'] = 'stat_missing'
        else:
            minutes = float(p['minutes'])
            xg, xa = float(p['xg']), float(p['xa'])
            if minutes < 0 or xg < 0 or xa < 0 or n < 1:
                row['projection_status'] = 'invalid_stats'
            else:
                # Team matches provide the season exposure denominator, including bench time.
                expected_minutes = min(90.0, minutes / n)
                play_prob = min(1.0, expected_minutes / 90.0)
                goal_factor = 1 + (3 - fixture['fdr']) * 0.08
                assist_factor = 1 + (3 - fixture['fdr']) * 0.06
                goal_contribution = xg / n * GOAL_POINTS[pos] * goal_factor
                assist_contribution = xa / n * 3 * assist_factor
                # Only playing and attacking points estimated. Clean sheets, cards,
                # saves, bonuses etc. are excluded; not official fantasy points.
                projected = 2 * play_prob + goal_contribution + assist_contribution
                row.update(expected_points=round(max(0, projected), 2),
                           expected_minutes=round(expected_minutes, 1),
                           projection_status='estimated_partial')
        output.append(row)
    output.sort(key=lambda p: (p['expected_points'] is not None, p['expected_points'] or 0), reverse=True)
    return output
