"""Every official formation, legacy replay policy and exact small-pool optimum."""
import itertools

import pytest

from analysis.optimizer import FORMATIONS, LEGACY_FORMATIONS, optimize, valid_formations
from analysis.phase38_optimizer_audit import objective
from analysis.capture_integrity import validate_inputs
from analysis.six_model_batch import replay

OFFICIAL={(3,5,2),(3,4,3),(4,4,2),(4,3,3),(4,5,1),(5,4,1),(5,3,2),(5,2,3)}


def pool_for(formation):
    d,m,f=formation
    positions=['GK']*2+['DEF']*5+['MID']*5+['FWD']*3
    counters={'GK':0,'DEF':0,'MID':0,'FWD':0}
    chosen={'GK':1,'DEF':d,'MID':m,'FWD':f}
    players=[]
    for i,pos in enumerate(positions,1):
        counters[pos]+=1
        points=10 if counters[pos]<=chosen[pos] else .1
        players.append({'id':i,'name':str(i),'team':str(i),'position':pos,'price':4.0,'xpts':points})
    return players


def test_official_formation_enumeration():
    assert set(valid_formations())==OFFICIAL
    assert set(FORMATIONS)==OFFICIAL
    assert set(LEGACY_FORMATIONS)==OFFICIAL-{(5,2,3)}


@pytest.mark.parametrize('formation',sorted(OFFICIAL))
def test_each_formation_can_win(formation):
    result=optimize(pool_for(formation),time_limit=2)
    assert result['formation']=='-'.join(map(str,formation))
    assert result['all_formations_proven_optimal']
    assert len(result['formation_comparison'])==8


def test_523_improves_objective_and_legacy_is_replayable():
    pool=pool_for((5,2,3))
    old=optimize(pool,formation_policy='legacy_pre39_v1',time_limit=2)
    new=optimize(pool,formation_policy='current_tff_v2',time_limit=2)
    assert old['formation']!='5-2-3'
    assert new['formation']=='5-2-3'
    assert new['risk_adjusted_objective']>old['risk_adjusted_objective']
    assert len(old['formation_comparison'])==7
    assert len(new['formation_comparison'])==8
    groups={pos:[p for p in pool if p['position']==pos] for pos in ('GK','DEF','MID','FWD')}
    best=-1
    for d,m,f in OFFICIAL:
        for g,ds,ms,fs in itertools.product(itertools.combinations(groups['GK'],1),
                itertools.combinations(groups['DEF'],d),itertools.combinations(groups['MID'],m),
                itertools.combinations(groups['FWD'],f)):
            xi=list(g+ds+ms+fs)
            bench=[p for p in pool if p not in xi]
            best=max(best,objective(xi,bench,max(xi,key=lambda p:p['xpts'])))
    assert abs(new['risk_adjusted_objective']-best)<.0002


def test_unknown_policy_rejected():
    with pytest.raises(ValueError,match='Unknown formation policy'):
        optimize(pool_for((3,4,3)),formation_policy='unknown')


def test_legacy_replay_routes_to_original_policy(monkeypatch):
    players=pool_for((3,4,3))
    fixtures=[{'id':1,'homeClubId':1,'awayClubId':2}]
    histories=[{'player_id':p['id'],'rows':[{'gameweekOrder':9,'points':2}]}
               for p in players]
    bundle={'gameweek':10,'players':players,'fixtures':fixtures,'histories':histories,
            'input_hash':validate_inputs(10,players,fixtures,histories),
            'cutoff_utc':'2026-11-01T10:00:00Z','deadline_at':'2026-11-01T12:00:00Z',
            'external_matches':[{'id':1}], 'availability_policy':'legacy_pre31a'}
    seen=[]
    monkeypatch.setattr('analysis.six_model_batch.make_adjuster_from_matches',
                        lambda *args:(lambda pool:pool,{}))
    result=replay(bundle,predictor=lambda *args,**kwargs:
                  seen.append(kwargs['formation_policy']) or {'starting_xi':[],'bench':[]})
    assert result['status']=='complete'
    assert seen==['legacy_pre39_v1']*6
