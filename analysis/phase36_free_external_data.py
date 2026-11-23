"""Offline, idempotent experimental import and lagged team-feature evaluation."""
import hashlib
import json
from collections import defaultdict
from datetime import datetime, timezone
from math import sqrt
from pathlib import Path
from statistics import mean

from analysis.multiweek_backtest import MODELS, build_week
from analysis.optimizer import optimize
from storage.football_data_repository import VERIFIED_TEAMS, parse_csv

ROOT=Path('docs')
CSV=ROOT/'phase31a_t1_source_probe.csv'
MISSING=ROOT/'phase31a_football_data_audit.json'
FIXTURES=Path('historical_data/tff_fixtures_verified_v5.json')
HISTORY=ROOT/'phase28_official_histories.json'
IMPORT=Path('historical_data/experimental_phase36/missing_gw10_gw11.json')
WEEKS=(6,7,8,9,10,11)
VARIANTS=('baseline','team_form','opponent_defense','combined')


def ingest_missing(raw, reconciliation):
    parsed=parse_csv(raw)
    expected={(x['date'],x['home_id'],x['away_id']):x for x in reconciliation['missing']}
    selected=[]
    for row in parsed['rows']:
        key=(row['date'].isoformat(),VERIFIED_TEAMS.get(row['home']),VERIFIED_TEAMS.get(row['away']))
        if key not in expected:continue
        target=expected[key]
        n=row['numbers']
        if n['FTHG']!=target['home_score'] or n['FTAG']!=target['away_score'] or n['HxG'] is None or n['AxG'] is None:
            raise ValueError(f'Unverified match {key}')
        selected.append({'fixture_id':target['id'],'gameweek':target['gameweek'],
            'date':key[0],'home_id':key[1],'away_id':key[2],
            'home_goals':n['FTHG'],'away_goals':n['FTAG'],
            'home_xg':n['HxG'],'away_xg':n['AxG'],
            'home_shots':n['HS'],'away_shots':n['AS'],
            'home_sot':n['HST'],'away_sot':n['AST']})
    if len(selected)!=18 or len({r['fixture_id'] for r in selected})!=18:
        raise ValueError('Expected 18 unique verified GW10–11 fixtures')
    selected.sort(key=lambda r:r['fixture_id'])
    artifact={'source':'football-data.co.uk','source_url':reconciliation['csv_url'],
        'csv_sha256':hashlib.sha256(raw).hexdigest(),
        'source_observed_at':reconciliation['official_retrieved_at'],
        'classification':'retrospective_local_import_not_predeadline_evidence',
        'matches':selected}
    if artifact['csv_sha256']!=reconciliation['csv_sha256']:
        raise ValueError('Source CSV hash disagrees with reviewed evidence')
    IMPORT.parent.mkdir(parents=True,exist_ok=True)
    if IMPORT.exists():
        old=json.loads(IMPORT.read_text(encoding='utf-8'))
        if old!=artifact:raise ValueError('Conflicting immutable experimental import')
    else:
        IMPORT.write_text(json.dumps(artifact,indent=2,ensure_ascii=False),encoding='utf-8')
    return artifact,parsed


def all_matches(parsed, fixture_archive, reconciliation):
    index={}
    for week,entry in fixture_archive['weeks'].items():
        for m in entry['matches']:
            key=(m['kickoffAt'][:10],str(m['homeClubId']),str(m['awayClubId']))
            index[key]=(int(week),m)
    matched=[]
    for row in parsed['rows']:
        key=(row['date'].isoformat(),VERIFIED_TEAMS.get(row['home']),VERIFIED_TEAMS.get(row['away']))
        if key not in index:continue
        week,official=index[key]
        n=row['numbers']
        expected = next((x for x in reconciliation['missing'] if x['date']==key[0]
                         and x['home_id']==key[1] and x['away_id']==key[2]), None)
        score_home = expected['home_score'] if expected else official['homeScore']
        score_away = expected['away_score'] if expected else official['awayScore']
        if n['FTHG']!=score_home or n['FTAG']!=score_away:
            raise ValueError(f'Fixture score mismatch {key}')
        matched.append({'week':week,'date':key[0],'home':key[1],'away':key[2],
            'hg':n['FTHG'],'ag':n['FTAG'],'hxg':n['HxG'],'axg':n['AxG'],
            'hs':n['HS'],'as':n['AS'],'hst':n['HST'],'ast':n['AST']})
    if len(matched)!=99 or len({(m['date'],m['home'],m['away']) for m in matched})!=99:
        raise ValueError(f'Incomplete/duplicate fixture mapping: {len(matched)}/99')
    return matched


