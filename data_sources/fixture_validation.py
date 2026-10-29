"""Validate official fixture membership without inventing postponed matches."""
from collections import Counter


def validate_week(entry, players):
    matches = entry.get('matches') or []
    teams = Counter()
    warnings = []
    fixture_ids = set()
    for match in matches:
        match_id = match.get('id')
        if match_id is None or match_id in fixture_ids:
            warnings.append(f'missing_or_duplicate_fixture_id:{match_id}')
        fixture_ids.add(match_id)
        for field in ('homeClubId', 'awayClubId'):
            team = match.get(field)
            if team is None:
                warnings.append(f'missing_{field}:{match_id}')
            else:
                teams[str(team)] += 1
        if match.get('homeClubId') == match.get('awayClubId'):
            warnings.append(f'self_fixture:{match_id}')
        if str(match.get('status') or '').upper() in ('POSTPONED', 'PST', 'CANCELLED', 'CANCELED'):
            warnings.append(f'postponed_or_cancelled:{match_id}')
        if not match.get('kickoffAt'):
            warnings.append(f'missing_kickoff:{match_id}')
    pool_teams = {str(p.get('club_id') or p.get('team') or '') for p in players}
    missing = sorted(pool_teams - set(teams) - {''})
    doubles = sorted(team for team, count in teams.items() if count > 1)
    if missing:
        warnings.append(f'missing_teams:{",".join(missing)}')
    if doubles:
        warnings.append(f'double_fixtures:{",".join(doubles)}')
    return {'fixture_coverage': {'teams_in_player_pool': len(pool_teams - {''}),
                                 'teams_with_fixture': len((pool_teams - {''}) & set(teams)),
                                 'fixtures': len(matches), 'missing_teams': missing,
                                 'double_fixture_teams': doubles},
            'invalid_club_mappings': len(missing), 'warnings': warnings}
