"""Explain saved lineup arithmetic without changing selection or penalties."""
from collections import defaultdict


def describe(lineup):
    xi = lineup['starting_xi']
    bench = lineup.get('bench', [])
    captain = next((p for p in xi if p.get('captain')), None)
    if captain is None:
        raise ValueError('Starting XI has no captain')
    pairs = []
    defenders = [p for p in xi if p['position'] in ('GK', 'DEF')]
    attackers = [p for p in xi if p['position'] in ('MID', 'FWD')]
    for defender in defenders:
        for attacker in attackers:
            if str(defender.get('opponent')) == str(attacker['team']) and str(attacker.get('opponent')) == str(defender['team']):
                pairs.append({'defender_id':defender['id'],'attacker_id':attacker['id']})
    by_club = defaultdict(list)
    for p in defenders:
        by_club[str(p['team'])].append({'id':p['id'],'name':p['name'],'position':p['position']})
    clusters = [{'team':team,'players':players} for team,players in sorted(by_club.items()) if len(players)>1]
    raw_xi = sum(float(p['xpts']) for p in xi)
    raw_captain = float(captain['xpts'])
    adjusted_captain = float(captain.get('captain_bonus_xpts',raw_captain))
    bench_tiebreak = .01 * sum(float(p['xpts']) for p in bench)
    pair_penalty = float(lineup.get('risk_penalty',0))
    ranked = sorted(xi,key=lambda p:float(p.get('captain_bonus_xpts',p['xpts'])),reverse=True)
    runner_up = ranked[1] if len(ranked)>1 else None
    return {'captain':{'id':captain['id'],'name':captain['name'],
                       'player_expected_points':round(raw_captain,3),
                       'risk_adjusted_bonus':round(adjusted_captain,3),
                       'risk_discount':round(raw_captain-adjusted_captain,3),
                       'runner_up':runner_up['name'] if runner_up else None,
                       'selection_margin':round(adjusted_captain-float(runner_up.get('captain_bonus_xpts',runner_up['xpts'])),3) if runner_up else None,
                       'upside_estimate':None,
                       'explanation':'Captain maximizes the adjusted bonus among the selected XI. Upside is not modeled.'},
            'objective':{'starting_xi_expected':round(raw_xi,3),
                         'raw_xi_plus_captain':round(raw_xi+raw_captain,3),
                         'captain_adjusted_total':round(raw_xi+adjusted_captain,3),
                         'bench_tiebreak':round(bench_tiebreak,4),
                         'opposing_pair_penalty':round(pair_penalty,2),
                         'reconstructed_objective':round(raw_xi+adjusted_captain+bench_tiebreak-pair_penalty,4)},
            'opposing_defender_attacker_pairs':pairs,
            'same_club_defensive_clusters':clusters,
            'same_club_defensive_penalty':0,
            'risk_scope':'Only opposing starter defender/goalkeeper versus attacker pairs have a strategy penalty.'}
