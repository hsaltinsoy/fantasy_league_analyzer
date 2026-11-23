from data_sources.tff_official import _extract, TFFFeedError
import pytest
from contextlib import contextmanager

def test_extract_official_player():
    players=_extract({'players':[{'playerId':507,'name':'Victor James','surname':'Osimhen','matchName':'Osimhen','clubId':17,'position':'FWD','cost':12}]})
    assert players[0]['position']=='FWD'
    assert players[0]['price']==12
    assert players[0]['club_id']==17

def test_unauthorized():
    with pytest.raises(TFFFeedError): _extract({'error':'unauthorized'})


def test_history_verification_filters_unfinished_and_records_retry(monkeypatch, tmp_path):
    import data_sources.tff_official as feed
    class Response:
        status = 200
        ok = True
        def json(self):
            return {'data': [{'gameweekOrder': 9}, {'gameweekOrder': 10},
                             {'gameweekOrder': 11}, {'gameweekOrder': 12}]}
    class Request:
        calls = 0
        def get(self, *_args, **_kwargs):
            self.calls += 1
            if self.calls == 1:
                raise TimeoutError('temporary timeout')
            return Response()
    class Browser:
        request = Request()
        def close(self):
            pass
    class Chromium:
        def launch_persistent_context(self, *_args, **_kwargs):
            return Browser()
    class Playwright:
        chromium = Chromium()
    @contextmanager
    def browser():
        yield Playwright()
    monkeypatch.setattr(feed, 'PROFILE', tmp_path)
    monkeypatch.setattr(feed, '_browser', browser)
    found = feed.fetch_player_histories([507], completed_through=10, target_week=12,
        max_retries=1, include_metrics=True)
    assert [r['gameweekOrder'] for r in found['rows_by_player']['507']] == [9, 10]
    assert found['metrics']['raw_week_coverage'] == {9: 1, 10: 1, 11: 1, 12: 1}
    assert found['metrics']['requests'] == 2
    assert found['metrics']['retries'] == 1
