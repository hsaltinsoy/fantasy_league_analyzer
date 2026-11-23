"""Offline six-variant replay from one immutable prospective input bundle."""
import copy
from datetime import datetime, timezone

from analysis.capture_integrity import digest, validate_inputs
from analysis.predict_next_week import predict
from analysis.football_data_live import make_adjuster_from_matches
from analysis.multisource_experimental import rest_days_adjustment
from analysis.live_benchmark import _fixture_lookup

BASE_MODEL = 'short_form_3w'
NAMES = ('baseline_5w', 'short_form_3w', 'stable_8w',
         'uniform_xg', 'position_aware_xg', 'rest_days_control')


def replay(bundle, *, predictor=predict):
    """Compute every variant without HTTP or database reads; fail batch if any fails."""
    week = int(bundle['gameweek'])
    players = bundle['players']
    fixtures = bundle['fixtures']
    histories = bundle['histories']
    input_hash = validate_inputs(week, players, fixtures, histories)
    if bundle.get('input_hash') != input_hash:
        raise ValueError('Frozen input hash mismatch')
    batch_id = digest({'input_hash': input_hash, 'variants': NAMES})
    cutoff = datetime.fromisoformat(bundle['cutoff_utc'].replace('Z', '+00:00'))
    if cutoff.tzinfo is None:
        raise ValueError('Cutoff must include timezone')
    deadline = datetime.fromisoformat(bundle['deadline_at'].replace('Z', '+00:00'))
    if cutoff >= deadline:
        raise ValueError('Post-deadline replay input')
    archive = {'weeks': {str(week): {'matches': fixtures}}}
    lookup = {week: _fixture_lookup({'matches': fixtures})}
    records = [(p, next(h['rows'] for h in histories if str(h['player_id']) == str(p['id'])))
               for p in players]
    outputs, statuses = {}, {}
    for name in NAMES:
        try:
            adjuster = None
            model = name if name in ('baseline_5w', 'short_form_3w', 'stable_8w') else BASE_MODEL
            if name in ('uniform_xg', 'position_aware_xg'):
                matches = bundle.get('external_matches')
                if not matches:
                    raise ValueError('Frozen external match evidence unavailable')
                adjuster, _ = make_adjuster_from_matches(matches, archive, week, cutoff,
                    name, .4)
            elif name == 'rest_days_control':
                team_features = bundle.get('team_features') or {}
                fixture_date = bundle.get('fixture_date')
                def adjuster(pool):
                    return [rest_days_adjustment(p, team_features.get(str(p['team']), {}),
                                                 fixture_date, 0.0) for p in pool]
            result = predictor(week, copy.deepcopy(players), copy.deepcopy(records),
                               copy.deepcopy(lookup), {}, model=model,
                               risk_profile='balanced', pool_adjuster=adjuster,
                               availability_policy=bundle.get('availability_policy', 'current'),
                               formation_policy=bundle.get('formation_policy',
                                   'legacy_pre39_v1' if bundle.get('availability_policy') == 'legacy_pre31a'
                                   else 'current_tff_v2'))
            result['model'] = name
            result['benchmark'] = {'variant': name, 'base_model': model,
                'sensitivity': .4 if name in ('uniform_xg', 'position_aware_xg') else 0.0,
                'rest_weight': 0.0, 'input_hash': input_hash,
                'batch_id': batch_id,
                'classification': 'control' if name == 'rest_days_control' else 'experimental'}
            outputs[name] = result
            statuses[name] = 'complete'
        except (ValueError, KeyError, TypeError, RuntimeError) as exc:
            statuses[name] = f'failed: {exc}'
    return {'batch_id': batch_id,
            'input_hash': input_hash, 'capture_timestamp': bundle['cutoff_utc'],
            'model_version': 'phase24b_v1', 'statuses': statuses,
            'status': 'complete' if len(outputs) == len(NAMES) else 'incomplete',
            'predictions': outputs if len(outputs) == len(NAMES) else {}}
