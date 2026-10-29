"""Retrospective, conditional-on-appearance squad risk diagnostics.

This module never changes production optimization or expected-point weights.
"""
import math
from collections import defaultdict
from itertools import combinations
from statistics import mean, stdev, variance


CATEGORIES = ('def_def', 'gk_def', 'opposing_def_att')


def category(a, b):
    positions = {a['position'], b['position']}
    if str(a['team']) == str(b['team']):
        if positions == {'DEF'}:
            return 'def_def'
        if positions == {'GK', 'DEF'}:
            return 'gk_def'
    elif ((a['position'] in ('GK', 'DEF') and b['position'] in ('MID', 'FWD')) or
          (b['position'] in ('GK', 'DEF') and a['position'] in ('MID', 'FWD'))):
        if str(a.get('opponent')) == str(b['team']) and str(b.get('opponent')) == str(a['team']):
            return 'opposing_def_att'
    return None


def estimate(records, fixture_weeks, target_week, prior_strength=24, min_clusters=20,
             start_week=1, omitted_match=None):
    """Use only completed matches and played rows strictly before target_week."""
    if target_week < 2 or prior_strength < 0 or min_clusters < 2 or not 1<=start_week<target_week:
        raise ValueError('Invalid target week or shrinkage')
    fixture_lookup = {}
    for week, entry in fixture_weeks.items():
        week = int(week)
        if week >= target_week or week < start_week:
            continue
        for match in entry.get('matches', []):
            if str(match.get('status')).upper() != 'FT':
                continue
            if omitted_match == (week, match.get('id')):
                continue
            for club in (match.get('homeClubId'), match.get('awayClubId')):
                fixture_lookup[(week, str(club))] = match
    observations = defaultdict(list)
    matches = defaultdict(list)
    excluded = defaultdict(int)
    for player, rows in records:
        pid = str(player['id'])
        for row in rows:
            week = int(row['gameweekOrder'])
            if week >= target_week or week < start_week:
                continue
            if row.get('played') is False or not row.get('minutesPlayed'):
                excluded['no_appearance'] += 1
                continue
            if row.get('points') is None:
                excluded['missing_points'] += 1
                continue
            opponent = str(row.get('opponentClubId'))
            match = fixture_lookup.get((week, opponent))
            if match is None:
                excluded['missing_or_unfinished_fixture'] += 1
                continue
            home, away = str(match['homeClubId']), str(match['awayClubId'])
            team = away if home == opponent else home
            if row.get('homeAway') != ('H' if team == home else 'A'):
                excluded['venue_mismatch'] += 1
                continue
            score = float(row['points'])
            if not math.isfinite(score):
                excluded['invalid_points'] += 1
                continue
            item = {'id':pid,'team':team,'opponent':opponent,
                    'position':player['position'],'points':score}
            observations[pid].append(item)
            matches[(week, match['id'])].append(item)
    player_means = {pid:mean(row['points'] for row in rows) for pid,rows in observations.items()}
    position_scores = defaultdict(list)
    for rows in observations.values():
        for row in rows:
            position_scores[row['position']].append(row['points'])
    position_variance = {pos:variance(scores) if len(scores)>=2 else None
                         for pos,scores in position_scores.items()}
    player_variance = {}
    for pid, rows in observations.items():
        scores = [r['points'] for r in rows]
        own = variance(scores) if len(scores)>=3 else None
        prior = position_variance.get(rows[0]['position'])
        if own is None:
            player_variance[pid] = {'variance':prior,'observations':len(scores),'source':'position_pool'}
        elif prior is None:
            player_variance[pid] = {'variance':own,'observations':len(scores),'source':'player'}
        else:
            weight = len(scores)/(len(scores)+4)
            player_variance[pid] = {'variance':weight*own+(1-weight)*prior,
                                    'observations':len(scores),'source':'shrunk_player'}
    cluster_products = {name:[] for name in CATEGORIES}
    pair_counts = defaultdict(int)
    for match_rows in matches.values():
        products = defaultdict(list)
        for a,b in combinations(match_rows,2):
            kind = category(a,b)
            if kind is None or len(observations[a['id']])<3 or len(observations[b['id']])<3:
                continue
            products[kind].append((a['points']-player_means[a['id']])*(b['points']-player_means[b['id']]))
            pair_counts[kind] += 1
        for kind, values in products.items():
            cluster_products[kind].append(mean(values))
    covariance = {}
    for kind, values in cluster_products.items():
        n = len(values)
        raw = mean(values) if values else None
        se = stdev(values)/math.sqrt(n) if n>=2 else None
        covariance[kind] = {'match_clusters':n,'pair_observations':pair_counts[kind],
                            'raw':raw,'shrunk':raw*n/(n+prior_strength) if raw is not None and n>=min_clusters else None,
                            'minimum_clusters':min_clusters,
                            'cluster_standard_error':se,
                            'rough_95pct_interval':[raw-1.96*se,raw+1.96*se] if se is not None else None}
    return {'target_week':target_week,'start_week':start_week,'covariance':covariance,
            'player_variance':player_variance,'position_variance':position_variance,
            'excluded':dict(excluded),'completed_match_clusters':len(matches),
            'classification':'RETROSPECTIVE_CONDITIONAL_ON_APPEARANCE_NOT_DEADLINE_VERIFIED',
            'limitations':['Current player positions may not match historical positions.',
                           'Historical fixture archive was captured after earlier deadlines.',
                           'Playing probability, postponed fixtures, auto-subs and transfers are not modeled.',
                           'Pair observations within a match are dependent; uncertainty uses match clusters.']}


