"""Official API fixtures, retrospective (NOT historical pre-deadline snapshots)."""
import argparse
import json
from collections import Counter
from pathlib import Path
from analysis.walkforward_v32 import walk_forward, save_report
from analysis.multiweek_backtest import load_history

SOURCE = '/api/backend/projection/stats/fixtures?league-id=1'

def load_verified(path, weeks):
    obj = json.loads(Path(path).read_text(encoding='utf-8'))
    if obj.get('source_endpoint') != SOURCE or obj.get('classification') != 'LIVE_API_FIXTURES_NOT_PREDEADLINE_SNAPSHOT':
        raise ValueError('Unexpected fixture source/provenance; refuse to run')
    allweeks = obj.get('weeks')
    if not isinstance(allweeks, dict):
        raise ValueError('Missing weeks')
    seen_match_ids = set()
    result = {}
    for week in sorted(allweeks, key=int):
        entry = allweeks[week]
        matches = entry.get('matches')
        if not isinstance(matches, list) or len(matches) != 9:
            raise ValueError(f'GW{week}: expected 9 matches')
        lookup = {}
        for match in matches:
            mid, home, away = match.get('id'), match.get('homeClubId'), match.get('awayClubId')
            if not isinstance(mid, int) or mid in seen_match_ids:
                raise ValueError(f'GW{week}: invalid/duplicate match ID')
            seen_match_ids.add(mid)
            if not isinstance(home, int) or not isinstance(away, int) or home == away or home in lookup or away in lookup:
                raise ValueError(f'GW{week}: invalid/duplicate club')
            lookup[str(home)], lookup[str(away)] = str(away), str(home)
        if len(lookup) != 18:
            raise ValueError(f'GW{week}: incomplete 18-team coverage')
        result[int(week)] = lookup
    if len(allweeks) != 34 or len(seen_match_ids) != 306:
        raise ValueError('Unexpected season size')
    for w in weeks:
        if w not in result:
            raise ValueError(f'GW{w}: missing')
    return result

def main():
    ap = argparse.ArgumentParser(description='v3.4 official fixture retrospective ablation')
    ap.add_argument('--fixtures', type=Path, default=Path('historical_data/tff_fixtures_verified_v5.json'))
    ap.add_argument('--weeks', nargs='+', type=int, default=[5,6,7,8,9])
    ap.add_argument('--weights', nargs='+', type=float, default=[0,.5])
    args = ap.parse_args()
    fixtures = load_verified(args.fixtures, args.weeks)
    report = walk_forward(load_history(), fixtures, args.weeks, args.weights, reconstructed=False)
    report['classification'] = 'OFFICIAL_LIVE_API_RETROSPECTIVE_NOT_PREDEADLINE_VERIFIED'
    report['fixture_mode'] = 'official_live_api_fixture_ids'
    report['source_endpoint'] = SOURCE
    report['limitations'] = [
        'API captured after GW5-9 deadlines: historical fixture state at each deadline not independently proven.',
        'Current player club membership and historical prices are not independently point-in-time verified.',
        'Only pre-target-week fantasy results are used to calculate opponent strength.',
        'No autosubs, chips, or transfer penalties; small sample.'
    ]
    jp, cp = save_report(report)
    target_jp = jp.with_name('walkforward_backtest_v34.json')
    target_cp = cp.with_name('walkforward_backtest_v34.csv')
    jp.replace(target_jp)
    cp.replace(target_cp)
    print('v3.4 summary:', report['summary'], '\nJSON:', target_jp, '\nCSV:', target_cp)

if __name__ == '__main__':
    main()
