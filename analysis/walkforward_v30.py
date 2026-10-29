"""v3.0: conservative pre-deadline feature audit and playing-time diagnostics.

Default excludes target-week opponent from the post-match archive. Historical
player availability/prices still lack snapshots, so this is NOT a verified
point-in-time backtest. Experimental fixture mode is explicitly retrospective.
"""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from analysis.historical_backtest import STORE, number
from analysis.multiweek_backtest import MODELS, load_history
from analysis.walkforward_v27 import evaluate as evaluate_fixture
from analysis.walkforward_backtest import evaluate as evaluate_plain
from analysis.walkforward_v28 import candidate_rank


def minutes_audit(records, week, result):
    history = {str(p['id']): rows for p, rows in records}
    players = []
    for player in result['starting_xi']:
        rows = history.get(str(player['id']), [])
        previous = [r for r in rows if int(r['gameweekOrder']) < week]
        target = next((r for r in rows if int(r['gameweekOrder']) == week), None)
        prev_mins = [max(0, number(r.get('minutesPlayed'), 0)) for r in previous[-4:]]
        avg_minutes = round(mean(prev_mins), 1) if prev_mins else None
        actual_minutes = number(target.get('minutesPlayed')) if target else None
        players.append({'id': player['id'], 'name': player['name'],
                        'previous_four_avg_minutes': avg_minutes,
                        'target_minutes': actual_minutes,
                        'predicted_regular': avg_minutes is not None and avg_minutes >= 60,
                        'actual_played': actual_minutes is not None and actual_minutes > 0})
    known = [p for p in players if p['target_minutes'] is not None]
    return {'xi_with_known_minutes': len(known),
            'xi_did_not_play': sum(not p['actual_played'] for p in known),
            'xi_under_60_minutes': sum(p['target_minutes'] < 60 for p in known),
            'players': players}


def walk_forward(records, weeks=(5, 6, 7, 8, 9), min_participation=.25,
                 risk_penalty=.35, allow_retrospective_fixture=False, optimizer=None):
    weeks = tuple(weeks)
    if not weeks or list(weeks) != sorted(set(weeks)) or min(weeks) < 2:
        raise ValueError('Weeks must be ascending, distinct and >= 2')
    if not 0 <= min_participation <= 1 or risk_penalty < 0:
        raise ValueError('Invalid thresholds')
    candidates = {f'{name}__plain': (cfg, False) for name, cfg in MODELS.items()}
    if allow_retrospective_fixture:
        candidates.update({f'{name}__fixture': (cfg, True) for name, cfg in MODELS.items()})
    cache = {}
    for week in weeks:
        for name, (config, fixture) in candidates.items():
            print(f'GW{week}: {name}', flush=True)
            if fixture:
                result = evaluate_fixture(records, week, config, .5, min_participation, optimizer)
            else:
                result = evaluate_plain(records, week, config, min_participation, optimizer)
            cache[(week, name)] = result
    steps = []
    for index, week in enumerate(weeks):
        prior = weeks[:index]
        if not prior:
            steps.append({'week': week, 'training_weeks': [], 'selected_model': None,
                          'result': None, 'all_models': {n: {k: cache[(week, n)][k] for k in
                          ('predicted', 'actual', 'absolute_error')} for n in candidates}})
            continue
        def rank(name):
            past = [cache[(w, name)] for w in prior]
            return (-candidate_rank(past, risk_penalty),
                    mean(r['absolute_error'] for r in past), name)
        selected = min(candidates, key=rank)
        result = dict(cache[(week, selected)])
        result['minutes_audit'] = minutes_audit(records, week, result)
        steps.append({'week': week, 'training_weeks': list(prior),
                      'selected_model': selected, 'result': result,
                      'all_models': {n: {k: cache[(week, n)][k] for k in
                      ('predicted', 'actual', 'absolute_error')} for n in candidates}})
    scored = [s['result'] for s in steps if s['result'] and s['result']['actual'] is not None]
    summary = {'scored_weeks': len(scored)}
    if scored:
        summary.update(mean_actual=round(mean(r['actual'] for r in scored), 3),
                       total_actual=round(sum(r['actual'] for r in scored), 2),
                       raw_mae=round(mean(r['absolute_error'] for r in scored), 3),
                       xi_did_not_play=sum(r['minutes_audit']['xi_did_not_play'] for r in scored),
                       xi_under_60_minutes=sum(r['minutes_audit']['xi_under_60_minutes'] for r in scored))
    return {'created_utc': datetime.now(timezone.utc).isoformat(),
            'classification': 'RETROSPECTIVE / NOT POINT-IN-TIME VERIFIED',
            'fixture_mode': 'post-match opponent (experimental)' if allow_retrospective_fixture else 'disabled: no verified pre-deadline opponent snapshot',
            'player_calibration': 'disabled (v2.9 experiment regressed)',
            'captain_risk_penalty': 0,
            'selection_rule': 'Prior-week realized team score minus population SD risk penalty; raw MAE tie-break',
            'weeks': steps, 'summary': summary,
            'limitations': ['Player universe, availability and prices are not verified deadline snapshots.',
                            'Minutes audit uses target-week minutes only AFTER selection for diagnostics.',
                            'No injury/suspension pre-deadline snapshots.',
                            'No autosubs, chips or transfer penalties.',
                            'Post-match opponent identifiers used only with --allow-retrospective-fixture.']}


def save_report(report, store=STORE):
    folder = Path(store)
    folder.mkdir(parents=True, exist_ok=True)
    jp, cp = folder / 'walkforward_backtest_v30.json', folder / 'walkforward_backtest_v30.csv'
    jp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    with cp.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['week', 'model', 'actual', 'predicted', 'absolute_error',
                                                'formation', 'captain', 'xi_did_not_play', 'xi_under_60_minutes'])
        writer.writeheader()
        for step in report['weeks']:
            r = step['result']
            if r:
                writer.writerow({'week': step['week'], 'model': step['selected_model'],
                                 'actual': r['actual'], 'predicted': r['predicted'],
                                 'absolute_error': r['absolute_error'], 'formation': r['formation'],
                                 'captain': r['captain'],
                                 'xi_did_not_play': r['minutes_audit']['xi_did_not_play'],
                                 'xi_under_60_minutes': r['minutes_audit']['xi_under_60_minutes']})
    return jp, cp


def main():
    parser = argparse.ArgumentParser(description='v3.0 conservative walk-forward and minutes audit')
    parser.add_argument('--weeks', nargs='+', type=int, default=[5, 6, 7, 8, 9])
    parser.add_argument('--min-participation', type=float, default=.25)
    parser.add_argument('--risk-penalty', type=float, default=.35)
    parser.add_argument('--allow-retrospective-fixture', action='store_true')
    parser.add_argument('--collect', action='store_true')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    if args.collect:
        from analysis.historical_backtest import collect
        collect(force=args.force)
    records = load_history()
    report = walk_forward(records, args.weeks, args.min_participation, args.risk_penalty,
                          args.allow_retrospective_fixture)
    j, c = save_report(report)
    print('Summary:', report['summary'])
    print('JSON:', j, '\nCSV:', c)


if __name__ == '__main__':
    main()
