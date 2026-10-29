from data_sources.tff_official import _extract, TFFFeedError
import pytest

def test_extract_official_player():
    players=_extract({'players':[{'playerId':507,'name':'Victor James','surname':'Osimhen','matchName':'Osimhen','clubId':17,'position':'FWD','cost':12}]})
    assert players[0]['position']=='FWD'
    assert players[0]['price']==12
    assert players[0]['club_id']==17

def test_unauthorized():
    with pytest.raises(TFFFeedError): _extract({'error':'unauthorized'})
