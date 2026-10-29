import json
import pytest
from analysis.walkforward_v32 import load_snapshots, evaluate_fixture, walk_forward


def test_missing_snapshot():
    with pytest.raises(ValueError, match='Provide'):
        load_snapshots(None, [5])


def test_snapshot_validation(tmp_path):
    p = tmp_path/'fixtures.json'
    base = {'captured_utc':'2026-08-01T10:00:00Z','deadline_utc':'2026-08-02T10:00:00Z',
            'source':'official URL','matches':[{'home_club_id':'A','away_club_id':'B'}]}
    p.write_text(json.dumps({'weeks':{'5':base}}))
    assert load_snapshots(p,[5]) == {5:{'A':'B','B':'A'}}
    with pytest.raises(ValueError, match='missing fixture'):
        load_snapshots(p,[5,6])
    base['captured_utc'] = '2026-08-03T10:00:00Z'
    p.write_text(json.dumps({'weeks':{'5':base}}))
    with pytest.raises(ValueError, match='before deadline'):
        load_snapshots(p,[5])


def test_duplicate_fixture_fails(tmp_path):
    p = tmp_path/'fixtures.json'
    p.write_text(json.dumps({'weeks':{'5':{'captured_utc':'2026-08-01T10:00:00Z',
      'deadline_utc':'2026-08-02T10:00:00Z','source':'url',
      'matches':[{'home_club_id':1,'away_club_id':2},{'home_club_id':1,'away_club_id':3}]}}}))
    with pytest.raises(ValueError, match='duplicate'):
        load_snapshots(p,[5])


def test_missing_team_fails():
    records = [({'id':1,'name':'X','position':'FWD','team':'A'},
                [{'gameweekOrder':4,'points':3,'minutesPlayed':90,'cost':5,'started':True},
                 {'gameweekOrder':5,'points':2,'minutesPlayed':90,'cost':5}])]
    with pytest.raises(ValueError, match='missing teams'):
        evaluate_fixture(records,5,{'window':5,'shrinkage':4,'recent_mix':.55,'recency':True},{'B':'C'}, optimizer=lambda pool: {})


def test_no_weeks():
    with pytest.raises(ValueError, match='Weeks'):
        walk_forward([],{},weeks=[])
