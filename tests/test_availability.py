from datetime import date
from analysis.availability import evaluate

TODAY = date(2026,10,27)

def test_official_unavailable():
    assert not evaluate({'id':1,'availability':'UNAVAILABLE'}, today=TODAY)['eligible']

def test_manual_round_out():
    rule={'player_id':507,'round':10,'status':'OUT','source':'PFDK','checked_at':'2026-10-27'}
    assert not evaluate({'id':507,'availability':'AVAILABLE'}, [rule], today=TODAY)['eligible']
    assert evaluate({'id':507,'availability':'AVAILABLE'}, [rule], round_number=11, today=TODAY)['eligible']

def test_doubtful_percent():
    assert evaluate({'id':1,'availability':'DOUBTFUL','availability_percent':40},today=TODAY)['factor']==.4

def test_unknown():
    assert evaluate({'id':1},today=TODAY)['status']=='UNKNOWN'

def test_expired_rule():
    rule={'player_id':1,'round':10,'status':'OUT','source':'News','expires':'2026-10-26'}
    assert evaluate({'id':1,'availability':'AVAILABLE'},[rule],today=TODAY)['eligible']
