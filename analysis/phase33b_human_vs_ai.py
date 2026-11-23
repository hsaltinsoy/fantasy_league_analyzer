"""Offline comparison of a reported predeadline human XI with Phase 32 replays."""
import json
from collections import Counter
from pathlib import Path

XI = [130, 120, 94, 27, 212, 176, 281, 877, 507, 148, 593]
BENCH = [216, 277, 597, 4]
CAPTAIN = 176
SUBSTITUTE = 277
MODELS = ('baseline_5w','short_form_3w','stable_8w','uniform_xg','position_aware_xg','rest_days_control')


def calculate_human(actual):
    xi = sum(actual[i]['points'] for i in XI)
    captain = actual[CAPTAIN]['points']
    substitute = actual[SUBSTITUTE]['points']
    return {'xi_points': xi, 'captain_extra': captain,
            'project_scoring_total': xi + captain,
            'murillo_substitution_points': substitute,
            'conditional_substitution_total': xi + captain + substitute,
            'reported_total': 105,
            'unreconciled_after_murillo': 105 - xi - captain - substitute}


def compare(human, model):
    model_xi = {p['id']: p for p in model['starting_xi']}
    shared = sorted(set(XI) & set(model_xi))
    human_only = sorted(set(XI) - set(model_xi))
    model_only = sorted(set(model_xi) - set(XI))
    human_only_points = sum(human[i]['points'] for i in human_only)
    model_only_points = sum(model_xi[i]['actual_points'] for i in model_only)
    xi_delta = human_only_points - model_only_points
    captain_delta = human[CAPTAIN]['points'] - model['captain_extra_points']
    assert xi_delta == sum(human[i]['points'] for i in XI) - model['actual_xi_points']
    return {'shared_ids': shared, 'human_only_ids': human_only,
            'model_only_ids': model_only, 'human_only_points': human_only_points,
            'model_only_points': model_only_points, 'xi_delta': xi_delta,
            'captain_delta': captain_delta, 'project_scoring_gap': xi_delta + captain_delta,
            'conditional_murillo_gap': xi_delta + captain_delta + human[SUBSTITUTE]['points'],
            'reported_105_gap': 105-model['actual_points']}


def run():
    players = {int(p['id']): p for p in json.loads(Path('historical_data/players.json').read_text(encoding='utf-8'))}
    rows = json.loads(Path('docs/phase28_official_histories.json').read_text(encoding='utf-8'))['rows_by_player']
    actual = {i: next(r for r in rows[str(i)] if int(r['gameweekOrder']) == 11) for i in XI+BENCH}
    phase32 = json.loads(Path('docs/phase32_gw11_walkforward.json').read_text(encoding='utf-8'))
    models = phase32['models']
    human = calculate_human(actual)
    human['archive_squad_cost'] = sum(float(players[i]['price']) for i in XI+BENCH)
    human['archive_club_counts'] = dict(Counter(str(players[i]['club_id']) for i in XI+BENCH))
    assert max(human['archive_club_counts'].values()) <= 3
    comparisons = {name: compare(actual, models[name]) for name in MODELS}
    detail = {str(i): {'id': i, 'name': players[i]['name'], 'position': players[i]['position'],
                       'club_id': players[i]['club_id'], 'points': actual[i]['points'],
                       'minutes': actual[i]['minutesPlayed'], 'price_archive': players[i]['price']}
              for i in XI+BENCH}
    result = {'classification': 'human_reported_predeadline_vs_approximate_retrospective_models',
              'human_selection_provenance': 'user assertion; no independently timestamped lineup export',
              'human_formation': '3-4-3', 'xi_ids': XI, 'bench_ids': BENCH,
              'captain_id': CAPTAIN, 'vice_captain_id': 507, 'reported_auto_sub_id': SUBSTITUTE,
              'players': detail, 'human_scoring': human, 'comparisons': comparisons,
              'model_results': models,
              'official_rules_url': 'https://tfffantezilig.com/yardim?tab=kurallar-1',
              'warnings': phase32['warnings'] + ['No timestamped user lineup export or account-level scoring ledger supplied',
                  'Local player archive is used only for identity; its prices are not deadline verified']}
    Path('docs/phase33b_human_vs_ai.json').write_text(json.dumps(result, indent=2, ensure_ascii=False), encoding='utf-8')
    render(result, players)
    return result