def stability_report(records, fixture_weeks, target_week, windows=(3,5,9)):
    full = estimate(records, fixture_weeks, target_week)
    keys = [(int(week), match['id']) for week,entry in fixture_weeks.items()
            if int(week)<target_week for match in entry.get('matches',[])
            if str(match.get('status')).upper()=='FT']
    leave_one_out = {kind:[] for kind in CATEGORIES}
    for key in keys:
        partial = estimate(records, fixture_weeks, target_week, omitted_match=key)
        for kind in CATEGORIES:
            value = partial['covariance'][kind]['shrunk']
            if value is not None:
                leave_one_out[kind].append((key,value))
    loo = {}
    for kind, values in leave_one_out.items():
        reference = full['covariance'][kind]['shrunk']
        loo[kind] = {'match_omissions':len(values),
                     'minimum':min((v for _,v in values),default=None),
                     'maximum':max((v for _,v in values),default=None),
                     'largest_absolute_change':max((abs(v-reference) for _,v in values),default=None)
                     if reference is not None else None}
    window_results = {}
    for width in windows:
        if width < 1:
            raise ValueError('Window must be positive')
        start=max(1,target_week-width)
        item=estimate(records,fixture_weeks,target_week,start_week=start)
        window_results[str(width)]={'start_week':start,'match_clusters':item['completed_match_clusters'],
                                    'covariance':{kind:item['covariance'][kind] for kind in CATEGORIES}}
    return {'full':full,'leave_one_match_out':loo,'windows':window_results,
            'note':'Leave-one-out recomputes player means and variances after removing each match.'}


def lineup_variance(xi, captain_id, evidence):
    total = 0.0
    components = []
    for player in xi:
        item = evidence['player_variance'].get(str(player['id']))
        value = item['variance'] if item else evidence['position_variance'].get(player['position'])
        if value is None:
            return None
        multiplier = 2 if str(player['id']) == str(captain_id) else 1
        total += multiplier*multiplier*value
    for a,b in combinations(xi,2):
        kind = category(a,b)
        if kind is None:
            continue
        estimate = evidence['covariance'][kind]['shrunk']
        if estimate is None:
            continue
        weight = (2 if str(a['id']) == str(captain_id) else 1)*(2 if str(b['id']) == str(captain_id) else 1)
        contribution = 2*weight*estimate
        total += contribution
        components.append({'category':kind,'player_ids':[a['id'],b['id']],
                           'variance_contribution':round(contribution,4),
                           'match_clusters':evidence['covariance'][kind]['match_clusters']})
    return {'variance':round(max(0,total),4),'standard_deviation':round(math.sqrt(max(0,total)),4),
            'covariance_components':components}


def compare_candidates(solutions, evidence, risk_aversions=(0,.5,1.0)):
    """Sensitivity analysis across existing formation solutions and their XI captains."""
    candidates = []
    for formation, solution in solutions.items():
        xi = solution['starting_xi']
        for captain in xi:
            spread = lineup_variance(xi,captain['id'],evidence)
            if spread is None:
                continue
            raw_mean = sum(float(p['xpts']) for p in xi)+float(captain['xpts'])
            candidates.append({'formation':formation,'captain_id':captain['id'],
                               'captain_name':captain['name'],
                               'squad_ids':sorted(p['id'] for p in solution['squad']),
                               'starting_xi':[{**p,'captain':p['id']==captain['id']} for p in xi],
                               'bench':[p for p in solution['squad'] if p['id'] not in {q['id'] for q in xi}],
                               'squad_cost':solution.get('squad_cost',sum(float(p.get('price',0)) for p in solution['squad'])),
                               'expected_points':round(raw_mean,3),**spread})
    selected = {}
    for risk in risk_aversions:
        if risk < 0:
            raise ValueError('Risk aversion must be nonnegative')
        choice = max(candidates,key=lambda c:c['expected_points']-risk*c['standard_deviation']) if candidates else None
        selected[str(risk)] = ({**choice,'risk_aversion':risk,
                                'selection_score':round(choice['expected_points']-risk*choice['standard_deviation'],3)}
                               if choice else None)
    return {'candidate_count':len(candidates),'candidates':candidates,'selected_by_risk_aversion':selected,
            'note':'Candidate set contains existing production formation solutions and their XI captains only; this does not optimize all possible squads under covariance.'}
