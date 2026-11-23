from datetime import date
from analysis.availability import BLOCKED, DOUBTFUL, evaluate, normalize_status
import pytest

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


@pytest.mark.parametrize('status', sorted(BLOCKED))
def test_all_blocked_official_statuses_override_manual_available(status):
    rule = {'player_id': 355, 'round': 10, 'status': 'AVAILABLE', 'source': 'manual'}
    result = evaluate({'id': 355, 'availability': f' {status.lower()} ',
                       'availability_percent': 100}, [rule], today=TODAY)
    assert result['status'] == status
    assert result['eligible'] is False
    assert result['factor'] == 0


@pytest.mark.parametrize('status', sorted(DOUBTFUL))
def test_doubtful_official_statuses(status):
    result = evaluate({'id': 1, 'availability': status}, today=TODAY)
    assert result['eligible'] is True
    assert result['factor'] == .5


def test_normalize_status_and_available():
    assert normalize_status(' injury-doubt ') == 'INJURY_DOUBT'
    assert evaluate({'id': 1, 'availability': ' available '}, today=TODAY)['factor'] == 1


def test_new_candidate_pool_excludes_departed_but_explicit_legacy_replay_preserves_it():
    from analysis.predict_next_week import build_candidate_pool
    players = [{'id': 355, 'name': 'Departed', 'club_id': 1, 'position': 'MID',
                'price': 5, 'availability': 'DEPARTED'}]
    rows = [{'gameweekOrder': week, 'points': 2, 'minutesPlayed': 90, 'started': True}
            for week in (7, 8, 9)]
    args = (10, players, [(players[0], rows)], {10: {'1': '2'}})
    current, excluded = build_candidate_pool(*args)
    legacy, _ = build_candidate_pool(*args, availability_policy='legacy_pre31a')
    assert current == []
    assert excluded['availability'] == 1
    assert [p['id'] for p in legacy] == [355]
