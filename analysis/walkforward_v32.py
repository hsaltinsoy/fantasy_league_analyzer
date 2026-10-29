"""v3.2 pre-deadline fixture snapshot ablation (no target-week opponent lookup).

Snapshot is supplied externally. Timestamps alone are NOT independent proof of provenance.
Missing/invalid fixtures fail closed. All opponent strength data is from prior rounds.
"""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from analysis.historical_backtest import STORE
from analysis.multiweek_backtest import MODELS, load_history
from analysis.walkforward_backtest import evaluate as evaluate_plain, week_pool
from analysis.walkforward_v27 import fixture_multipliers
from analysis.walkforward_v28 import candidate_rank
from analysis.walkforward_v30 import minutes_audit


def load_snapshots(path, weeks, allow_reconstructed=False):
    if path is None:
        raise ValueError('Provide --fixture-snapshot with pre-deadline fixture data; fixture mode will not guess opponents.')
    obj = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(obj, dict) or not isinstance(obj.get('weeks'), dict):
        raise ValueError('Snapshot must contain a weeks object')
    reconstructed = 'RETROSPECTIVE' in str(obj.get('classification', '')).upper() or 'NO_PREDEADLINE' in str(obj.get('classification', '')).upper()
    if reconstructed and not allow_reconstructed:
        raise ValueError('Reconstructed fixtures require --allow-reconstructed; never treat them as pre-deadline snapshots')
    maps = {}
    for week in weeks:
        entry = obj['weeks'].get(str(week))
        if not isinstance(entry, dict):
            raise ValueError(f'GW{week}: missing fixture snapshot')
        if reconstructed:
            if entry.get('classification') != 'RETROSPECTIVE_FIXTURE_RECONSTRUCTION_NOT_PREDEADLINE_SNAPSHOT':
                raise ValueError(f'GW{week}: unexpected reconstructed provenance')
            matches = entry.get('matches')
            if not isinstance(matches, list) or len(matches) != 9:
                raise ValueError(f'GW{week}: expected 9 reconstructed matches')
            lookup = {}
            for match in matches:
                home, away = str(match.get('home_club_id_candidate', '')).strip(), str(match.get('away_club_id_candidate', '')).strip()
                if not home.isdigit() or not away.isdigit() or home == away or home in lookup or away in lookup:
                    raise ValueError(f'GW{week}: duplicate or invalid inferred club ID')
                lookup[home], lookup[away] = away, home
            if len(lookup) != 18 or not entry.get('source'):
                raise ValueError(f'GW{week}: incomplete reconstructed fixtures')
            maps[week] = lookup
            continue
        try:
            captured = datetime.fromisoformat(entry['captured_utc'].replace('Z', '+00:00'))
            deadline = datetime.fromisoformat(entry['deadline_utc'].replace('Z', '+00:00'))
        except (KeyError, ValueError, AttributeError) as exc:
            raise ValueError(f'GW{week}: invalid timestamps') from exc
        if captured.tzinfo is None or deadline.tzinfo is None or captured >= deadline:
            raise ValueError(f'GW{week}: snapshot must be dated before deadline with timezone')
        if not entry.get('source'):
            raise ValueError(f'GW{week}: source required')
        matches = entry.get('matches')
        if not isinstance(matches, list) or not matches:
            raise ValueError(f'GW{week}: matches missing')
        lookup = {}
        for match in matches:
            home, away = str(match.get('home_club_id', '')).strip(), str(match.get('away_club_id', '')).strip()
            if not home or not away or home == away or home in lookup or away in lookup:
                raise ValueError(f'GW{week}: invalid or duplicate team fixture')
            lookup[home], lookup[away] = away, home
        maps[week] = lookup
    return maps


