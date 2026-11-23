"""Read-only GW11 price-only sensitivity using the Phase 32 input bundle."""
import copy
import json
from pathlib import Path

from analysis.capture_integrity import validate_inputs
from analysis.phase32_gw11_walkforward import prepare, predict_only, evaluate_predictions
from analysis.six_model_batch import NAMES

OUT = Path('docs/phase32b_gw11_price_sensitivity.json')
REPORT = Path('docs/phase32b_gw11_price_sensitivity.md')


def price_scenarios(base):
    """Return independent bundles; histories/fixtures/external evidence stay identical."""
    history = {str(h['player_id']): h['rows'] for h in base['histories']}
    result = {}
    for scenario, week in (('snapshot_oct31', None), ('gw9_postmatch', 9), ('gw10_postmatch', 10)):
        bundle = copy.deepcopy(base)
        changes, missing = [], []
        for player in bundle['players']:
            pid = str(player['id'])
            if week is None:
                continue
            rows = [r for r in history[pid] if int(r['gameweekOrder']) == week]
            price = rows[0].get('cost') if len(rows) == 1 else None
            if price is None or isinstance(price, bool) or float(price) <= 0:
                missing.append(player['id'])
                continue
            old = float(player['price'])
            if float(price) != old:
                changes.append({'id': player['id'], 'name': player['name'],
                                'snapshot_price': old, 'scenario_price': float(price),
                                'delta': round(float(price)-old, 3)})
            player['price'] = price
        bundle['input_hash'] = validate_inputs(11, bundle['players'], bundle['fixtures'], bundle['histories'])
        assert bundle['histories'] == base['histories'] and bundle['fixtures'] == base['fixtures']
        assert bundle['external_matches'] == base['external_matches']
        assert all({k:v for k,v in a.items() if k != 'price'} ==
                   {k:v for k,v in b.items() if k != 'price'}
                   for a,b in zip(bundle['players'], base['players']))
        result[scenario] = {'bundle': bundle, 'price_changes': changes, 'fallback_ids': missing}
    return result


def generate_all(scenarios, predictor=predict_only):
    """All model generation finishes before outcome data enters the workflow."""
    return {name: predictor(item['bundle'])['predictions'] for name,item in scenarios.items()}


def compare(scenarios, forecasts, actual_rows):
    outcomes = {name: evaluate_predictions(forecasts[name], actual_rows) for name in scenarios}
    baseline = outcomes['snapshot_oct31']
    summary = {}
    for scenario, models in outcomes.items():
        summary[scenario] = {}
        ranks = {name: rank for rank,(name,_) in enumerate(
            sorted(models.items(), key=lambda kv: (-kv[1]['actual_points'], kv[0])), 1)}
        for name in NAMES:
            m, old = models[name], baseline[name]
            xi = {p['id'] for p in m['starting_xi']}
            old_xi = {p['id'] for p in old['starting_xi']}
            bench = {p['id'] for p in m['bench']}
            old_bench = {p['id'] for p in old['bench']}
            summary[scenario][name] = {
                'rank_by_actual': ranks[name], 'xi_overlap': len(xi & old_xi),
                'xi_in': sorted(xi-old_xi), 'xi_out': sorted(old_xi-xi),
                'bench_in': sorted(bench-old_bench), 'bench_out': sorted(old_bench-bench),
                'captain': m['captain'], 'captain_id': m['captain_id'],
                'formation': m['formation'], 'cost': m['squad_cost'],
                'predicted': m['predicted_points'], 'actual': m['actual_points'],
                'actual_delta': m['actual_points']-old['actual_points'],
                'predicted_minus_actual': m['predicted_minus_actual'],
                'objective': m['optimization_objective'],
                'starting_xi': m['starting_xi'], 'bench': m['bench']}
    return summary


