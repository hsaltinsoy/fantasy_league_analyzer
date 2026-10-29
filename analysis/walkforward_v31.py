"""v3.1: strictly prior-round participation threshold experiments and fixture snapshot audit.

No target-week minutes, points or opponent IDs enter lineup construction.
A fixture snapshot is validated for provenance only; fixture factors are NOT applied.
"""
import argparse
import csv
import json
from datetime import datetime, timezone
from pathlib import Path
from statistics import mean

from analysis.historical_backtest import STORE
from analysis.multiweek_backtest import MODELS, load_history
from analysis.walkforward_backtest import evaluate
from analysis.walkforward_v28 import candidate_rank
from analysis.walkforward_v30 import minutes_audit


def audit_fixture_snapshot(path, weeks):
    if path is None:
        return {'status': 'not_provided', 'usable_for_prediction': False}
    raw = json.loads(Path(path).read_text(encoding='utf-8'))
    if not isinstance(raw, dict) or not isinstance(raw.get('weeks'), dict):
        raise ValueError('Fixture snapshot must have a weeks object')
    details = {}
    for week in weeks:
        entry = raw['weeks'].get(str(week))
        if entry is None:
            details[str(week)] = {'status': 'missing'}
            continue
        if not isinstance(entry, dict) or not isinstance(entry.get('matches'), list):
            raise ValueError(f'GW{week}: expected matches list')
        stamp = entry.get('captured_utc')
        deadline = entry.get('deadline_utc')
        valid_time = False
        if isinstance(stamp, str) and isinstance(deadline, str):
            try:
                captured = datetime.fromisoformat(stamp.replace('Z', '+00:00'))
                cutoff = datetime.fromisoformat(deadline.replace('Z', '+00:00'))
                valid_time = captured.tzinfo is not None and cutoff.tzinfo is not None and captured < cutoff
            except ValueError:
                pass
        matches = entry['matches']
        valid_matches = all(isinstance(m, dict) and m.get('home_club_id') is not None and
                            m.get('away_club_id') is not None and
                            str(m['home_club_id']) != str(m['away_club_id']) for m in matches)
        details[str(week)] = {'status': 'timestamp_before_deadline' if valid_time and valid_matches and matches else 'unverified',
                              'match_count': len(matches), 'has_source': bool(entry.get('source')),
                              'captured_before_deadline': valid_time, 'match_ids_valid': valid_matches}
    return {'status': 'audited_only', 'usable_for_prediction': False, 'weeks': details,
            'note': 'Timestamps are self-declared and do not independently prove capture time; no fixture factors applied.'}


