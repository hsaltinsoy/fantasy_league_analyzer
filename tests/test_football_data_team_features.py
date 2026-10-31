from datetime import date

import pytest

from analysis.football_data_team_features import fixture_features, team_features
from storage.football_data_repository import parse_csv


def csv_bytes(rows, header='Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR,HS,AS,HST,AST'):
    return (header + '\n' + '\n'.join(rows) + '\n').encode()


def test_optional_statistics_remain_missing():
    parsed = parse_csv(csv_bytes(['T1,14/08/2026,Alpha,Beta,2,1,H,,,,']))
    assert parsed['rows'][0]['numbers']['HS'] is None
    assert parsed['rows'][0]['numbers']['HxG'] is None


def test_invalid_and_duplicate_matches_rejected():
    row = 'T1,14/08/2026,Alpha,Beta,2,1,H,10,8,5,2'
    with pytest.raises(ValueError, match='duplicate'):
        parse_csv(csv_bytes([row, row]))
    with pytest.raises(ValueError, match='disagrees'):
        parse_csv(csv_bytes([row.replace(',H,', ',A,')]))
    with pytest.raises(ValueError, match='invalid date'):
        parse_csv(csv_bytes([row.replace('14/08/2026', '99/08/2026')]))


def test_team_features_preserve_missing_and_form():
    matches = [{
        'id': 'one', 'match_date': date(2026, 8, 14),
        'home_team_id': '1', 'away_team_id': '2',
        'full_time_result': 'H', 'home_goals': 2, 'away_goals': 0,
        'home_shots': None, 'away_shots': None,
        'home_sot': None, 'away_sot': None,
        'home_xg': 1.5, 'away_xg': 0.3,
    }]
    result = team_features(matches)
    assert result['1']['last3_points'] == 3
    assert result['1']['clean_sheet_rate'] == 1
    assert result['1']['shots_per_match'] is None
    assert result['1']['xg_for'] == 1.5
    assert result['1']['xg_against'] == 0.3
    assert result['1']['xg_difference'] == 1.2
    assert result['1']['last3_shots_on_target'] is None
    assert fixture_features(result, '1', '2')['opponent_attacking_strength'] == 0
    assert fixture_features(result, '1', '2')['opponent_defensive_xg_conceded'] == 1.5