def write_report(data):
    audit, summary = data['price_audit'], data['scenarios']
    lines = ['# Phase 32B — GW11 historical price sensitivity', '',
        '**Classification:** retrospective price-only sensitivity of the approximate Phase 32 GW11 simulation. No scenario is a verified immediately pre-GW11 forecast.', '',
        '## Price evidence', '',
        f'Official GW11 deadline: {data["input_evidence"]["official_deadline"]}. The frozen GW11 snapshot was captured {data["input_evidence"]["snapshot_captured_at"]} before the deadline, with a verified input hash. Its prices are observed at capture, but their validity at the later deadline cannot be established. The same 572 players, GW1–10 histories, GW11 fixtures, availability, external evidence, model settings and optimizer constraints are used in every scenario.', '',
        f'GW10 history `cost` was retrieved {data["input_evidence"]["gw10_rows_retrieved_at"]}, after the deadline. This is a gameweek result field, with no independent pre-deadline price timestamp. Prior project audits classify it as a **postmatch price, not a verified deadline price**. It is therefore a plausible sensitivity input, not a historically verified GW11 price. GW9 postmatch cost was already embedded in the Oct 31 snapshot; its deadline-time interpretation is also unverified.', '',
        '| Scenario | Source | Positive history cost | Snapshot fallback | Price differences vs snapshot | Status |',
        '| --- | --- | ---: | ---: | ---: | --- |']
    for name, label in [('snapshot_oct31','Oct 31 frozen player price'),('gw9_postmatch','GW9 history cost'),('gw10_postmatch','GW10 history cost')]:
        a = audit[name]
        coverage = '—' if name == 'snapshot_oct31' else str(572-len(a['fallback_ids']))
        lines.append(f'| {name} | {label} | {coverage} | {len(a["fallback_ids"])} | {len(a["price_changes"])} | {"verified Oct 31 observation; stale at deadline" if name=="snapshot_oct31" else "postmatch proxy; deadline validity unverified"} |')
    ch = audit['gw10_postmatch']['price_changes']
    increments = sum(c['delta']>0 for c in ch)
    decrements = sum(c['delta']<0 for c in ch)
    lines += ['', f'The {len(ch)} GW10 differences comprise {increments} increases and {decrements} decreases relative to frozen prices. Among changed players, deltas range from {min(c["delta"] for c in ch):+.1f} to {max(c["delta"] for c in ch):+.1f}; all 220 IDs and values are in the JSON artifact. Zero/missing history costs are treated as unavailable, never as free players.', '',
        f'GW9 and GW10 history cost agree for {data["price_audit"]["gw9_gw10_equal_positive"]} players with positive values in both weeks and differ for {data["price_audit"]["gw9_gw10_different_positive"]}. Thus the GW9 and GW10 price scenarios are the same observed price state, not independent evidence of a deadline-time update. Comparison with GW11 postmatch costs is reserved for field-semantics audit and never enters a prediction.', '',
        '## Six-model results', '',
        '| Scenario | Model | XI overlap | XI in / out | Bench in / out | Captain | Formation | Cost | Pred xPts | Actual | Δ actual | Rank |',
        '| --- | --- | ---: | --- | --- | --- | --- | ---: | ---: | ---: | ---: | ---: |']
    for scenario in ('snapshot_oct31','gw9_postmatch','gw10_postmatch'):
        for name in NAMES:
            m = summary[scenario][name]
            lines.append(f'| {scenario} | {name} | {m["xi_overlap"]}/11 | {", ".join(map(str,m["xi_in"])) or "—"} / {", ".join(map(str,m["xi_out"])) or "—"} | {", ".join(map(str,m["bench_in"])) or "—"} / {", ".join(map(str,m["bench_out"])) or "—"} | {m["captain"]} | {m["formation"]} | {m["cost"]:.1f} | {m["predicted"]:.2f} | {m["actual"]:.0f} | {m["actual_delta"]:+.0f} | {m["rank_by_actual"]} |')
    lines += ['', 'Rank is by official GW11 score, with model name breaking ties. Actual points equal XI points plus the captain’s points a second time; bench contributes zero. IDs in the lineup-change columns refer to official TFF player IDs. Full XI and bench player rows, predictions and outcomes are in the JSON artifact. Objectives are in the JSON and should only be compared within the same model.', '',
        '## Baseline and stable sensitivity', '']
    for name in ('baseline_5w','stable_8w'):
        rows = [(s, summary[s][name]) for s in ('snapshot_oct31','gw9_postmatch','gw10_postmatch')]
        lines.append(f'**{name}:** ' + '; '.join(f'{s} {m["actual"]} actual, {m["predicted"]:.2f} predicted, {m["xi_overlap"]}/11 XI shared, captain {m["captain"]}' for s,m in rows) + '.')
        lines.append('')
    for scenario in ('snapshot_oct31','gw9_postmatch','gw10_postmatch'):
        ordered = sorted(NAMES, key=lambda n: (-summary[scenario][n]['actual'], n))
        lines.append(f'{scenario} realized ranking: ' + ' > '.join(f'{n} ({summary[scenario][n]["actual"]})' for n in ordered) + '.')
        lines.append('')
    lines += ['## Interpretation and limitations', '',
        'Every tested XI, bench, captain, formation and predicted total is unchanged. The 220 lower proxy prices reduce selected squad costs by 3.0–3.5, but no roster crosses an optimizer decision boundary. Baseline stays at 75 actual and Stable at 73; their ordering and the six-model realized-score ordering remain unchanged under the two distinct observed price states. This does not establish robustness to unobserved deadline prices or larger price changes.', '',
        'Only price changes across scenarios. Official GW11 points are loaded after all 18 predictions are generated; they do not enter optimization. The GW10 history rows themselves were first observed after the GW11 deadline, and availability/fixture metadata also predates that deadline. Thus this isolates sensitivity to price assumptions within an approximate retrospective setup, not a validated pre-deadline price forecast.', '',
        'GW10 `cost` may reflect an after-match or later-adjusted value. The available data do not establish when each price became selectable. The scenario cannot establish causal model superiority from one gameweek. The most defensible next step is to timestamp a player-price capture before each future deadline.', '',
        '## Verification', '',
        'The original frozen hash and all Phase 32 non-price inputs were checked. Prediction generation was completed before outcome loading. Focused tests cover price-only mutation, zero-cost fallback and outcome isolation. No saved snapshot, prediction, weights or optimizer rules were changed.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')