def features(matches, cutoff):
    """Only completed matches before the first kickoff of the target week."""
    by_team=defaultdict(list)
    for m in matches:
        if m['date']>=cutoff:continue
        if any(m[k] is None for k in ('hxg','axg','hs','as','hst','ast')):continue
        by_team[m['home']].append({'date':m['date'],'home':1,'gf':m['hg'],'ga':m['ag'],
            'xgf':m['hxg'],'xga':m['axg'],'shots':m['hs'],'sot':m['hst']})
        by_team[m['away']].append({'date':m['date'],'home':0,'gf':m['ag'],'ga':m['hg'],
            'xgf':m['axg'],'xga':m['hxg'],'shots':m['as'],'sot':m['ast']})
    result={}
    for team,rows in by_team.items():
        recent=sorted(rows,key=lambda r:r['date'])[-5:]
        result[team]={'n':len(recent),
            **{key:mean(r[key] for r in recent) for key in ('gf','ga','xgf','xga','shots','sot')},
            'home_xgf':mean(r['xgf'] for r in recent if r['home']) if any(r['home'] for r in recent) else None,
            'away_xgf':mean(r['xgf'] for r in recent if not r['home']) if any(not r['home'] for r in recent) else None,
            'latest_match_date':max(r['date'] for r in recent)}
    return result


def adjust(pool, fixture_map, team, mode):
    updated=[];missing=0
    for p in pool:
        opponent,home=fixture_map.get(str(p['team']),(None,None))
        own=team.get(str(p['team']));other=team.get(opponent)
        if mode!='baseline' and (not own or not other or own['n']<2 or other['n']<2):
            missing+=1;updated.append(dict(p));continue
        team_signal=0 if mode in ('baseline','opponent_defense') else max(-.1,min(.1,(own['xgf']-own['xga'])/10))
        opp_signal=0 if mode in ('baseline','team_form') else max(-.1,min(.1,(1.25-other['xga'])/-10))
        venue=0
        if mode!='baseline':
            venue_xgf=own['home_xgf'] if home else own['away_xgf']
            venue=0 if venue_xgf is None else max(-.03,min(.03,(venue_xgf-own['xgf'])/20))
        updated.append({**p,'xpts':round(p['xpts']*(1+team_signal+opp_signal+venue),3)})
    return updated,missing


