"""Run with PHASE20_TEST_DATABASE_URL pointing only to a disposable database."""
import os
import uuid
from datetime import datetime, timezone, timedelta

import pytest
from sqlalchemy import create_engine, select
from sqlalchemy.dialects.postgresql import insert

from storage import models as m
from storage.football_data_repository import FootballDataRepository


@pytest.fixture
def repository():
    url = os.getenv('PHASE20_TEST_DATABASE_URL')
    if not url:
        pytest.skip('PHASE20_TEST_DATABASE_URL required')
    if not url.endswith('/fantasy_league_phase20b_test'):
        pytest.fail('Dedicated Phase 20B test database required')
    engine = create_engine(url, pool_pre_ping=True)
    with engine.begin() as db:
        for team_id in ('1', '2'):
            db.execute(insert(m.teams).values(id=team_id, name=f'Test {team_id}')
                       .on_conflict_do_nothing(index_elements=['id']))
    yield FootballDataRepository(engine)
    engine.dispose()


def test_import_idempotent_and_transaction_rollback(repository, tmp_path, monkeypatch):
    suffix = uuid.uuid4().hex
    alpha, beta = 'Alpha-' + suffix, 'Beta-' + suffix
    monkeypatch.setitem(__import__('storage.football_data_repository', fromlist=['VERIFIED_TEAMS']).VERIFIED_TEAMS,
                        alpha, '1')
    monkeypatch.setitem(__import__('storage.football_data_repository', fromlist=['VERIFIED_TEAMS']).VERIFIED_TEAMS,
                        beta, '2')
    path = tmp_path / 'mini.csv'
    path.write_text('Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\n'
                    f'T1,14/08/2026,{alpha},{beta},2,1,H\n', encoding='utf-8')
    first = repository.import_file(path)
    second = repository.import_file(path)
    assert first['inserted'] == 1 and second['skipped'] == 1
    with repository.engine.connect() as db:
        count = db.execute(select(m.football_data_matches.c.id).where(
            m.football_data_matches.c.import_id == 'football-data:' + first['source_sha256'])).all()
    assert len(count) == 1
    assert repository.matches_before(datetime(2026, 8, 15, tzinfo=timezone.utc)) == []
    assert any(row['import_id'] == 'football-data:' + first['source_sha256']
               for row in repository.matches_before(datetime.now(timezone.utc) + timedelta(seconds=5)))
    bad = tmp_path / 'bad.csv'
    bad.write_text('Div,Date,HomeTeam,AwayTeam,FTHG,FTAG,FTR\n'
                   f'T1,15/08/2026,{alpha},{beta},2,1,A\n', encoding='utf-8')
    with pytest.raises(ValueError, match='disagrees'):
        repository.import_file(bad)
    with repository.engine.connect() as db:
        assert db.execute(select(m.football_data_imports.c.id).where(
            m.football_data_imports.c.original_filename == 'bad.csv')).first() is None
