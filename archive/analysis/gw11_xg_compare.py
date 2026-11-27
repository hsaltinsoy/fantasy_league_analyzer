"""Read-only frozen GW11 baseline vs opt-in xG lineup comparison."""
import json
from datetime import datetime, timezone

from analysis.predict_next_week import predict
from analysis.live_benchmark import _fixture_lookup
from analysis.football_data_live import make_adjuster
from analysis.prediction_tracking import parse_time
from storage.db import engine_from_env
from storage.runtime_repository import RuntimeRepository


def run(engine):
    repo = RuntimeRepository(engine)
    cutoff = datetime.now(timezone.utc)
    archive = repo.fixture_archive(max_age_seconds=3600)
    entry = archive['weeks']['11']
    if parse_time(entry['deadline']) <= cutoff:
        raise ValueError('GW11 deadline passed')
    players = repo.current_player_pool(max_age_seconds=3600)
    histories = repo.historical_records(before_week=11)
    records = [(p, histories.get(str(p['id']), [])) for p in players]
    fixtures = {11: _fixture_lookup(entry)}
    from analysis.lineup_snapshot import fingerprint, source_versions
    input_sha256 = fingerprint(11, players, histories, entry, 'short_form_3w', 'balanced', 0)
    output = {'week': 11, 'cutoff_utc': cutoff.isoformat(),
              'fixture_retrieved_at': archive['captured_utc'],
              'input_snapshot_sha256': input_sha256,
              'input_sources': source_versions(engine),
              'player_pool_count': len(players), 'scenarios': {}}
    for name, mode in [('baseline', None), ('position_aware_40', 'position_aware_xg'),
                       ('uniform_40', 'uniform_xg')]:
        adjuster = None
        meta = None
        if mode:
            adjuster, meta = make_adjuster(engine, archive, 11, cutoff, mode, .4)
        result = predict(11, players, records, fixtures, {}, 'short_form_3w',
                         risk_profile='balanced', fixture_archive=archive,
                         pool_adjuster=adjuster)
        output['scenarios'][name] = {'lineup': result, 'metadata': meta}
    output['report_id'] = repo.save_generated_report('gw11_xg_comparison', output)
    return output


if __name__ == '__main__':
    engine = engine_from_env()
    try:
        print(json.dumps(run(engine), ensure_ascii=True))
    finally:
        engine.dispose()
