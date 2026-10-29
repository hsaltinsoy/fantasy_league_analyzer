from analysis.multiweek_backtest import MODELS, project

def _row(week, points, minutes=90):
    return {'gameweekOrder':week,'points':points,'minutesPlayed':minutes}

def test_robust_one_off_outlier():
    p={'position':'MID'}
    past=[_row(i,v) for i,v in enumerate([3,4,4,4,30],1)]
    robust=project(p,past,MODELS['robust_5w'])
    baseline=project(p,past,MODELS['baseline_5w'])
    assert robust < baseline

def test_robust_repeat_performance_not_zeroed():
    p={'position':'FWD'}
    past=[_row(i,v) for i,v in enumerate([7,9,10,8,11],1)]
    assert project(p,past,MODELS['robust_5w'])>0