def evaluate_fixture(records, week, config, opponents, fixture_weight=.5, min_probability=.25, optimizer=None):
    if optimizer is None:
        from analysis.optimizer import optimize
        optimizer = optimize
    if not 0 <= fixture_weight <= 1:
        raise ValueError('fixture_weight must be within [0,1]')
    pool, actual, coverage = week_pool(records, week, config, min_probability)
    factors = fixture_multipliers(records, week)
    # Explicit mapping is mandatory. Current team membership is NOT point-in-time verified.
    missing_teams = sorted({str(p['team']) for p in pool if str(p['team']) not in opponents})
    if missing_teams:
        raise ValueError(f'GW{week}: snapshot missing teams for eligible players: {missing_teams[:12]}')
    applied = 0
    for p in pool:
        opponent = opponents[str(p['team'])]
        factor = factors.get((opponent, p['position']), 1.)
        applied += (opponent, p['position']) in factors
        p['opponent_club_id'] = opponent
        p['fixture_factor'] = round(1 + fixture_weight * (factor - 1), 4)
        p['xpts'] = round(max(.1, p['xpts'] * p['fixture_factor']), 3)
    if len(pool) < 15:
        raise ValueError(f'GW{week}: insufficient eligible players')
    result = optimizer(pool)
    if 'error' in result:
        raise ValueError(result['error'])
    xi, captain = result['starting_xi'], result['captain']
    missing = [p['id'] for p in xi if actual.get(str(p['id'])) is None]
    score = None if missing else round(sum(actual[str(p['id'])] * (2 if str(p['id']) == str(captain['id']) else 1) for p in xi), 2)
    coverage.update({'fixture_factor_available': applied, 'fixture_factor_neutral': len(pool)-applied,
                     'snapshot_team_coverage': len(pool)})
    return {'week': week, 'formation': result['formation'], 'captain': captain['name'],
            'predicted': result['expected_points'], 'actual': score,
            'absolute_error': None if score is None else round(abs(result['expected_points']-score), 2),
            'budget': result['squad_cost'], 'eligible_players': len(pool), 'coverage': coverage,
            'missing_actual_ids': missing,
            'starting_xi': [{'id': p['id'], 'name': p['name'], 'position': p['position'], 'xpts': p['xpts'],
                             'actual_points': actual.get(str(p['id'])), 'captain': str(p['id']) == str(captain['id']),
                             'participation_proxy': p['participation_proxy'], 'opponent_club_id': p['opponent_club_id'],
                             'fixture_factor': p['fixture_factor']} for p in xi],
            'bench': [{'id': p['id'], 'name': p['name'], 'position': p['position'], 'xpts': p['xpts'],
                       'actual_points': actual.get(str(p['id']))} for p in result['squad'] if p['id'] not in {x['id'] for x in xi}],
            'formation_comparison': result['formation_comparison']}


