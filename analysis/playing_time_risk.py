"""Experimental prior-only probability of an appearance; not a team selector."""
import math
from statistics import mean, stdev


def valid_appearance(row, week, fixture_weeks):
    """Return 0/1 only when a completed fixture and coherent player row exist."""
    entry = fixture_weeks.get(str(week), fixture_weeks.get(week, {}))
    opponent = str(row.get('opponentClubId'))
    matches = [m for m in entry.get('matches', []) if
               str(m.get('status')).upper()=='FT' and opponent in
               (str(m.get('homeClubId')),str(m.get('awayClubId')))]
    if len(matches)!=1 or not isinstance(row.get('played'),bool):
        return None
    minutes = row.get('minutesPlayed')
    if not isinstance(minutes,(int,float)) or not math.isfinite(minutes) or minutes<0:
        return None
    if row['played'] and minutes==0:
        return None  # Inconsistent source; do not relabel as non-appearance.
    if not row['played'] and minutes>0:
        return None
    return int(row['played'])


def probability(past_labels, league_rate, prior_strength=4, lookback=4):
    if not 0<=league_rate<=1 or prior_strength<=0 or lookback<1:
        raise ValueError('Invalid prior or lookback')
    recent=past_labels[-lookback:]
    if any(x not in (0,1) for x in recent):
        raise ValueError('Labels must be 0 or 1')
    alpha=prior_strength*league_rate+sum(recent)
    beta=prior_strength*(1-league_rate)+len(recent)-sum(recent)
    p=alpha/(alpha+beta)
    standard_error=math.sqrt(alpha*beta/((alpha+beta)**2*(alpha+beta+1)))
    return {'probability':round(p,4),'prior_observations':len(recent),
            'posterior_standard_deviation':round(standard_error,4),
            'rough_95pct_interval':[round(max(0,p-1.96*standard_error),4),
                                    round(min(1,p+1.96*standard_error),4)]}


def chronological_report(records, fixture_weeks, weeks=(5,6,7,8,9)):
    examples=[]
    missing=0
    match_errors={}
    for week in weeks:
        if week<2:
            raise ValueError('Holdout weeks must be >=2')
        prior_all=[]
        for _,rows in records:
            for row in rows:
                w=int(row['gameweekOrder'])
                if w>=week:continue
                label=valid_appearance(row,w,fixture_weeks)
                if label is not None:prior_all.append(label)
        if not prior_all:continue
        league_rate=mean(prior_all)
        for player,rows in records:
            target=[r for r in rows if int(r['gameweekOrder'])==week]
            if len(target)!=1:
                missing+=1
                continue
            outcome=valid_appearance(target[0],week,fixture_weeks)
            if outcome is None:
                missing+=1
                continue
            past=[(int(r['gameweekOrder']),valid_appearance(r,int(r['gameweekOrder']),fixture_weeks))
                  for r in rows if int(r['gameweekOrder'])<week]
            labels=[value for _,value in sorted(past) if value is not None]
            if not labels:continue
            pred=probability(labels,league_rate)
            entry=fixture_weeks.get(str(week),fixture_weeks.get(week,{}))
            match=next((m for m in entry.get('matches',[]) if
                        str(target[0].get('opponentClubId')) in
                        (str(m.get('homeClubId')),str(m.get('awayClubId'))) and
                        str(m.get('status')).upper()=='FT'),None)
            if match is None:
                missing+=1
                continue
            match_errors.setdefault((week,match['id']),[]).append(
                ((pred['probability']-outcome)**2,(league_rate-outcome)**2))
            examples.append({'week':week,'player_id':player['id'],'predicted':pred['probability'],
                             'actual':outcome,'league_baseline':league_rate,
                             'prior_observations':pred['prior_observations']})
    cluster_model=[mean(x[0] for x in values) for values in match_errors.values()]
    cluster_gain=[mean(x[1]-x[0] for x in values) for values in match_errors.values()]
    def interval(values):
        if len(values)<2:return None
        center=mean(values)
        margin=1.96*stdev(values)/math.sqrt(len(values))
        return [round(center-margin,4),round(center+margin,4)]
    return {'classification':'RETROSPECTIVE_PARTICIPATION_NOT_DEADLINE_VERIFIED',
            'n':len(examples),'missing_target_rows':missing,
            'match_clusters':len(match_errors),
            'rough_95pct_cluster_brier_interval':interval(cluster_model),
            'rough_95pct_cluster_improvement_interval':interval(cluster_gain),
            'brier':round(mean((r['predicted']-r['actual'])**2 for r in examples),4) if examples else None,
            'league_baseline_brier':round(mean((r['league_baseline']-r['actual'])**2 for r in examples),4) if examples else None,
            'by_week':{str(week):{'n':sum(r['week']==week for r in examples),
                'brier':round(mean((r['predicted']-r['actual'])**2 for r in examples if r['week']==week),4)
                if any(r['week']==week for r in examples) else None} for week in weeks},
            'limitations':['Current archive roster may omit players who were available historically.',
                           'Historical injury, suspension, transfer and lineup news are unavailable.',
                           'Rows marked played with zero minutes are excluded as inconsistent.',
                           'Cluster intervals group by match but do not account for repeated players across matches.',
                           'This measures appearance probability only, not minutes or fantasy points.']}
