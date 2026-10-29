from analysis.playing_time_risk import valid_appearance, probability, chronological_report


def fixture(status='FT'):
    return {'1':{'matches':[{'id':1,'homeClubId':1,'awayClubId':2,'status':status}]},
            '2':{'matches':[{'id':2,'homeClubId':1,'awayClubId':2,'status':'FT'}]},
            '3':{'matches':[{'id':3,'homeClubId':1,'awayClubId':2,'status':'FT'}]}}


def row(week, played, minutes):
    return {'gameweekOrder':week,'played':played,'minutesPlayed':minutes,'opponentClubId':2}


def test_absence_zero_minute_and_postponement_are_distinct():
    assert valid_appearance(row(1,False,0),1,fixture())==0
    assert valid_appearance(row(1,True,0),1,fixture()) is None
    assert valid_appearance(row(1,False,0),1,fixture('POSTPONED')) is None
    assert valid_appearance(row(1,True,75),1,fixture())==1


def test_probability_uses_only_earlier_labels():
    records=[({'id':1},[row(1,True,90),row(2,False,0),row(3,True,90)])]
    early=chronological_report(records,fixture(),weeks=(2,))
    records[0][1][-1]['played']=False
    records[0][1][-1]['minutesPlayed']=0
    assert chronological_report(records,fixture(),weeks=(2,))==early
    assert probability([1,0],.5)['prior_observations']==2