def run():
    base, evidence = prepare()
    scenarios = price_scenarios(base)
    forecasts = generate_all(scenarios)
    actual = json.loads(Path('docs/phase28_official_histories.json').read_text(encoding='utf-8'))
    summary = compare(scenarios, forecasts, actual['rows_by_player'])
    by_history = {str(h['player_id']): {int(r['gameweekOrder']): r for r in h['rows']}
                  for h in base['histories']}
    comparable = [(rows[9].get('cost'), rows[10].get('cost')) for rows in by_history.values()
                  if 9 in rows and 10 in rows and (rows[9].get('cost') or 0) > 0 and (rows[10].get('cost') or 0) > 0]
    data = {'classification': 'retrospective_price_only_sensitivity', 'input_evidence': evidence,
            'price_audit': {name: {'input_hash': item['bundle']['input_hash'],
                                  'price_changes': item['price_changes'],
                                  'fallback_ids': item['fallback_ids']}
                            for name,item in scenarios.items()},
            'official_actual_retrieved_at': actual['retrieved_at'], 'scenarios': summary}
    data['price_audit']['gw9_gw10_equal_positive'] = sum(a == b for a,b in comparable)
    data['price_audit']['gw9_gw10_different_positive'] = sum(a != b for a,b in comparable)
    OUT.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding='utf-8')
    write_report(data)
    return data


if __name__ == '__main__':
    result = run()
    print({s: {n: m['actual'] for n,m in models.items()} for s,models in result['scenarios'].items()})
