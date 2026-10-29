from analysis.walkforward_backtest import participation, week_pool, walk_forward, save_report
from tests.test_multiweek_backtest import fake_records, fake_optimizer


def test_participation_no_future_leak():
    records = fake_records()
    config = {'window': 3, 'shrinkage': 6, 'recent_mix': .6, 'recency': True}
    pool1, _, _ = week_pool(records, 9, config)
    records[0][1][-1]['points'] = 99999
    records[0][1][-1]['minutesPlayed'] = 0
    pool2, _, _ = week_pool(records, 9, config)
    assert [{k:v for k,v in p.items() if k != 'actual_points'} for p in pool1] == [{k:v for k,v in p.items() if k != 'actual_points'} for p in pool2]


def test_walkforward_selects_using_only_prior_rounds(tmp_path):
    models = {'a': {'window': 3, 'shrinkage': 6, 'recent_mix': .6, 'recency': True},
              'b': {'window': 5, 'shrinkage': 4, 'recent_mix': .55, 'recency': True}}
    report = walk_forward(fake_records(), (5,6,7), models=models, optimizer=fake_optimizer)
    assert report['weeks'][0]['selected_model'] is None
    assert report['weeks'][1]['training_weeks'] == [5]
    assert report['weeks'][2]['training_weeks'] == [5,6]
    j,c = save_report(report, tmp_path)
    assert j.exists() and c.exists()


def test_minutes_proxy_excludes_past_nonparticipants():
    records = fake_records()
    for r in records[0][1]:
        if r['gameweekOrder'] < 9:
            r['minutesPlayed'] = 0
    config = {'window': 3, 'shrinkage': 6, 'recent_mix': .6, 'recency': True}
    pool, _, cov = week_pool(records, 9, config)
    assert 1 not in {p['id'] for p in pool}
    assert cov['excluded_low_participation_proxy'] == 1
