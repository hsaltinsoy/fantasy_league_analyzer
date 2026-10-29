"""Transparent, opponent-specific fixture rating; no fabricated match data."""
from collections import defaultdict
from datetime import date
from data_sources.team_names import normalize_team


def calculate(matches, fixtures, as_of=None):
    as_of = as_of or date.today()
    history = defaultdict(list)
    for match in matches:
        try:
            played = date.fromisoformat(match['date'])
            hg, ag = int(match['home_goals']), int(match['away_goals'])
        except (KeyError, ValueError, TypeError):
            continue
        if played >= as_of:
            continue
        home, away = normalize_team(match['home']), normalize_team(match['away'])
        history[home].append((played, hg, ag, True))
        history[away].append((played, ag, hg, False))

    def stats(team):
        games = sorted(history.get(team, []), reverse=True)[:5]
        if not games:
            return None
        n = len(games)
        points = sum(3 if gf > ga else 1 if gf == ga else 0 for _, gf, ga, _ in games)
        return {'matches': n, 'points': points, 'points_per_match': round(points / n, 2),
                'goals_for_per_match': round(sum(gf for _, gf, _, _ in games) / n, 2),
                'goals_against_per_match': round(sum(ga for _, _, ga, _ in games) / n, 2)}

    teams = {normalize_team(team) for f in fixtures for team in (f['home'], f['away'])}
    forms = {team: stats(team) for team in sorted(teams)}
    output = []
    for fixture in fixtures:
        for side in ('home', 'away'):
            team = fixture[side]
            opponent = fixture['away' if side == 'home' else 'home']
            own, other = forms[normalize_team(team)], forms[normalize_team(opponent)]
            if own is None or other is None:
                difficulty = None
                detail = ('No historical matches for '+ (team if own is None else opponent))
            else:
                # Difficulty is higher against strong, in-form teams; away matches harder.
                raw = (other['points_per_match'] / 3 * 0.45 +
                       min(other['goals_for_per_match'] / 3, 1) * 0.30 +
                       (1 - min(other['goals_against_per_match'] / 3, 1)) * 0.25)
                raw += 0.08 if side == 'away' else -0.08
                difficulty = max(1, min(5, round(1 + 4 * max(0, min(1, raw)))))
                detail = 'Opponent last-5 form, attack, defence and home/away adjustment'
            output.append({'team': team, 'opponent': opponent, 'venue': side,
                           'date': fixture.get('date'), 'fdr': difficulty,
                           'form': own, 'opponent_form': other, 'method': detail, 'data_status': ('ok' if difficulty is not None else 'missing_history'), 'normalized_team': normalize_team(team), 'normalized_opponent': normalize_team(opponent)})
    return output
