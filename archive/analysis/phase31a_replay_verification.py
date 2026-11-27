"""Read-only check that the availability fix preserves saved GW12 lineup replays."""
import json
from pathlib import Path

from analysis.capture_integrity import validate_inputs
from analysis.prediction_tracking import get_snapshot, get_prediction, _postgres, DEFAULT_DB
from analysis.six_model_batch import replay, NAMES

IDS = ('ceddd5ae-a154-411b-9581-31a484c87f5f',
       '914af52a-997c-4b32-84b9-41e1be804637')


def run():
    pg = _postgres(DEFAULT_DB)
    report = {}
    for sid in IDS:
        snapshot = get_snapshot(sid)
        payload = snapshot['payload']
        hash_before = payload['input_sha256']
        bundle = {'gameweek':12, 'players':payload['players'],
                  'fixtures':payload['fixtures'],'histories':payload['histories'],
                  'cutoff_utc':snapshot['captured_at'],'deadline_at':snapshot['deadline_at'],
                  'external_matches':payload['feature_evidence']['football_data_matches'],
                  'team_features':{}, 'fixture_date':None,
                  'availability_policy':'legacy_pre31a',
                  'input_hash':validate_inputs(12, payload['players'],payload['fixtures'],payload['histories'])}
        saved = [get_prediction(pid) for pid in pg.prediction_ids(sid)]
        six = {p['model']:p['payload'] for p in saved if
               (p['payload'].get('benchmark') or {}).get('batch_id') and p['model'] in NAMES}
        if set(six) != set(NAMES):
            raise RuntimeError('Incomplete saved six-model batch')
        fresh = replay(bundle)
        if fresh['status'] != 'complete':
            raise RuntimeError(f'Replay incomplete: {fresh["statuses"]}')
        checks = {}
        for name in NAMES:
            a, b = six[name], fresh['predictions'][name]
            checks[name] = {'xi':{p['id'] for p in a['starting_xi']} == {p['id'] for p in b['starting_xi']},
                'bench':{p['id'] for p in a['bench']} == {p['id'] for p in b['bench']},
                'captain':a['captain'] == b['captain'],
                'formation':a['formation'] == b['formation'],
                'fantasy_xpts':a['expected_fantasy_points'] == b['expected_fantasy_points'],
                'objective':a['risk_adjusted_objective'] == b['risk_adjusted_objective'],
                'eligible_old':a['eligible_players'],'eligible_new':b['eligible_players']}
        if not all(all(v for k,v in result.items() if k not in ('eligible_old','eligible_new')) and
                   result['eligible_old'] == result['eligible_new'] for result in checks.values()):
            raise RuntimeError(f'Saved replay mismatch: {sid}: {checks}')
        if get_snapshot(sid)['payload']['input_sha256'] != hash_before:
            raise RuntimeError('Frozen snapshot changed')
        report[sid] = checks
    return report


if __name__ == '__main__':
    path = Path('docs/phase31a_replay_verification.json')
    path.write_text(json.dumps(run(), indent=2), encoding='utf-8')
    print(path)