def walk_forward(records, snapshots, weeks=(5,6,7,8,9), weights=(0., .5), risk_penalty=.35, optimizer=None, reconstructed=False):
    weeks = tuple(weeks)
    if not weeks or sorted(set(weeks)) != list(weeks) or min(weeks) < 2:
        raise ValueError('Weeks must be sorted unique >=2')
    if not weights or len(set(weights)) != len(weights) or any(not 0 <= w <= 1 for w in weights):
        raise ValueError('Weights must be unique in [0,1]')
    if any(w not in snapshots for w in weeks):
        raise ValueError('Missing fixture snapshot week')
    candidates = {f'{name}__f{int(w*100):03d}': (cfg, w) for name, cfg in MODELS.items() for w in weights}
    cache = {}
    for week in weeks:
        for name, (config, weight) in candidates.items():
            print(f'GW{week}: {name}', flush=True)
            if weight == 0:
                cache[(week,name)] = evaluate_plain(records, week, config, .25, optimizer)
            else:
                cache[(week,name)] = evaluate_fixture(records, week, config, snapshots[week], weight, .25, optimizer)
    steps = []
    for i, week in enumerate(weeks):
        prior = weeks[:i]
        if prior:
            def rank(name):
                past = [cache[(w,name)] for w in prior]
                if any(r['actual'] is None for r in past):
                    raise ValueError('Missing prior actuals')
                return (-candidate_rank(past, risk_penalty), mean(r['absolute_error'] for r in past), name)
            selected = min(candidates, key=rank)
            result = dict(cache[(week,selected)])
            result['minutes_audit'] = minutes_audit(records, week, result)
        else:
            selected, result = None, None
        steps.append({'week':week, 'training_weeks':list(prior), 'selected_model':selected,
                      'fixture_weight':candidates[selected][1] if selected else None, 'result':result,
                      'all_models':{name:{k:cache[(week,name)][k] for k in ('predicted','actual','absolute_error')}
                                    for name in candidates}})
    scored = [s['result'] for s in steps if s['result'] and s['result']['actual'] is not None]
    return {'created_utc':datetime.now(timezone.utc).isoformat(),
            'classification':'RETROSPECTIVE RECONSTRUCTION / UNVERIFIED CLUB IDS / NOT POINT-IN-TIME' if reconstructed else 'RETROSPECTIVE / NOT POINT-IN-TIME VERIFIED',
            'fixture_mode':'retrospective_reconstructed_UNVERIFIED_CLUB_IDS' if reconstructed else 'external_snapshot_required',
            'selection_rule':'prior-week actual score minus risk penalty * SD; MAE tie break',
            'weeks':steps, 'summary':{'scored_weeks':len(scored),
                'total_actual':round(sum(r['actual'] for r in scored),2),
                'mean_actual':round(mean(r['actual'] for r in scored),3) if scored else None,
                'raw_mae':round(mean(r['absolute_error'] for r in scored),3) if scored else None},
            'limitations':['Reconstructed fixtures were assembled after the matches; team IDs inferred from current rosters.' if reconstructed else 'Snapshot timestamps and source are self-reported, not independently verified.',
                           'Current player-to-team mapping and historical prices are not point-in-time verified.',
                           'Fixture factor is based on historical fantasy points conceded, not actual xG or odds.',
                           'No autosubs, chips or transfer penalties. Small backtest sample.']}


def save_report(report, store=STORE):
    folder = Path(store)
    folder.mkdir(parents=True, exist_ok=True)
    jp, cp = folder/'walkforward_backtest_v32.json', folder/'walkforward_backtest_v32.csv'
    jp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    with cp.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['week','model','fixture_weight','actual','predicted','absolute_error','formation','captain'])
        writer.writeheader()
        for step in report['weeks']:
            r = step['result']
            if r:
                writer.writerow({'week':step['week'],'model':step['selected_model'],'fixture_weight':step['fixture_weight'],
                                 **{k:r[k] for k in ('actual','predicted','absolute_error','formation','captain')}})
    return jp, cp


def main():
    parser = argparse.ArgumentParser(description='v3.2 fixture snapshot ablation')
    parser.add_argument('--weeks', nargs='+', type=int, default=[5,6,7,8,9])
    parser.add_argument('--fixture-snapshot', type=Path, required=True)
    parser.add_argument('--allow-reconstructed', action='store_true', help='EXPLORATORY ONLY: reconstructed fixtures, inferred club IDs, not point-in-time')
    parser.add_argument('--weights', nargs='+', type=float, default=[0.,.5])
    parser.add_argument('--risk-penalty', type=float, default=.35)
    args = parser.parse_args()
    snapshots = load_snapshots(args.fixture_snapshot, args.weeks, allow_reconstructed=args.allow_reconstructed)
    report = walk_forward(load_history(), snapshots, args.weeks, args.weights, args.risk_penalty, reconstructed=args.allow_reconstructed)
    jp, cp = save_report(report)
    print('Summary:',report['summary'],'\nJSON:',jp,'\nCSV:',cp)

if __name__ == '__main__':
    main()
