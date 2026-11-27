"""Independent constraint checks and exact small-pool enumeration."""
import itertools

from analysis.optimizer import FORMATIONS, optimize
from archive.analysis.phase38_optimizer_audit import objective, validate


def test_exact_small_pool_matches_independent_enumeration():
    positions=['GK']*2+['DEF']*5+['MID']*5+['FWD']*3
    players=[{'id':i+1,'name':str(i+1),'team':str(i+1),'position':pos,
              'price':4.0,'xpts':round(1+i*.17,3)} for i,pos in enumerate(positions)]
    result=optimize(players,time_limit=2)
    assert result['all_formations_proven_optimal']
    best=-1
    groups={pos:[p for p in players if p['position']==pos] for pos in ('GK','DEF','MID','FWD')}
    for defenders,mids,forwards in FORMATIONS:
        for g,d,m,f in itertools.product(itertools.combinations(groups['GK'],1),
                itertools.combinations(groups['DEF'],defenders),
                itertools.combinations(groups['MID'],mids),
                itertools.combinations(groups['FWD'],forwards)):
            xi=list(g+d+m+f)
            bench=[p for p in players if p not in xi]
            captain=max(xi,key=lambda p:p['xpts'])
            best=max(best,objective(xi,bench,captain))
    assert abs(result['risk_adjusted_objective']-best)<.0002


def test_constraint_checker_rejects_illegal_captain():
    squad=[{'id':i+1,'team':str(i+1),'position':pos,'price':4.0,'xpts':1.0}
           for i,pos in enumerate(['GK']*2+['DEF']*5+['MID']*5+['FWD']*3)]
    xi=[squad[0]]+squad[2:5]+squad[7:11]+squad[12:15]
    check=validate(squad,xi,squad[1])
    assert check['formation_legal']
    assert not check['captain_in_xi']
