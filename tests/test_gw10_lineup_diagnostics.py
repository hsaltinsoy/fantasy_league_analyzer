"""Frozen GW10 starting XI from the 2026-10-29 local saved lineup."""
from analysis.lineup_diagnostics import describe


def current_gw10():
    rows = [
        (216,'Bahadır Han Güngördü','7','17','GK',6.048,5.839),
        (48,'Guram Giorbelidze','2','8','DEF',6.808,6.524),
        (217,'Chidozie Collins Awaziem','7','17','DEF',6.034,5.514),
        (53,'Amar Gerxhaliu','2','8','DEF',5.428,5.233),
        (12,'Mohamed Salah Hamed Mahrous Ghaly','1','18','MID',6.758,6.185),
        (136,"Diaa Sabi'a",'5','16','MID',6.657,6.496),
        (212,'Berkan İsmail Kutlu','4','12','MID',6.268,5.951),
        (4,'Ernest Muçi','1','18','MID',5.458,5.168),
        (148,'Gift Emmanuel Orban','5','16','FWD',6.806,6.364),
        (75,'Adrian Dawid Benedyczak','3','9','FWD',5.965,5.725),
        (404,'Eldor Shomurodov','13','15','FWD',5.839,5.529),
    ]
    xi=[{'id':i,'name':name,'team':team,'opponent':opponent,'position':position,
         'xpts':points,'captain_bonus_xpts':bonus,'captain':i==48}
        for i,name,team,opponent,position,points,bonus in rows]
    return {'starting_xi':xi,'bench':[{'xpts':x} for x in (5.085,4.89,4.576,4.969)],
            'risk_penalty':0,'risk_profile':'cautious'}


def test_gw10_captain_and_zero_conflict_are_explained():
    diagnostic=describe(current_gw10())
    assert diagnostic['captain']['name']=='Guram Giorbelidze'
    assert diagnostic['captain']['risk_discount']==.284
    assert diagnostic['captain']['selection_margin']==.028
    assert diagnostic['captain']['upside_estimate'] is None
    assert diagnostic['opposing_defender_attacker_pairs']==[]
    assert diagnostic['objective']['opposing_pair_penalty']==0
    assert diagnostic['objective']['raw_xi_plus_captain']==74.877
    assert diagnostic['objective']['reconstructed_objective']==74.7882
    assert {x['team'] for x in diagnostic['same_club_defensive_clusters']}=={'2','7'}
    assert diagnostic['same_club_defensive_penalty']==0