def run():
    rec=json.loads(MISSING.read_text(encoding='utf-8'))
    imported,parsed=ingest_missing(CSV.read_bytes(),rec)
    fixture=json.loads(FIXTURES.read_text(encoding='utf-8'))
    matches=all_matches(parsed,fixture,rec)
    fetched=json.loads(HISTORY.read_text(encoding='utf-8'))
    players=json.loads(Path('historical_data/players.json').read_text(encoding='utf-8'))
    records=[(p,fetched['rows_by_player'][str(p['id'])]) for p in players]
    output={}
    for week in WEEKS:
        entry=fixture['weeks'][str(week)]
        cutoff=min(m['kickoffAt'][:10] for m in entry['matches'])
        prior=[m for m in matches if m['date']<cutoff]
        team=features(prior,cutoff)
        fixture_map={}
        for m in entry['matches']:
            fixture_map[str(m['homeClubId'])]=(str(m['awayClubId']),True)
            fixture_map[str(m['awayClubId'])]=(str(m['homeClubId']),False)
        pool,actual,_=build_week(records,week,MODELS['baseline_5w'])
        pool=[{k:v for k,v in p.items() if k!='actual_points'} for p in pool]
        variants={}
        for mode in VARIANTS:
            changed,missing=adjust(pool,fixture_map,team,mode)
            errors=[p['xpts']-actual[str(p['id'])] for p in changed if str(p['id']) in actual]
            solution=optimize(changed)
            if 'error' in solution:raise RuntimeError(solution['error'])
            xi=solution['starting_xi'];captain=solution['captain']['id']
            zero=sum(next(r for r in fetched['rows_by_player'][str(p['id'])] if int(r['gameweekOrder'])==week)['minutesPlayed']==0 for p in xi)
            variants[mode]={'mae':round(mean(abs(e) for e in errors),3),
                'rmse':round(sqrt(mean(e*e for e in errors)),3),'n':len(errors),
                'actual_squad_points':sum(actual[str(p['id'])] for p in xi)+actual[str(captain)],
                'predicted_squad_points':solution['expected_fantasy_points'],
                'formation':solution['formation'],
                'captain_id':captain,'captain_actual':actual[str(captain)],
                'xi_ids':[p['id'] for p in xi],'bench_ids':[p['id'] for p in solution['squad'] if p['id'] not in {q['id'] for q in xi}],
                'xi_players':[{'id':p['id'],'name':p['name'],'predicted':p['xpts'],
                               'actual':actual[str(p['id'])]} for p in xi],
                'zero_minute_starters':zero,'missing_feature_candidates':missing,
                'candidate_count':len(changed)}
        output[str(week)]={'cutoff_date':cutoff,'prior_match_count':len(prior),
                           'feature_team_count':len(team),'variants':variants}
    result={'classification':'retrospective_experimental_not_prospective',
        'source_csv_sha256':imported['csv_sha256'],'source_observed_at':imported['source_observed_at'],
        'local_import_path':str(IMPORT),'imported_missing_fixture_ids':[m['fixture_id'] for m in imported['matches']],
        'imported_missing_matches':imported['matches'],
        'matched_csv_fixtures':len(matches),'mapped_teams':len(VERIFIED_TEAMS),
        'source_coverage':{'team_xg':sum(m['hxg'] is not None and m['axg'] is not None for m in matches),
            'shots':sum(m['hs'] is not None and m['as'] is not None for m in matches),
            'shots_on_target':sum(m['hst'] is not None and m['ast'] is not None for m in matches),
            'player_appearances':0,'starting_lineups':0,'injuries_suspensions':0,'player_xg_xa':0},
        'historical_experiments':output,
        'warnings':['CSV observed Nov 9; earlier publication times unknown',
                    'No verified historical club, availability or price snapshots',
                    'Experimental coefficients are fixed heuristics, not trained weights',
                    'No player-level external statistics in Football-Data CSV']}
    (ROOT/'phase36_free_external_data.json').write_text(json.dumps(result,indent=2,ensure_ascii=False),encoding='utf-8')
    report(result)
    return result


