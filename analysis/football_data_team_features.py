"""Descriptive team features from completed, pre-cutoff external matches."""
from collections import defaultdict
from statistics import mean
from math import exp


def _avg(values):
    present = [float(value) for value in values if value is not None]
    return mean(present) if present else None


def team_features(matches):
    by_team = defaultdict(list)
    for match in matches:
        if match['full_time_result'] is None:
            continue
        for side in ('home', 'away'):
            home = side == 'home'
            team = match[f'{side}_team_id']
            if team is None:
                continue
            goals = match['home_goals'] if home else match['away_goals']
            conceded = match['away_goals'] if home else match['home_goals']
            if goals is None or conceded is None:
                continue
            by_team[str(team)].append({
                'date': match['match_date'], 'id': match['id'], 'home': home,
                'points': 3 if goals > conceded else 1 if goals == conceded else 0,
                'goals': goals, 'conceded': conceded,
                'shots': match['home_shots'] if home else match['away_shots'],
                'sot': match['home_sot'] if home else match['away_sot'],
                'xg': match['home_xg'] if home else match['away_xg'],
                'xg_against': match['away_xg'] if home else match['home_xg'],
            })
    result = {}
    for team, games in by_team.items():
        games.sort(key=lambda game: (game['date'], game['id']))
        home = [game for game in games if game['home']]
        away = [game for game in games if not game['home']]
        result[team] = {
            'matches': len(games), 'last3_points': sum(g['points'] for g in games[-3:]),
            'last5_points': sum(g['points'] for g in games[-5:]),
            'goals_scored': _avg(g['goals'] for g in games),
            'goals_conceded': _avg(g['conceded'] for g in games),
            'home_points_per_match': _avg(g['points'] for g in home),
            'away_points_per_match': _avg(g['points'] for g in away),
            'clean_sheet_rate': _avg(int(g['conceded'] == 0) for g in games),
            'shots_per_match': _avg(g['shots'] for g in games),
            'shots_on_target_per_match': _avg(g['sot'] for g in games),
            'xg_for': _avg(g['xg'] for g in games),
            'xg_against': _avg(g['xg_against'] for g in games),
            'xg_difference': _avg(float(g['xg']) - float(g['xg_against'])
                                  if g['xg'] is not None and g['xg_against'] is not None
                                  else None for g in games),
            'last3_xg_for': _avg(g['xg'] for g in games[-3:]),
            'last5_xg_for': _avg(g['xg'] for g in games[-5:]),
            'last3_xg_against': _avg(g['xg_against'] for g in games[-3:]),
            'last5_xg_against': _avg(g['xg_against'] for g in games[-5:]),
            'last3_xg_difference': _avg(float(g['xg']) - float(g['xg_against'])
                                          if g['xg'] is not None and g['xg_against'] is not None
                                          else None for g in games[-3:]),
            'last5_xg_difference': _avg(float(g['xg']) - float(g['xg_against'])
                                          if g['xg'] is not None and g['xg_against'] is not None
                                          else None for g in games[-5:]),
            'home_xg_for': _avg(g['xg'] for g in home),
            'home_xg_against': _avg(g['xg_against'] for g in home),
            'away_xg_for': _avg(g['xg'] for g in away),
            'away_xg_against': _avg(g['xg_against'] for g in away),
            'last3_shots': _avg(g['shots'] for g in games[-3:]),
            'last5_shots': _avg(g['shots'] for g in games[-5:]),
            'last3_shots_on_target': _avg(g['sot'] for g in games[-3:]),
            'last5_shots_on_target': _avg(g['sot'] for g in games[-5:]),
        }
    return result


def fixture_features(features, team_id, opponent_id):
    team = features.get(str(team_id))
    opponent = features.get(str(opponent_id))
    if team is None or opponent is None:
        return None
    attack = opponent['goals_scored']
    defence = opponent['goals_conceded']
    league_defence = _avg(row['goals_conceded'] for row in features.values())
    expected_clean_sheet = (exp(-opponent['xg_for']) if opponent['xg_for'] is not None
                            else None)
    return {'team': team, 'opponent_attacking_strength': attack,
            'opponent_defensive_strength': defence,
            'opponent_defensive_xg_conceded': opponent['xg_against'],
            'opponent_shots_on_target': opponent.get('shots_on_target_per_match'),
            'expected_clean_sheet_indicator': expected_clean_sheet,
            'fixture_difficulty': (attack / league_defence if league_defence else None)}
