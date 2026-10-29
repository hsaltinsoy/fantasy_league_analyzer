from analysis.experimental_covariance import category, estimate, lineup_variance, compare_candidates, stability_report


def fixture(week):
    return {'matches':[{'id':week,'homeClubId':1,'awayClubId':2,'status':'FT'}]}


def row(week, points, played=True, opponent=2, venue='H'):
    return {'gameweekOrder':week,'points':points,'played':played,
            'minutesPlayed':90 if played else 0,'opponentClubId':opponent,'homeAway':venue}


def test_appearance_and_future_rows_are_excluded():
    records=[({'id':1,'position':'DEF'},[row(1,2),row(2,4),row(3,0,False),row(4,8),row(5,999)]),
             ({'id':2,'position':'DEF'},[row(1,3),row(2,5),row(3,0,False),row(4,7),row(5,999)])]
    weeks={str(w):fixture(w) for w in range(1,6)}
    evidence=estimate(records,weeks,5)
    assert evidence['excluded']['no_appearance']==2
    assert evidence['completed_match_clusters']==3
    assert evidence['covariance']['def_def']['match_clusters']==3
    assert evidence['covariance']['def_def']['shrunk'] is None
    records[0][1][-1]['points']=-999
    assert estimate(records,weeks,5)['covariance']==evidence['covariance']


def test_missing_or_postponed_is_not_zero_score():
    records=[({'id':1,'position':'GK'},[row(1,2),row(2,None),row(3,4)]),
             ({'id':2,'position':'DEF'},[row(1,3),row(2,5),row(3,6)])]
    weeks={'1':fixture(1),'2':{'matches':[{'id':2,'homeClubId':1,'awayClubId':2,'status':'POSTPONED'}]},'3':fixture(3)}
    evidence=estimate(records,weeks,4)
    assert evidence['excluded']['missing_points']==1
    assert evidence['excluded']['missing_or_unfinished_fixture']==1
    assert evidence['covariance']['gk_def']['match_clusters']==0
    assert evidence['covariance']['gk_def']['shrunk'] is None


def test_category_and_risk_sensitivity_without_production_optimizer():
    a={'id':1,'name':'A','team':'1','opponent':'2','position':'DEF','xpts':6}
    b={'id':2,'name':'B','team':'1','opponent':'2','position':'DEF','xpts':5}
    c={'id':3,'name':'C','team':'2','opponent':'1','position':'FWD','xpts':7}
    assert category(a,b)=='def_def'
    assert category(a,c)=='opposing_def_att'
    evidence={'player_variance':{'1':{'variance':16},'2':{'variance':16},'3':{'variance':1}},
              'position_variance':{},'covariance':{
                  'def_def':{'shrunk':4,'match_clusters':30},
                  'gk_def':{'shrunk':None,'match_clusters':0},
                  'opposing_def_att':{'shrunk':-1,'match_clusters':30}}}
    assert lineup_variance([a,b],1,evidence)['variance']>lineup_variance([a,c],3,evidence)['variance']
    solutions={'A':{'starting_xi':[a,b],'squad':[a,b]},
               'B':{'starting_xi':[a,c],'squad':[a,c]}}
    choices=compare_candidates(solutions,evidence,(0,1))['selected_by_risk_aversion']
    assert choices['0']['captain_id']==3
    assert choices['1']['captain_id']==3


def test_stability_report_omits_one_completed_match_at_a_time():
    records=[({'id':1,'position':'DEF'},[row(w,w) for w in range(1,6)]),
             ({'id':2,'position':'DEF'},[row(w,w+1) for w in range(1,6)])]
    weeks={str(w):fixture(w) for w in range(1,6)}
    report=stability_report(records,weeks,6,windows=(3,5))
    assert report['leave_one_match_out']['def_def']['match_omissions']==0  # Below 20-cluster safety threshold.
    assert report['windows']['3']['match_clusters']==3
