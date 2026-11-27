"""Experimental import identity and strict event-date cutoff."""
import json

import pytest

from archive.analysis import phase36_free_external_data as p


def test_import_is_idempotent_and_conflicts_fail(tmp_path, monkeypatch):
    monkeypatch.setattr(p,'IMPORT',tmp_path/'missing.json')
    raw=p.CSV.read_bytes()
    reconciliation=json.loads(p.MISSING.read_text(encoding='utf-8'))
    first,_=p.ingest_missing(raw,reconciliation)
    second,_=p.ingest_missing(raw,reconciliation)
    assert first==second
    assert len(first['matches'])==18
    assert len({m['fixture_id'] for m in first['matches']})==18
    (tmp_path/'missing.json').write_text('{}',encoding='utf-8')
    with pytest.raises(ValueError,match='Conflicting immutable'):
        p.ingest_missing(raw,reconciliation)


def test_target_week_match_never_enters_features():
    prior={'date':'2026-10-25','home':'1','away':'2','hg':1,'ag':0,
           'hxg':1.5,'axg':.4,'hs':12,'as':5,'hst':4,'ast':2}
    target={**prior,'date':'2026-11-01','hg':10,'hxg':9.0}
    before=p.features([prior],'2026-11-01')
    after=p.features([prior,target],'2026-11-01')
    assert before==after
    assert before['1']['gf']==1
