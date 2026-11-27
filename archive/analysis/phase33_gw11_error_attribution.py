"""Offline decision attribution from immutable Phase 32/32B artifacts."""
import json
from itertools import combinations
from pathlib import Path

from analysis.six_model_batch import NAMES

SOURCE = Path('docs/phase32_gw11_walkforward.json')
PRICES = Path('docs/phase32b_gw11_price_sensitivity.json')
HISTORIES = Path('docs/phase28_official_histories.json')
REPORT = Path('docs/phase33_gw11_error_attribution.md')
JSON_REPORT = Path('docs/phase33_gw11_error_attribution.json')


def player_index(model):
    return {p['id']: p for p in model['starting_xi']}


def pair_attribution(a, b):
    """A minus B; shared player points cancel exactly."""
    left, right = player_index(a), player_index(b)
    common = sorted(left.keys() & right.keys())
    only_a = sorted(left.keys() - right.keys())
    only_b = sorted(right.keys() - left.keys())
    left_only = sum(left[i]['actual_points'] for i in only_a)
    right_only = sum(right[i]['actual_points'] for i in only_b)
    xi_delta = left_only - right_only
    cap_delta = a['captain_extra_points'] - b['captain_extra_points']
    assert sum(p['actual_points'] for p in a['starting_xi']) == a['actual_xi_points']
    assert sum(p['actual_points'] for p in b['starting_xi']) == b['actual_xi_points']
    assert a['actual_points'] == a['actual_xi_points'] + a['captain_extra_points']
    assert b['actual_points'] == b['actual_xi_points'] + b['captain_extra_points']
    assert xi_delta == a['actual_xi_points'] - b['actual_xi_points']
    assert xi_delta + cap_delta == a['actual_points'] - b['actual_points']
    def detail(i, model):
        p = model[i]
        return {'id': i, 'name': p['name'], 'position': p['position'],
                'predicted': p['predicted_xpts'], 'actual': p['actual_points']}
    return {'shared': [detail(i,left) for i in common],
            'a_only': [detail(i,left) for i in only_a],
            'b_only': [detail(i,right) for i in only_b],
            'a_only_actual': left_only, 'b_only_actual': right_only,
            'xi_delta': xi_delta, 'captain_delta': cap_delta,
            'substitution_delta': 0, 'total_delta': a['actual_points']-b['actual_points']}


def projection_rank(model, pid):
    xi = sorted(model['starting_xi'], key=lambda p: (-p['predicted_xpts'], p['id']))
    return next((n for n,p in enumerate(xi, 1) if p['id'] == pid), None)


def unique_errors(models, sign):
    by_player = {}
    for name, model in models.items():
        for slot, group in [('XI', model['starting_xi']), ('bench', model['bench'])]:
            for p in group:
                error = p['difference']
                if (sign == 'over' and error <= 0) or (sign == 'under' and error >= 0):
                    continue
                previous = by_player.get(p['id'])
                if previous is None or abs(error) > abs(previous['difference']):
                    by_player[p['id']] = {**p, 'model': name, 'slot': slot}
    return sorted(by_player.values(), key=lambda p: -abs(p['difference']))[:5]


