from datetime import date
from data_sources.free_sync import sync

class Response:
    def __init__(self, text): self.content = text.encode()
    def raise_for_status(self): pass

def test_free_sync():
    def get(url, **kwargs):
        if 'results_' in url:
            return Response('date,home,away,ft_home,ft_away\n2026-10-01,Galatasaray,Besiktas,2,1\n2026-10-02,Fenerbahce,Trabzonspor,1,0\n')
        return Response('gw,date,home,away\n10,2026-10-30,Galatasaray,Fenerbahce\n10,2026-10-31,Besiktas,Trabzonspor\n11,2026-11-07,Galatasaray,Besiktas\n')
    data = sync(today=date(2026,10,26), get=get)
    assert data['fixture_count'] == 2
    assert len(data['fixtures']) == 4
    assert data['matches_loaded'] == 2
    assert data['players'] == []
