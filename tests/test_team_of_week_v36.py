from analysis.team_of_week_v36 import feature,boost
from data_sources.team_of_week import parse

def test_future_never_used():
    weeks={1:{1},2:{1},3:{2}}
    assert feature(weeks,2,1)['last5']==1
    assert feature(weeks,3,1)['last5']==2
    assert feature(weeks,3,2)['last5']==0
    assert boost(weeks,2,2,.1)==1

def test_api_shape():
    result=parse({'data':{'available':True,'players':[{'playerId':i,'points':i} for i in range(1,12)]}},9)
    assert len(result['players'])==11
