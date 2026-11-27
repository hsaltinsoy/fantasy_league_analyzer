"""Prospective check: did the official availability status at the deadline predict who played?

For gameweek W, the deadline-time player status comes from the latest pre-deadline snapshot of
week W. The realised minutes for W come from a later snapshot (W+1 or later) whose stored
histories contain week W rows. Nothing is fetched from the network and nothing is written to
the database. The report is written to artifacts/availability_outcome.json.

Usage (PostgreSQL running, .env present):
    python -m analysis.availability_outcome            # every week that has both snapshots
    python -m analysis.availability_outcome --week 12
"""
import argparse
import json
from collections import defaultdict
from pathlib import Path

OUT = Path('artifacts/availability_outcome.json')
CLEAR = {'AVAILABLE', 'FIT', 'OK'}
UNKNOWN = {'', 'UNKNOWN', 'NONE'}


def status_bucket(player):
    """Group a deadline-time player record into one comparable bucket."""
    status = str(player.get('availability') or '').strip().upper()
    pct = player.get('availability_percent')
    try:
        pct = None if pct is None or pct == '' else float(pct)
    except (TypeError, ValueError):
        pct = None
    if status in UNKNOWN and pct is None:
        return 'unknown'
    if pct is not None and pct < 100:
        if pct <= 25:
            return 'percent_0_25'
        if pct <= 50:
            return 'percent_26_50'
        if pct <= 75:
            return 'percent_51_75'
        return 'percent_76_99'
    if status in CLEAR or (status in UNKNOWN and pct is not None):
        return 'clear'
    return 'flagged_' + status.lower()


def week_minutes(histories, week):
    """player_id -> minutes in `week`; players without a row for that week are omitted."""
    result = {}
    for item in histories:
        for row in item.get('rows') or []:
            if int(row.get('gameweekOrder', -1)) == week:
                result[str(item['player_id'])] = float(row.get('minutesPlayed') or 0)
    return result


def regular_ids(histories, week):
    """Players who played 60+ minutes in at least 2 of their last 3 rows before `week`.

    These are the players a lineup model would actually consider, so a missed game here is a
    genuine surprise absence rather than a squad-depth player who never plays.
    """
    ids = set()
    for item in histories:
        rows = sorted((r for r in item.get('rows') or [] if int(r.get('gameweekOrder', -1)) < week),
                      key=lambda r: int(r['gameweekOrder']))[-3:]
        if len(rows) >= 2 and sum(float(r.get('minutesPlayed') or 0) >= 60 for r in rows) >= 2:
            ids.add(str(item['player_id']))
    return ids


def evaluate(week, players, minutes, regulars=None):
    """Pure function: compare deadline-time buckets with realised minutes.

    With `regulars` (a set of player ids) the report also carries the same comparison for
    that segment under the key 'regulars'.
    """
    buckets = defaultdict(lambda: {'n': 0, 'played': 0, 'played_60plus': 0, 'minutes_sum': 0.0})
    missing_row = 0
    for player in players:
        pid = str(player['id'])
        if pid not in minutes:
            missing_row += 1
            continue
        b = buckets[status_bucket(player)]
        m = minutes[pid]
        b['n'] += 1
        b['played'] += m > 0
        b['played_60plus'] += m >= 60
        b['minutes_sum'] += m
    table = {}
    for name, b in sorted(buckets.items()):
        table[name] = {'n': b['n'], 'played': b['played'], 'zero_minutes': b['n'] - b['played'],
                       'played_pct': round(100 * b['played'] / b['n'], 1),
                       'played_60plus_pct': round(100 * b['played_60plus'] / b['n'], 1),
                       'mean_minutes': round(b['minutes_sum'] / b['n'], 1)}
    zero_total = sum(v['zero_minutes'] for v in table.values())
    zero_flagged = sum(v['zero_minutes'] for k, v in table.items() if k not in ('clear', 'unknown'))
    flagged_total = sum(v['n'] for k, v in table.items() if k not in ('clear', 'unknown'))
    flagged_played = sum(v['played'] for k, v in table.items() if k not in ('clear', 'unknown'))
    report = {'week': week, 'players_compared': sum(v['n'] for v in table.values()),
            'players_without_outcome_row': missing_row, 'by_bucket': table,
            'zero_minute_players': zero_total,
            'zero_minute_players_that_were_flagged': zero_flagged,
            'flagged_players': flagged_total, 'flagged_players_who_played': flagged_played,
            'recall_of_zero_minutes_pct': round(100 * zero_flagged / zero_total, 1) if zero_total else None,
            'precision_of_flag_pct': round(100 * (flagged_total - flagged_played) / flagged_total, 1)
            if flagged_total else None}
    if regulars is not None:
        report['regulars'] = evaluate(week, [p for p in players if str(p['id']) in regulars], minutes)
    return report