def render(data, players):
    h = data['human_scoring']
    label = lambda i: f'{players[i]["name"]} ({i})'
    lines = ['# Phase 33B — GW11 human vs AI decisions', '',
        '**Classification:** user-reported genuine pre-deadline selection versus six approximate retrospective model replays. The human selection time is user-attested; no timestamped lineup export was supplied.', '',
        '## Human squad and official results', '',
        '| Role | Position | Player (TFF ID) | Club ID | GW11 minutes | Official points |',
        '| --- | --- | --- | ---: | ---: | ---: |']
    for i in data['xi_ids'] + data['bench_ids']:
        p = data['players'][str(i)]
        role = 'Captain' if i==CAPTAIN else 'Vice-captain' if i==507 else 'Reported auto-sub' if i==SUBSTITUTE else 'XI' if i in XI else 'Bench'
        lines.append(f'| {role} | {p["position"]} | {label(i)} | {p["club_id"]} | {p["minutes"]} | {p["points"]} |')
    lines += ['', f'User formation: **3-4-3**. Starting XI official points: **{h["xi_points"]}**. Greenwood captain extra: **+{h["captain_extra"]}**. Project evaluator total (XI + captain): **{h["project_scoring_total"]}**. Murillo’s reported automatic substitution: **+{h["murillo_substitution_points"]}**, yielding **{h["conditional_substitution_total"]}** if the substitution applies without removing any nonzero XI points. User-reported official total: **105**. Remaining difference: **{h["unreconciled_after_murillo"]:+}**.', '',
        'The project evaluator counts XI plus captain once more and has no auto-substitution, manager-card or Nostradamus scoring implementation. The [official TFF rules](https://tfffantezilig.com/yardim?tab=kurallar-1) say a zero-minute starter is replaced by a playing bench player in bench order when the resulting formation is legal; captain points are doubled. Murillo is the first outfield substitute, played 70 minutes, and replacing Osimhen makes a legal 4-4-2 with two forwards. Thus the official scoring rule supports the +5 substitution. The arithmetic exactly reconciles 105 without additional card or Nostradamus points; account-level ledger evidence was not supplied to independently exclude such adjustments.', '',
        '## Six model comparisons', '',
        'Human minus model. XI delta is human-only player points minus model-only player points; shared players cancel. Captain delta is Greenwood’s extra points minus the model captain’s extra points. Murillo is a conditional extra and is not included in the project-scoring gap.', '',
        '| Model | Shared XI | Human-only pts | Model-only pts | XI Δ | Captain Δ | Project gap | With Murillo | Reported 105 gap |',
        '| --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for name in MODELS:
        c = data['comparisons'][name]
        lines.append(f'| {name} | {len(c["shared_ids"])}/11 | {c["human_only_points"]} | {c["model_only_points"]} | {c["xi_delta"]:+} | {c["captain_delta"]:+} | {c["project_scoring_gap"]:+} | {c["conditional_murillo_gap"]:+} | {c["reported_105_gap"]:+} |')
    lines += ['', '### Exact lineup differences', '']
    for name in MODELS:
        c = data['comparisons'][name]
        model = data['model_results'][name]
        model_xi = {p['id']:p for p in model['starting_xi']}
        lines += [f'**{name}** — shared: ' + ', '.join(f'{label(i)} {data["players"][str(i)]["points"]} actual / {model_xi[i]["predicted_xpts"]:.2f} xPts' for i in c['shared_ids']) + '.', '',
            'Human only: ' + ', '.join(f'{label(i)} {data["players"][str(i)]["points"]} pts' for i in c['human_only_ids']) + '. Model only: ' + ', '.join(f'{label(i)} {model_xi[i]["actual_points"]} actual / {model_xi[i]["predicted_xpts"]:.2f} xPts' for i in c['model_only_ids']) + '.', '',
            f'Model captain {model["captain"]} added {model["captain_extra_points"]}; Greenwood added {h["captain_extra"]}. Model formation {model["formation"]}, bench: ' + ', '.join(f'{p["name"]} ({p["id"]}) {p["actual_points"]} actual / {p["predicted_xpts"]:.2f} xPts, {p["actual_minutes"]} min' for p in model['bench']) + '.', '']
    lines += ['## Decisions and evidence', '',
        f'Greenwood scored **{data["players"]["176"]["points"]}**; his captaincy added the same amount beyond his XI score. The models captained Salah (10 actual) or Muçi (3 actual). The human captain advantage is therefore +{h["captain_extra"]-10} against Baseline/Stable and +{h["captain_extra"]-3} against the other four models. This is an observed outcome, not evidence Greenwood was predictably the better captain before the deadline.', '',
        f'Osimhen played **{data["players"]["507"]["minutes"]} minutes** and scored **{data["players"]["507"]["points"]}**. Four models started him; Baseline and Stable did not. His zero is present in the human XI and those model XIs. Under the [official substitution rule](https://tfffantezilig.com/yardim?tab=kurallar-1), Murillo adds five points and the final human formation becomes 4-4-2. The project evaluator leaves zero-minute starters in place, so its model totals remain on a different scoring basis.', '',
        f'Berkan, Batrakov, Orban, Vlahovic and the other human choices have exact official points in the squad table. The local player archive prices sum to **{h["archive_squad_cost"]:.1f}M** for the human 15 and their club counts respect the three-player limit; those prices are not verified at the GW11 deadline. The Phase 32 artifact’s high-scoring unselected list includes Greenwood and Vlahovic; both were in the historical short-form candidate pool, but candidate eligibility alone does not establish budget feasibility for a model replacement squad or pre-deadline superiority.', '',
        '### Demonstrated errors versus hypotheses', '',
        '- **Verified:** zero-minute Osimhen was selected by four models and the human; the project’s actual-score evaluator omits automatic substitutions. Greenwood’s captain outcome exceeded the model captains’ outcomes.',
        '- **Hypotheses:** expected minutes, lineup probability, availability, recent-form windows, opponent strength, team strength and team-level xG may have affected selections. The artifacts do not retain pre-deadline injury/lineup evidence or per-player feature contributions needed to attribute these causally.',
        '- **External-statistics limit:** the existing xG variants used team-level Football-Data matches, not verified player xG/xA. Their one-week outcomes do not establish xG reliability or value.', '',
        '## Free pre-deadline data priorities', '',
        '| Priority | Feature and free source | Needed evidence before deadline | Feasibility / limit |',
        '| ---: | --- | --- | --- |',
        '| 1 | Official TFF player status and dated squad/fixture notices | Timestamped status, suspension and expected availability per player | Official identity is reliable; historical deadline snapshots must be captured prospectively |',
        '| 2 | Team-published starting XI and club injury notices | Published timestamp, player ID match and expected role | Often free, but confirmed XI may arrive after fantasy deadline; only earlier notices qualify |',
        '| 3 | Official recent starts/minutes | GW1–10 rows observed before deadline; lagged participation features | Already available, but source availability time and calibration need auditing |',
        '| 4 | Free Football-Data team results/xG | Pre-deadline retrieval timestamp, match coverage and opponent features | Existing 81-match archive is usable with publication lag; no player xG or guaranteed freshness |',
        '| 5 | Official fixture, venue and rest schedule | Snapshot and reschedule timestamps before deadline | Free and stable identifiers; late changes require new observations |', '',
        'Test these features across multiple genuinely timestamped gameweeks before changing weights. No paid API is recommended.', '',
        '## Scientific limits and verification', '',
        'The six model replays use GW10 histories first retrieved after the GW11 deadline, unverified deadline prices, frozen October 31 metadata and postmatch price proxies. Phase 32B found unchanged model XIs under its two distinct price states. The three genuine saved GW11 predictions remain separate (saved short-form actual 57; saved stable actual 76). No GW11 outcomes were used to generate new lineups here.', '',
        'All comparison equations are asserted in code. Focused regression tests cover captain arithmetic, lineup differences and the conditional substitution. No frozen prediction or previous report was modified.', '']
    Path('docs/phase33b_human_vs_ai.md').write_text('\n'.join(lines), encoding='utf-8')


if __name__ == '__main__':
    print(run()['human_scoring'])
