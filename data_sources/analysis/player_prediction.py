"""Transparent baseline projections, not calibrated fantasy scoring."""
from data_sources.team_names import normalize_team

def predict(players, fixtures):
    fixture_by_team = {normalize_team(f['team']): f for f in fixtures}
    output = []
    for player in players:
        fixture = fixture_by_team.get(normalize_team(player['team']))
        mins = min(90.0, player['minutes_last5'] / 5)
        play_factor = mins / 90.0
        goals = player['xg_last5'] if player['xg_last5'] is not None else player['goals_last5']
        assists = player['xa_last5'] if player['xa_last5'] is not None else player['assists_last5']
        attack = (goals * (6 if player['position'] in ('GK','DEF') else 5 if player['position']=='MID' else 4) + assists * 3) / 5
        baseline = 2 * play_factor + attack
        # Provisional position-sensitive adjustment; neutral when fixture data missing.
        fdr = fixture['fdr'] if fixture else None
        factor = 1.0 if fdr is None else 1 + (3-fdr)* (0.08 if player['position'] in ('MID','FWD') else 0.05)
        projected = round(max(0, baseline * factor), 2)
        output.append({**player, 'expected_points': projected, 'fixture': fixture['opponent'] if fixture else None, 'fdr': fdr, 'data_status': 'ok' if fdr is not None else 'missing_fixture_or_history', 'model': 'baseline_v0.4_uncalibrated'})
    return sorted(output, key=lambda p: p['expected_points'], reverse=True)
