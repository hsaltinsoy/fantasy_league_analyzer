from collections import Counter

import pytest

from analysis.direct_risk_optimization import pareto_frontier, solve
from analysis.optimizer import FORMATIONS


def sample_pool():
    positions = ['GK']*3+['DEF']*7+['MID']*7+['FWD']*4
    return [{'id':i+1,'name':f'P{i+1}','team':str(i%7),'position':pos,
             'price':5.,'xpts':5.+(i%3)*.2,'opponent':str((i+1)%7)}
            for i,pos in enumerate(positions)]


def evidence(pool):
    return {'player_variance':{str(p['id']):{'variance':1.+(p['id']%4)*.5} for p in pool},
            'position_variance':{},
            'covariance':{k:{'shrunk':None} for k in ('def_def','gk_def','opposing_def_att')}}


def test_direct_solution_preserves_fantasy_rules_and_reproducibility():
    pool = sample_pool()
    first = solve(pool,evidence(pool),time_limit=3)
    second = solve(pool,evidence(pool),time_limit=3)
    assert first == second
    assert first['status']=='optimal'
    assert len(first['squad_ids'])==15
    assert len(first['starting_xi_ids'])==11
    assert len(first['bench_ids'])==4
    assert set(first['starting_xi_ids']) <= set(first['squad_ids'])
    assert first['captain_id'] in first['starting_xi_ids']
    assert first['squad_cost'] <= 100
    selected = [p for p in pool if p['id'] in first['squad_ids']]
    xi = [p for p in pool if p['id'] in first['starting_xi_ids']]
    assert Counter(p['position'] for p in selected)=={'GK':2,'DEF':5,'MID':5,'FWD':3}
    assert max(Counter(p['team'] for p in selected).values())<=3
    counts=Counter(p['position'] for p in xi)
    assert counts['GK']==1
    assert (counts['DEF'],counts['MID'],counts['FWD']) in FORMATIONS


def test_mean_floor_and_missing_variance():
    pool=sample_pool()
    data=evidence(pool)
    maximum=solve(pool,data,objective='mean',time_limit=3)
    floor=maximum['expected_points']-1
    low_risk=solve(pool,data,mean_floor=floor,time_limit=3,hint=maximum)
    assert low_risk['expected_points']>=floor-.001
    assert low_risk['standard_deviation']<=maximum['standard_deviation']+.001
    data['player_variance'].pop(str(pool[0]['id']))
    with pytest.raises(ValueError,match='Missing variance'):
        solve(pool,data,time_limit=1)


def test_observed_frontier_removes_dominated_solutions():
    rows=[{'starting_xi_ids':[1],'captain_id':1,'expected_points':60,'standard_deviation':12},
          {'starting_xi_ids':[2],'captain_id':2,'expected_points':59,'standard_deviation':10},
          {'starting_xi_ids':[3],'captain_id':3,'expected_points':58,'standard_deviation':11}]
    frontier=pareto_frontier(rows)
    assert [r['captain_id'] for r in frontier]==[1,2]
