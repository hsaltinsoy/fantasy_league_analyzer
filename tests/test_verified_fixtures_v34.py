import json
import pytest
from analysis.verified_fixtures_v34 import load_verified

def test_official_fixtures():
    data = load_verified('historical_data/tff_fixtures_verified_v5.json', [5,6,7,8,9])
    assert len(data) == 34
    assert data[10]['7'] == '17'
    assert data[10]['17'] == '7'
    assert all(len(data[w]) == 18 for w in (5,6,7,8,9))

def test_reject_corrupt(tmp_path):
    source = json.loads(open('historical_data/tff_fixtures_verified_v5.json',encoding='utf8').read())
    source['weeks']['5']['matches'][0]['homeClubId'] = source['weeks']['5']['matches'][0]['awayClubId']
    p = tmp_path/'bad.json'
    p.write_text(json.dumps(source))
    with pytest.raises(ValueError):
        load_verified(p, [5])