def walk_forward(records, weeks=(5, 6, 7, 8, 9), thresholds=(.25, .45, .65),
                 risk_penalty=.35, optimizer=None, fixture_snapshot=None):
    weeks = tuple(weeks)
    thresholds = tuple(float(x) for x in thresholds)
    if not weeks or list(weeks) != sorted(set(weeks)) or min(weeks) < 2:
        raise ValueError('Weeks must be sorted unique integers >=2')
    if not thresholds or len(set(thresholds)) != len(thresholds) or any(not 0 <= x <= 1 for x in thresholds):
        raise ValueError('Thresholds must be unique within [0,1]')
    if risk_penalty < 0:
        raise ValueError('risk_penalty must be nonnegative')
    candidates = {f'{name}__p{int(t*100):02d}': (cfg, t) for t in thresholds for name, cfg in MODELS.items()}
    cache = {}
    for week in weeks:
        for name, (cfg, threshold) in candidates.items():
            print(f'GW{week}: {name}', flush=True)
            cache[(week, name)] = evaluate(records, week, cfg, threshold, optimizer)
    steps = []
    for i, week in enumerate(weeks):
        prior = weeks[:i]
        if prior:
            def rank(name):
                past = [cache[(w, name)] for w in prior]
                if any(r['actual'] is None for r in past):
                    raise ValueError('Missing prior actual points')
                return (-candidate_rank(past, risk_penalty), mean(r['absolute_error'] for r in past), name)
            selected = min(candidates, key=rank)
            result = dict(cache[(week, selected)])
            result['minutes_audit'] = minutes_audit(records, week, result)
        else:
            selected, result = None, None
        steps.append({'week': week, 'training_weeks': list(prior), 'selected_model': selected,
                      'selected_threshold': candidates[selected][1] if selected else None,
                      'result': result,
                      'all_models': {name: {k: cache[(week, name)][k] for k in ('predicted','actual','absolute_error')}
                                     for name in candidates}})
    scored = [s['result'] for s in steps if s['result'] and s['result']['actual'] is not None]
    return {'created_utc': datetime.now(timezone.utc).isoformat(),
            'classification': 'RETROSPECTIVE / NOT POINT-IN-TIME VERIFIED',
            'fixture_mode': 'disabled', 'fixture_snapshot_audit': audit_fixture_snapshot(fixture_snapshot, weeks),
            'thresholds': list(thresholds), 'selection_rule': 'Prior-week realized score minus risk penalty times SD; raw MAE tie-break',
            'weeks': steps,
            'summary': {'scored_weeks': len(scored),
                        'total_actual': round(sum(r['actual'] for r in scored),2),
                        'mean_actual': round(mean(r['actual'] for r in scored),3) if scored else None,
                        'raw_mae': round(mean(r['absolute_error'] for r in scored),3) if scored else None,
                        'xi_did_not_play': sum(r['minutes_audit']['xi_did_not_play'] for r in scored),
                        'xi_under_60_minutes': sum(r['minutes_audit']['xi_under_60_minutes'] for r in scored)},
            'limitations': ['No verified pre-deadline player universe, price, injury or suspension snapshots.',
                            'Fixture snapshots are audit-only, never applied to predictions.',
                            'Target-week minutes used exclusively in post-selection diagnostics.',
                            'No autosubs, chips or transfer penalties.',
                            'Small sample; changing thresholds may overfit.']}


def save_report(report, store=STORE):
    folder = Path(store)
    folder.mkdir(parents=True, exist_ok=True)
    jp, cp = folder/'walkforward_backtest_v31.json', folder/'walkforward_backtest_v31.csv'
    jp.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    with cp.open('w', newline='', encoding='utf-8-sig') as f:
        writer = csv.DictWriter(f, fieldnames=['week','model','threshold','actual','predicted','absolute_error','formation','captain','xi_did_not_play','xi_under_60_minutes'])
        writer.writeheader()
        for step in report['weeks']:
            r = step['result']
            if r:
                writer.writerow({'week':step['week'], 'model':step['selected_model'], 'threshold':step['selected_threshold'],
                                 'actual':r['actual'], 'predicted':r['predicted'], 'absolute_error':r['absolute_error'],
                                 'formation':r['formation'], 'captain':r['captain'],
                                 'xi_did_not_play':r['minutes_audit']['xi_did_not_play'],
                                 'xi_under_60_minutes':r['minutes_audit']['xi_under_60_minutes']})
    return jp, cp


def main():
    parser = argparse.ArgumentParser(description='v3.1 participation thresholds and fixture provenance audit')
    parser.add_argument('--weeks', nargs='+', type=int, default=[5,6,7,8,9])
    parser.add_argument('--thresholds', nargs='+', type=float, default=[.25,.45,.65])
    parser.add_argument('--risk-penalty', type=float, default=.35)
    parser.add_argument('--fixture-snapshot', type=Path)
    parser.add_argument('--collect', action='store_true')
    parser.add_argument('--force', action='store_true')
    args = parser.parse_args()
    if args.collect:
        from analysis.historical_backtest import collect
        collect(force=args.force)
    report = walk_forward(load_history(), args.weeks, args.thresholds, args.risk_penalty,
                          fixture_snapshot=args.fixture_snapshot)
    jp, cp = save_report(report)
    print('Summary:', report['summary'])
    print('JSON:', jp, '\nCSV:', cp)

if __name__ == '__main__':
    main()