def render(data, prices, histories):
    models = data['models']
    actual_rows = {int(pid): next((r for r in rows if int(r['gameweekOrder']) == 11), None)
                   for pid,rows in histories['rows_by_player'].items()}
    pairs = {(a,b): pair_attribution(models[a], models[b]) for a,b in combinations(NAMES,2)}
    lines = ['# Phase 33 — GW11 model decision and error attribution', '',
        '**Scope:** offline analysis of Phase 32 and 32B retrospective artifacts. The GW10 history and deadline-time metadata limitations remain; these are not genuine prospective six-model forecasts.', '',
        '## Score reconciliation', '',
        '| Model | XI actual | Captain extra | Substitution effect | Recorded actual |',
        '| --- | ---: | ---: | ---: | ---: |']
    for name in NAMES:
        m = models[name]
        lines.append(f'| {name} | {m["actual_xi_points"]} | {m["captain_extra_points"]} | 0 | {m["actual_points"]} |')
    lines += ['', 'Bench players did not score in the Phase 32 fresh-squad evaluation; no automatic substitution was applied. Every row reconciles as XI + captain extra.', '',
        '## Every pair of starting XIs', '',
        'Each row is **first model minus second model**. Common player points cancel. XI difference equals first-only actual points minus second-only actual points; total gap also includes the captain bonus. No substitution effect occurred.', '',
        '| First / second | Shared | First-only actual | Second-only actual | XI Δ | Captain Δ | Total Δ |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: |']
    for (a,b), p in pairs.items():
        lines.append(f'| {a} / {b} | {len(p["shared"])}/11 | {p["a_only_actual"]} | {p["b_only_actual"]} | {p["xi_delta"]:+} | {p["captain_delta"]:+} | {p["total_delta"]:+} |')
    lines += ['', '### Player identities and projections for each pair', '',
        'Each entry is `player (ID): predicted xPts / actual GW11 points`. Shared players are listed so the full XI overlap is inspectable.', '']
    def fmt(rows):
        return ', '.join(f'{p["name"]} ({p["id"]}): {p["predicted"]:.2f} / {p["actual"]}' for p in rows) or 'none'
    for (a,b), p in pairs.items():
        lines += [f'**{a} vs {b}** — shared: {fmt(p["shared"])}.', '',
                  f'{a} only: {fmt(p["a_only"])}. {b} only: {fmt(p["b_only"])}. Captains: {models[a]["captain"]} (+{models[a]["captain_extra_points"]}) vs {models[b]["captain"]} (+{models[b]["captain_extra_points"]}).', '']
    lines += ['## Osimhen and forward choices', '',
        'Osimhen (TFF 507) played **0 minutes** and scored **0 official points** in GW11. This is a verified nonappearance. The source artifacts do not contain an ex-ante minute forecast, so the precise minutes forecast error cannot be measured.', '',
        '| Model | Osimhen xPts | Selected | Other starting forwards (actual) |',
        '| --- | ---: | --- | --- |']
    for name in NAMES:
        m = models[name]
        p = next((p for p in m['starting_xi'] + m['bench'] if p['id'] == 507), None)
        status = 'XI' if any(p['id']==507 for p in m['starting_xi']) else 'bench' if p else 'out'
        others = ', '.join(f'{p["name"]} ({p["actual_points"]})' for p in m['starting_xi'] if p['position']=='FWD' and p['id'] != 507)
        lines.append(f'| {name} | {p["predicted_xpts"]:.3f} | {status} | {others} |' if p else f'| {name} | unavailable in selected 15 | {status} | {others} |')
    lines += ['', 'Baseline and Stable started Orban (5), Shomurodov (2), and Benedyczak (7), for 14 forward points. Short Form and the zero-weight Rest control started Orban (5) and Osimhen (0), for 5; Uniform xG started Orban (5), Shomurodov (2), and Osimhen (0), for 7; Position-aware xG started Orban (5) and Osimhen (0), for 5. The 7-point Benedyczak versus 0-point Osimhen contrast is observed, but it is not a standalone causal substitution: formation and other positions also changed.', '',
        '## Salah captain decision', '',
        'The rank below is Salah’s **uncaptained xPts rank within the selected XI**. Phase 32 did not persist the optimizer’s separate captain-bonus alternatives; therefore this is an observable projection rank, not a verified internal captain ranking.', '',
        '| Model | Salah xPts | XI xPts rank | Captain | Highest XI xPts | Actual captain extra |',
        '| --- | ---: | ---: | --- | --- | ---: |']
    for name in NAMES:
        m = models[name]
        salah = next(p for p in m['starting_xi'] if p['id'] == 12)
        top = max(m['starting_xi'], key=lambda p:p['predicted_xpts'])
        lines.append(f'| {name} | {salah["predicted_xpts"]:.3f} | {projection_rank(m,12)}/11 | {"yes" if m["captain_id"]==12 else "no"} | {top["name"]} ({top["predicted_xpts"]:.3f}) | {m["captain_extra_points"]} |')
    lines += ['', 'Salah scored 10 official points. Baseline and Stable doubled him, adding **10** to each XI. The four other variants doubled Muçi, who scored 3, adding **3**. Thus the observed captain-choice component of each Baseline/Stable gap against those variants is **+7**. Salah’s higher projected XI xPts in Baseline/Stable and Muçi’s higher projection in the other variants are consistent with the captain choices; exact optimizer tie-break and risk-adjusted captain scores were not saved in these artifacts.', '',
        '## Largest selected-player errors', '',
        'Errors are predicted player xPts minus actual points, before captain doubling. The five rows in each direction use distinct TFF player IDs and show the most extreme model/player observation for each ID.', '',
        '| Direction | Player | Model | Slot | Predicted | Actual | Error | Minutes |',
        '| --- | --- | --- | --- | ---: | ---: | ---: | ---: |']
    for direction, sign in [('Over','over'),('Under','under')]:
        for p in unique_errors(models,sign):
            lines.append(f'| {direction} | {p["name"]} ({p["id"]}) | {p["model"]} | {p["slot"]} | {p["predicted_xpts"]:.2f} | {p["actual_points"]} | {p["difference"]:+.2f} | {p["actual_minutes"]} |')
    lines += ['', '### Observed match context for these errors', '',
        '| Player | Opponent | Venue | Result | Goals | Assists | Clean sheet | Bonus |',
        '| --- | --- | --- | --- | ---: | ---: | ---: | ---: |']
    seen = set()
    for p in unique_errors(models,'over') + unique_errors(models,'under'):
        if p['id'] in seen:
            continue
        seen.add(p['id'])
        r = actual_rows.get(p['id'])
        if r is None:
            continue
        lines.append(f'| {p["name"]} ({p["id"]}) | {r.get("opponentClubName", "—")} | {r.get("homeAway", "—")} | {r.get("result", "—")} | {r.get("goals", "—")} | {r.get("assists", "—")} | {r.get("cleanSheets", "—")} | {r.get("bonus", "—")} |')
    lines += ['', '## Mechanisms and evidential limits', '']
    zero = sorted({p['id']:p for m in models.values() for p in m['starting_xi'] if p['actual_minutes']==0}.values(), key=lambda p:-p['predicted_xpts'])
    lines += ['**Minutes:** ' + (', '.join(f'{p["name"]} ({p["id"]}, up to {max(q["predicted_xpts"] for m in models.values() for q in m["starting_xi"] if q["id"]==p["id"]):.2f} xPts)' for p in zero) if zero else 'No selected zero-minute players') + ' earned zero minutes. Their nonappearance directly explains their realized zero, while the reason for nonappearance and pre-deadline knowability are unverified. Other differences could reflect fantasy events or minutes; projected minutes were not saved.', '',
        '**Fixtures:** All models used the same frozen GW11 fixture inputs. Outcome rows contain actual opponent and result, but no saved per-player fixture multiplier or counterfactual projection without fixtures. Match outcomes and fantasy clean sheets can explain realized point components; they cannot establish that fixture weighting caused the model gap.', '',
        '**xG adjustments:** Uniform and position-aware variants altered short-form projections using 81 pre-snapshot team-level external matches. Uniform scored 58 and position-aware 57 versus short-form 57. Their XI changes and captain choices are tabulated above. These are observed one-week differences; they do not identify an xG effect apart from optimizer interactions and do not establish long-run xG value.', '',
        '**Prices:** Phase 32B tested the frozen Oct 31 price and the GW9/GW10 postmatch cost proxy. All XIs, benches, captains, predicted totals and realized ranking were unchanged. The postmatch cost is not a verified deadline price.', '',
        '## Prioritized improvements', '',
        '1. Capture official price and availability snapshots shortly before every deadline, with source and timestamp. The retrospective metadata gap limits the strength of every GW11 explanation.',
        '2. Record predicted participation/minutes and the optimizer’s captain-bonus alternatives in future batch artifacts. This allows direct minutes-error and captain-choice audits.',
        '3. Backtest participation and captain selection across many completed gameweeks before changing thresholds or weights. GW11 alone cannot justify tuning.',
        '4. Preserve fixture-feature and xG adjustment provenance per player so future differences can be decomposed without refetching or inferring.', '',
        '## Verification', '',
        'Read-only analysis of existing JSON artifacts; no live API call or prediction replay. Every model total and every pairwise score gap was asserted to reconcile exactly. Focused tests cover pairwise accounting and unique-player error selection. Frozen predictions and production weights were not changed.', '']
    REPORT.write_text('\n'.join(lines), encoding='utf-8')
    return pairs


