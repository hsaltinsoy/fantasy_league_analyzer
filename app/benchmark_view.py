"""Read-only presentation of saved benchmark predictions."""
from analysis.prediction_tracking import get_prediction, get_snapshot

POSITIONS = ('FWD', 'MID', 'DEF', 'GK')


def comparison_view(report, left_id=None, right_id=None, clubs=None):
    rows = report.get('predictions') or []
    if not rows:
        return None
    by_id = {row['id']:row for row in rows}
    left_id = left_id if left_id in by_id else rows[0]['id']
    right_id = right_id if right_id in by_id else next(
        (row['id'] for row in rows if row['model']=='direct_risk_frontier' and
         (row.get('swaps_vs_production') or {}).get('only_direct') and row['id'] != left_id),
        next((row['id'] for row in rows if row['model'] == 'experimental_covariance' and row['id'] != left_id),
             next((row['id'] for row in rows if row['id'] != left_id), left_id)))
    clubs = clubs or {}

    def read_side(prediction_id):
        row = by_id[prediction_id]
        saved = get_prediction(prediction_id)
        snapshot = get_snapshot(saved['snapshot_id'])
        payload = saved['payload']
        players = []
        for player in payload['starting_xi']:
            team_id = str(player.get('team') or '')
            club = clubs.get(team_id) or {}
            players.append({**player,
                            'club_label':club.get('short_name') or club.get('name') or
                            (f'Club ID {team_id}' if team_id else 'Club unavailable')})
        groups = {position:[p for p in players if p.get('position') == position]
                  for position in POSITIONS}
        cost = payload.get('cost')
        remaining = payload.get('budget_remaining')
        if remaining is None and cost is not None:
            remaining = round(100-float(cost),2)
        return {'id':prediction_id,'row':row,'saved':saved,'snapshot':snapshot,
                'players':players,'groups':groups,'formation':payload.get('formation'),
                'captain':next((p for p in players if p.get('captain')),None),
                'expected_points':saved['raw_expected_points'],
                'risk_adjusted_objective':saved['risk_adjusted_objective'],
                'remaining_budget':remaining,
                'fixture_retrieved_at':snapshot['source'].get('fixtures_retrieved_at'),
                'freshness_hours_at_capture':(snapshot['payload'].get('data_quality') or {}).get('fixture_source_age_hours')}

    left, right = read_side(left_id), read_side(right_id)
    left_ids = {str(p['id']) for p in left['players']}
    right_ids = {str(p['id']) for p in right['players']}
    left_unique, right_unique = left_ids-right_ids, right_ids-left_ids
    for side, unique in ((left,left_unique),(right,right_unique)):
        for player in side['players']:
            player['unique_to_side'] = str(player['id']) in unique
    left_captain = left['captain']
    right_captain = right['captain']
    return {'left':left,'right':right,
            'common_players':len(left_ids & right_ids),
            'common_players_list':[p for p in left['players'] if str(p['id']) in right_ids],
            'left_unique':[p for p in left['players'] if str(p['id']) in left_unique],
            'right_unique':[p for p in right['players'] if str(p['id']) in right_unique],
            'captain_different':bool(left_captain and right_captain and str(left_captain['id']) != str(right_captain['id'])),
            'formation_different':left['formation'] != right['formation'],
            'same_snapshot':left['saved']['snapshot_id'] == right['saved']['snapshot_id'],
            'same_gameweek':left['saved']['gameweek'] == right['saved']['gameweek']}


def risk_chart_view(report, snapshot_id, selected_ids=()):
    """Scale saved risk/return estimates for an accessible SVG scatterplot."""
    rows=[row for row in report.get('risk_return',[]) if row['snapshot_id']==snapshot_id]
    if not rows:
        return None
    min_risk=min(row['estimated_standard_deviation'] for row in rows)
    max_risk=max(row['estimated_standard_deviation'] for row in rows)
    min_return=min(row['expected_points'] for row in rows)
    max_return=max(row['expected_points'] for row in rows)
    risk_span=max(max_risk-min_risk,.01)
    return_span=max(max_return-min_return,.01)
    points=[]
    for row in rows:
        points.append({**row,'x':round(65+570*(row['estimated_standard_deviation']-min_risk)/risk_span,1),
                       'y':round(260-215*(row['expected_points']-min_return)/return_span,1),
                       'selected':row['prediction_id'] in selected_ids,
                       'direct':row['model']=='direct_risk_frontier'})
    return {'points':points,'min_risk':round(min_risk,2),'max_risk':round(max_risk,2),
            'min_return':round(min_return,2),'max_return':round(max_return,2),
            'snapshot_id':snapshot_id}