def load_snapshots(engine):
    """Read-only: (id, week, captured_at, deadline_at, classification, payload) for all snapshots."""
    from sqlalchemy import select
    from storage import models as m
    from analysis.prediction_tracking import parse_time
    cols = [m.snapshots.c.id, m.snapshots.c.gameweek, m.snapshots.c.captured_at_text,
            m.snapshots.c.deadline_at_text, m.snapshots.c.classification, m.snapshots.c.payload_text]
    with engine.connect() as db:
        rows = db.execute(select(*cols)).all()
    return [{'id': r[0], 'week': r[1], 'captured_at': parse_time(r[2]), 'deadline_at': parse_time(r[3]),
             'classification': r[4], 'payload': json.loads(r[5])} for r in rows]


def pick_status_snapshot(snapshots, week):
    """Latest snapshot of `week` captured at or before its deadline."""
    candidates = [s for s in snapshots if s['week'] == week and s['captured_at'] is not None
                  and (s['deadline_at'] is None or s['captured_at'] <= s['deadline_at'])]
    return max(candidates, key=lambda s: s['captured_at'], default=None)


def pick_outcome_snapshot(snapshots, week):
    """Earliest later snapshot whose stored histories contain a row for `week`."""
    for s in sorted((x for x in snapshots if x['week'] > week and x['captured_at'] is not None),
                    key=lambda x: (x['week'], x['captured_at'])):
        if week_minutes(s['payload'].get('histories') or [], week):
            return s
    return None


def run(weeks=None, engine=None):
    from storage.db import engine_from_env
    engine = engine or engine_from_env()
    snapshots = load_snapshots(engine)
    all_weeks = sorted({s['week'] for s in snapshots})
    reports = []
    for week in (weeks or all_weeks):
        status = pick_status_snapshot(snapshots, week)
        outcome = pick_outcome_snapshot(snapshots, week)
        if status is None or outcome is None:
            reports.append({'week': week, 'status': 'skipped',
                            'reason': 'no pre-deadline snapshot' if status is None
                            else 'no later snapshot with that week\'s history rows'})
            continue
        report = evaluate(week, status['payload']['players'],
                          week_minutes(outcome['payload']['histories'], week),
                          regulars=regular_ids(status['payload'].get('histories') or [], week))
        report.update(status='ok', status_snapshot=status['id'], status_captured_at=str(status['captured_at']),
                      outcome_snapshot=outcome['id'], outcome_snapshot_week=outcome['week'])
        reports.append(report)
    return reports


def print_report(reports):
    for r in reports:
        if r['status'] != 'ok':
            print(f"GW{r['week']}: skipped ({r['reason']})")
            continue
        print(f"\nGW{r['week']}  compared {r['players_compared']}  (status snapshot {r['status_snapshot'][:8]}, "
              f"outcome from GW{r['outcome_snapshot_week']} snapshot {r['outcome_snapshot'][:8]})")
        print(f"{'bucket':22}{'n':>5}{'played%':>9}{'60+%':>7}{'mean min':>10}{'zero-min':>10}")
        for name, v in r['by_bucket'].items():
            print(f"{name:22}{v['n']:>5}{v['played_pct']:>9}{v['played_60plus_pct']:>7}"
                  f"{v['mean_minutes']:>10}{v['zero_minutes']:>10}")
        print(f"zero-minute players: {r['zero_minute_players']}, flagged beforehand: "
              f"{r['zero_minute_players_that_were_flagged']} (recall {r['recall_of_zero_minutes_pct']}%)")
        print(f"flagged players: {r['flagged_players']}, actually missed: "
              f"{r['flagged_players'] - r['flagged_players_who_played']} (precision {r['precision_of_flag_pct']}%)")
        reg = r.get('regulars')
        if reg:
            print(f"\n  REGULARS only (60+ min in 2 of last 3 games): {reg['players_compared']} players")
            for name, v in reg['by_bucket'].items():
                print(f"  {name:22}{v['n']:>5}{v['played_pct']:>9}{v['played_60plus_pct']:>7}"
                      f"{v['mean_minutes']:>10}{v['zero_minutes']:>10}")
            print(f"  surprise absences (0 min): {reg['zero_minute_players']}, flagged beforehand: "
                  f"{reg['zero_minute_players_that_were_flagged']} (recall {reg['recall_of_zero_minutes_pct']}%)")


def main():
    parser = argparse.ArgumentParser(description=__doc__.split('\n')[0])
    parser.add_argument('--week', type=int, action='append', help='repeat for several weeks')
    args = parser.parse_args()
    reports = run(args.week)
    OUT.parent.mkdir(exist_ok=True)
    OUT.write_text(json.dumps(reports, ensure_ascii=False, indent=2), encoding='utf-8')
    print_report(reports)
    print('\nSaved', OUT)


if __name__ == '__main__':
    main()
