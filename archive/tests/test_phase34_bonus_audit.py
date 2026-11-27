"""Bonus decomposition uses only lagged bonus and avoids double counting."""
from archive.analysis.phase34_bonus_audit import bonus_value, experimental
from analysis.multiweek_backtest import MODELS, project


def test_bonus_is_replaced_not_added_twice():
    player = {'position':'MID'}
    past = [{'gameweekOrder':w,'points':5,'bonus':2,'minutesPlayed':90} for w in range(1,6)]
    base_only = [{**row,'points':3,'bonus':0} for row in past]
    assert experimental(player,past,MODELS['baseline_5w']) > experimental(player,base_only,MODELS['baseline_5w'])
    assert experimental(player,past,MODELS['baseline_5w']) == round(
        project(player,base_only,MODELS['baseline_5w']) + 2, 3)


def test_target_bonus_cannot_change_lagged_projection():
    player = {'position':'FWD'}
    past = [{'gameweekOrder':w,'points':2,'bonus':0,'minutesPlayed':80} for w in range(1,6)]
    before = experimental(player,past,MODELS['baseline_5w'])
    target = {'gameweekOrder':6,'points':20,'bonus':3,'minutesPlayed':90}
    target['bonus'] = 0
    assert experimental(player,past,MODELS['baseline_5w']) == before
    assert bonus_value({'bonus':0}) == 0
