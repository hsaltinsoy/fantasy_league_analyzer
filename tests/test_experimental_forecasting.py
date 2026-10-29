import json
import math

import pytest

from analysis.experimental_forecasting import (ALPHA, BLEND, FEATURES, MIN_TRAIN,
    NAME, build_features, fit_ridge, forecast)
from app import create_app


def _history(points=(1, 2, 3), *, last_week=None):
    return [{'gameweekOrder': week, 'points': point, 'minutesPlayed': 90,
             'goals': 0, 'assists': 0} for week, point in enumerate(points, 1)]


def test_feature_builder_rejects_future_rows_and_cold_starts():
    prior = _history()
    assert build_features(prior, 4, 'MID')['points_3'] == 2
    assert build_features(prior, 4, 'MID')['points_5'] is None
    assert build_features(prior, 4, 'MID')['has_5_weeks'] == 0
    assert build_features(prior, 4, 'MID')['position_MID'] == 1
    with pytest.raises(ValueError, match='future'):
        build_features(prior, 3, 'MID')
    with pytest.raises(ValueError, match='three'):
        build_features(prior[:2], 4, 'MID')
    with pytest.raises(ValueError, match='position'):
        build_features(prior, 4, 'UNKNOWN')


def test_missing_optional_history_is_not_fabricated():
    prior = _history()
    del prior[0]['goals']
    features = build_features(prior, 4, 'DEF')
    assert features['goals_3'] is None
    assert features['points_3'] == 2


def test_ridge_uses_training_only_statistics_and_rejects_small_fit():
    rows = []
    for i in range(MIN_TRAIN):
        features = build_features(_history((i % 3, (i+1) % 4, (i+2) % 5)), 4,
                                  ('GK', 'DEF', 'MID', 'FWD')[i % 4])
        rows.append({'features': features, 'actual': float(i % 7)})
    with pytest.raises(ValueError, match='Insufficient'):
        fit_ridge(rows[:-1])
    model = fit_ridge(rows)
    assert model['alpha'] == ALPHA
    assert model['training_n'] == MIN_TRAIN
    prediction = forecast(model, rows[0]['features'])
    assert math.isfinite(prediction) and prediction >= 0
    unseen = dict(rows[0]['features'], goals_3=None)
    assert math.isfinite(forecast(model, unseen))


def test_report_matches_all_models_on_each_week_and_keeps_tiers_separate():
    for tier in ('official', 'combined'):
        with open(f'historical_data/experimental_phase15/ridge_{tier}.json', encoding='utf-8') as file:
            report = json.load(file)
        assert report['classification'] == 'retrospective_reconstruction'
        assert report['training_gap_gameweeks'] == 1
        for week in report['by_gameweek']:
            if week['status'] != 'retrospective_reconstruction':
                continue
            assert max(week['training_weeks']) <= week['week']-2
            assert {item['n'] for item in week['models'].values()} == {week['test_n']}
            assert NAME in week['models'] and BLEND in week['models']


def test_dashboard_labels_experiment_without_activating_it():
    client = create_app().test_client()
    page = client.get('/')
    assert page.status_code == 200
    assert b'Experimental Models' in page.data
    assert b'Not used by production lineup' in page.data
    assert b'one-gameweek horizon' in page.data
    assert b'GW9' not in page.data or b'Retrospective' in page.data
    # Production form still offers its original five model variants only.
    form = page.get_data(as_text=True).split('</form>', 1)[0]
    assert NAME not in form