def report(d):
    lines=['# Phase 36 — free external team data experiment','',
        '**Classification:** retrospective experimental analysis. No frozen prediction or production weight changed.','',
        '## Source refresh and measured coverage','',
        f'The existing local [Football-Data Turkey CSV](https://football-data.co.uk/turkeym.php) (SHA-256 `{d["source_csv_sha256"]}`) was observed {d["source_observed_at"]}. Its 99 matches map one-to-one to official fixtures and all 18 clubs. A separate idempotent experimental import stores exactly the 18 previously missing GW10–11 fixture IDs at `{d["local_import_path"]}`; the original 81-row PostgreSQL archive and frozen external evidence were not changed. Re-running with the same bytes is a no-op; conflicting bytes are rejected. No new CSV download was made.','',
        f'Measured CSV coverage: {d["source_coverage"]["team_xg"]}/99 matches with both team xG, {d["source_coverage"]["shots"]}/99 with both shot counts, {d["source_coverage"]["shots_on_target"]}/99 with both shots-on-target counts. Player appearances, starting XIs, injuries/suspensions and player xG/xA: **0 verified rows** from this source. Other free provider marketing claims were not treated as tested endpoints; no authorized credentials or measured current-season player responses were available.','',
        'The [source fair-use policy](https://football-data.co.uk/contact.php) permits only light personal/academic automated downloads (at most twice weekly) and does not grant commercial or heavy AI training use. The existing local file was reused; licensing for any broader deployment needs separate review.','',
        '## Experimental features and cutoff','',
        'Each target GW uses only CSV matches dated **before the first target-week kickoff**. Up to five recent matches per team yield goals for/against, xG for/against, shots, shots on target, and home/away xG. Fixture opponent and venue come from the frozen official fixture archive. The team-form variant uses capped xG balance; opponent-defense uses capped opponent xG conceded; combined uses both. Venue adjustment is capped and shared by experimental variants. All coefficients are fixed small heuristics and are not production weights. Missing or fewer than two team matches leaves the player at baseline xPts and is counted.','',
        '**Point-in-time limitation:** the 99-row CSV was first observed after GW11. Event-date filtering prevents target-match statistics from entering a target prediction, but does not prove that every earlier row was published by that earlier deadline. These are reconstructed experiments, not genuine pre-deadline forecasts. Historical player club, price and availability are also imperfect.','',
        '## Controlled GW6–11 results','',
        '| GW | Variant | Prior matches | Candidate N | Missing-feature candidates | MAE | RMSE | XI actual + captain | Captain actual | Zero-minute XI |',
        '| ---: | --- | ---: | ---: | ---: | ---: | ---: | ---: | ---: | ---: |']
    for w in WEEKS:
        row=d['historical_experiments'][str(w)]
        for name in VARIANTS:
            x=row['variants'][name]
            lines.append(f'| {w} | {name} | {row["prior_match_count"]} | {x["candidate_count"]} | {x["missing_feature_candidates"]} | {x["mae"]:.3f} | {x["rmse"]:.3f} | {x["actual_squad_points"]} | {x["captain_actual"]} | {x["zero_minute_starters"]} |')
    lines += ['', 'Six-week total XI-plus-captain scores: ' + ', '.join(
        f'{name} {sum(d["historical_experiments"][str(w)]["variants"][name]["actual_squad_points"] for w in WEEKS):.0f}'
        for name in VARIANTS) + '. Mean player MAE across weeks: ' + ', '.join(
        f'{name} {mean(d["historical_experiments"][str(w)]["variants"][name]["mae"] for w in WEEKS):.3f}'
        for name in VARIANTS) + '. These descriptive totals are too small and too retrospective to justify production integration.', '']
    lines += ['', 'All variants within a week use the identical historical player pool, prices, target fixture and optimizer. Only external team-feature adjustments change. Full XI, bench and captain IDs are in JSON. The squad score uses XI official points plus captain once more; automatic substitution and chips are outside this evaluator. Compare objectives only within the same configuration.','',
        '## Other free-source verification','',
        '| Source | Turkish current-season evidence | Automated access / use | Outcome |','| --- | --- | --- | --- |',
        '| Official TFF Fantasy API | Previous project audit measured 573 GW11 history rows and official fixtures | Existing authenticated integration; historical pre-deadline source timestamps incomplete | Useful for player minutes, starts, points and live status; no reliable populated player xG/xA |',
        '| Football-Data Turkey CSV | 99/99 current-season matches mapped here | [Fair-use limits](https://football-data.co.uk/contact.php) apply | Team xG, goals, shots and SOT only |',
        '| Yuvron / API-Football and other advertised free tiers | No authenticated current-season endpoint response measured in this phase | Key, quota and reuse rights not verified | No player/lineup/injury/xG fields integrated |','',
        '## Recommendation','',
        'Keep the team features experimental. The study can show directional sensitivity but cannot establish prospective benefit because CSV publication dates and historical player metadata are missing. Next capture a timestamped, permitted Football-Data observation before each deadline, verify its rights and completeness, and evaluate on multiple genuinely prospective weeks. Seek player-level free data only after legal access, current-season endpoint coverage and ID matching are measured. Do not assign production weights from this retrospective sample.','',
        'Focused regression tests check idempotent import, fixture matching and strict target-week date exclusion.','']
    (ROOT/'phase36_free_external_data.md').write_text('\n'.join(lines),encoding='utf-8')


if __name__=='__main__':
    r=run();print(r['matched_csv_fixtures'],r['source_coverage'])
