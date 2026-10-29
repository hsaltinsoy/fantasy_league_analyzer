"""v3.3: paired fixture ablation and fail-closed club-ID provenance checks.

Works on a v3.2 JSON report; no historical scores are fabricated.
"""
import argparse
import csv
import json
from pathlib import Path
from statistics import mean


def verify_mapping(candidates, authoritative):
    """Require independent club ID/name evidence; roster inference is insufficient."""
    c = json.loads(Path(candidates).read_text(encoding='utf-8'))
    a = json.loads(Path(authoritative).read_text(encoding='utf-8'))
    if a.get('source_type') != 'OFFICIAL_FANTASY_API' or not a.get('source_url') or not a.get('captured_utc'):
        raise ValueError('Official fantasy API provenance (source_type, source_url, captured_utc) required')
    official = a.get('clubs')
    if not isinstance(official, list) or len(official) != 18:
        raise ValueError('Expected 18 independently sourced official club records')
    actual = {}
    for x in official:
        club_id = str(x.get('club_id', '')).strip()
        name = str(x.get('team_name', '')).strip()
        if not club_id.isdigit() or not name or club_id in actual:
            raise ValueError('Duplicate/invalid official club ID or team name')
        actual[club_id] = name
    candidates_list = c.get('clubs', [])
    mismatches = [{'club_id': str(x['club_id']), 'inferred': x['team_name'], 'official': actual.get(str(x['club_id']))}
                  for x in candidates_list if actual.get(str(x['club_id'])) != x['team_name']]
    return {'status':'MATCH' if not mismatches and len(candidates_list)==18 else 'MISMATCH',
            'official_source':a['source_url'], 'official_captured_utc':a['captured_utc'],
            'mismatches':mismatches, 'official_clubs':len(actual)}


def paired_ablation(report):
    """Compare each base model at weight zero vs .5, not different selected models."""
    rows = []
    for step in report['weeks']:
        if step.get('result') is None:
            continue
        models = step['all_models']
        for name, zero in models.items():
            if not name.endswith('__f000'):
                continue
            paired = name[:-3] + '050'
            if paired not in models:
                continue
            fixture = models[paired]
            if zero.get('actual') is None or fixture.get('actual') is None:
                continue
            rows.append({'week':step['week'], 'base_model':name[:-6],
                         'without_fixture':zero['actual'], 'with_fixture':fixture['actual'],
                         'fixture_gain':round(fixture['actual']-zero['actual'],2),
                         'without_fixture_mae':zero['absolute_error'],
                         'with_fixture_mae':fixture['absolute_error'],
                         'mae_improvement':round(zero['absolute_error']-fixture['absolute_error'],2)})
    by_model = {}
    for name in sorted({r['base_model'] for r in rows}):
        subset = [r for r in rows if r['base_model']==name]
        by_model[name] = {'weeks':len(subset), 'total_fixture_gain':round(sum(r['fixture_gain'] for r in subset),2),
                          'mean_fixture_gain':round(mean(r['fixture_gain'] for r in subset),3),
                          'mean_mae_improvement':round(mean(r['mae_improvement'] for r in subset),3)}
    selected = [s for s in report['weeks'] if s.get('result')]
    return {'classification':report.get('classification'), 'warning':'Paired ablation is exploratory, not causal or point-in-time verified.',
            'selected_total':round(sum(s['result']['actual'] for s in selected),2),
            'paired_rows':rows, 'by_model':by_model}


def main():
    p=argparse.ArgumentParser(description='v3.3 provenance and paired fixture audit')
    p.add_argument('--report',type=Path,required=True)
    p.add_argument('--out',type=Path,default=Path('historical_data/v33_audit'))
    p.add_argument('--candidate-mapping',type=Path)
    p.add_argument('--official-mapping',type=Path)
    args=p.parse_args()
    report=json.loads(args.report.read_text(encoding='utf-8'))
    result=paired_ablation(report)
    if bool(args.candidate_mapping) != bool(args.official_mapping):
        p.error('Provide both --candidate-mapping and --official-mapping for independent verification')
    result['club_mapping_verification']=(verify_mapping(args.candidate_mapping,args.official_mapping)
                                         if args.official_mapping else {'status':'UNVERIFIED', 'reason':'No independent official API mapping supplied'})
    args.out.mkdir(parents=True,exist_ok=True)
    (args.out/'audit.json').write_text(json.dumps(result,ensure_ascii=False,indent=2),encoding='utf-8')
    with (args.out/'paired_ablation.csv').open('w',newline='',encoding='utf-8-sig') as f:
        if result['paired_rows']:
            writer=csv.DictWriter(f,fieldnames=list(result['paired_rows'][0]));writer.writeheader();writer.writerows(result['paired_rows'])
    print(json.dumps({'selected_total':result['selected_total'],'by_model':result['by_model'],
                      'club_mapping_verification':result['club_mapping_verification']},ensure_ascii=False,indent=2))

if __name__=='__main__':main()