def run():
    data = json.loads(SOURCE.read_text(encoding='utf-8'))
    prices = json.loads(PRICES.read_text(encoding='utf-8'))
    histories = json.loads(HISTORIES.read_text(encoding='utf-8'))
    assert set(data['models']) == set(NAMES)
    assert prices['scenarios']['snapshot_oct31']['baseline_5w']['actual'] == data['models']['baseline_5w']['actual_points']
    pairs = render(data, prices, histories)
    structured = {'classification': 'approximate_retrospective_simulation',
        'scoring_rule': 'XI official points plus captain points once; no autosub in project evaluator',
        'source_artifacts': [str(SOURCE), str(PRICES), str(HISTORIES)],
        'limitations': data['warnings'],
        'models': data['models'],
        'pairwise': {f'{a}__vs__{b}': value for (a,b),value in pairs.items()},
        'largest_overpredictions': unique_errors(data['models'], 'over'),
        'largest_underpredictions': unique_errors(data['models'], 'under'),
        'high_actual_not_in_any_xi': data['high_actual_not_in_any_xi'],
        'saved_gw11_predictions_separate': {'short_form_3w_actual': 57, 'stable_8w_actual': 76}}
    JSON_REPORT.write_text(json.dumps(structured, indent=2, ensure_ascii=False), encoding='utf-8')
    return pairs


if __name__ == '__main__':
    print(f'{len(run())} model pairs reconciled')
