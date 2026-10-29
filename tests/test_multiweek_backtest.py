from analysis.multiweek_backtest import MODELS, build_week, compare, save_report


def fake_records():
    records = []
    for i in range(1, 17):
        pos = 'GK' if i <= 2 else 'DEF' if i <= 7 else 'MID' if i <= 12 else 'FWD'
        p = {'id': i, 'name': f'Player {i}', 'team': str((i-1)//2), 'position': pos}
        rows = [{'gameweekOrder': w, 'points': (i+w)%7, 'minutesPlayed': 90, 'cost': 4.0} for w in range(1, 10)]
        records.append((p, rows))
    return records


def fake_optimizer(pool):
    xi = pool[:11]
    captain = xi[0]
    return {'starting_xi': xi, 'captain': captain, 'expected_points': round(sum(p['xpts'] for p in xi)+captain['xpts'], 2),
            'formation': 'test', 'squad_cost': 60, 'squad': pool[:15], 'formation_comparison': []}


def test_no_target_leakage():
    records = fake_records()
    config = {'window': 5, 'shrinkage': 4, 'recent_mix': .55, 'recency': True}
    pool1, _, _ = build_week(records, 9, config)
    records[0][1][-1]['points'] = 9999
    pool2, _, _ = build_week(records, 9, config)
    assert [{k:v for k,v in p.items() if k != "actual_points"} for p in pool1] == [{k:v for k,v in p.items() if k != "actual_points"} for p in pool2]
    assert pool1[0]["actual_points"] != pool2[0]["actual_points"]


def test_holdout_selection_and_report(tmp_path):
    report = compare(fake_records(), (5,6,7,8), 9, optimizer=fake_optimizer)
    assert report['holdout']['week'] == 9
    assert set(report['models']) == set(MODELS)
    assert report['holdout']['actual'] is not None
    json_path, csv_path = save_report(report, tmp_path)
    assert json_path.exists() and csv_path.exists()
    assert len(csv_path.read_text(encoding='utf-8-sig').splitlines()) == 1 + len(MODELS) * 4 + 1


def test_target_after_training():
    try:
        compare(fake_records(), (5, 9), 9, optimizer=fake_optimizer)
    except ValueError as e:
        assert 'sonra' in str(e)
    else:
        assert False
