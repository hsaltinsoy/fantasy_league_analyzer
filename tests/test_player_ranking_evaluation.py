import copy
import json

import pytest

from analysis import player_ranking_evaluation as ranking
from app import create_app


def test_tied_scores_use_average_ranks_and_fractional_cutoff():
    rows = [{'player_id': str(i), 'actual': 2 if i < 21 else 0,
             'predictions': {'test': 2 if i < 21 else 0}} for i in range(25)]
    metric = ranking.ranking_metrics(rows, 'test')
    assert metric['spearman'] == 1
    assert metric['actual_tie_at_10'] and metric['predicted_tie_at_20']
    assert metric['precision_at_20'] == metric['recall_at_20'] == round(20 / 21, 4)
    assert metric['ndcg_at_20'] is not None


def test_missing_scores_and_duplicate_players_are_rejected():
    rows = [{'player_id': '1', 'actual': 2, 'predictions': {'a': 3}}]
    with pytest.raises(ValueError):
        ranking.ranking_metrics(rows * 2, 'a')
    for invalid in (None, '3', float('nan')):
        changed = copy.deepcopy(rows)
        changed[0]['predictions']['a'] = invalid
        with pytest.raises(ValueError):
            ranking.ranking_metrics(changed, 'a')


def test_short_samples_have_unavailable_top_k():
    rows = [{'player_id': str(i), 'actual': i, 'predictions': {'a': i}}
            for i in range(15)]
    metric = ranking.ranking_metrics(rows, 'a')
    assert metric['precision_at_10'] == 1
    assert metric['precision_at_20'] is None
    assert metric['recall_at_20'] is None
    assert metric['ndcg_at_20'] is None


def test_forecast_inputs_exclude_target_result(monkeypatch):
    position = {'1': {'position': 'MID', 'source_effective_week': 1}}
    fixtures = {week: {'gameweek_id': week, 'matches': []} for week in range(1, 5)}
    history = [{'gameweekOrder': week, 'points': week, 'played': True} for week in range(1, 5)]
    monkeypatch.setattr(ranking, '_positions_for_week', lambda *_: (position, []))
    monkeypatch.setattr(ranking, '_fixture_teams', lambda *_: {'club'})
    monkeypatch.setattr(ranking, 'valid_row', lambda row, *_: (True, None))

    def prior_only(past, week):
        assert week == 4
        assert [row['gameweekOrder'] for row in past] == [1, 2, 3]
        return {name: 2.0 for name in ranking.BASELINES}

    monkeypatch.setattr(ranking, 'baseline_predictions', prior_only)
    monkeypatch.setattr(ranking, 'forecast_with_prior_position',
                        lambda position, past, week, model: prior_only(past, week) and 2.0)
    first = ranking._week_samples(4, position, fixtures, {'1': history}, 'official_only')['all'][0]
    changed = copy.deepcopy(history)
    changed[-1]['points'] = 99
    second = ranking._week_samples(4, position, fixtures, {'1': changed}, 'official_only')['all'][0]
    assert first['predictions'] == second['predictions']
    assert first['actual'] != second['actual']


def test_report_samples_are_identical_across_models_and_tiers():
    for source in ('official', 'combined'):
        with open(f'historical_data/recovered/player_ranking_{source}.json', encoding='utf-8') as handle:
            report = json.load(handle)
        assert report['classification'] == 'retrospective_ranking_not_predeadline_verified'
        for week in report['by_gameweek']:
            assert {m['n'] for m in week['metrics']['all'].values()} == {week['sample_n']}
            assert {m['n'] for m in week['metrics']['appeared'].values()} == {week['appeared_n']}
        assert len(report['gw9_matched']['metrics']['all']) == 7


def test_benchmark_shows_ranking_tiers_and_read_only_report():
    client = create_app().test_client()
    page = client.get('/benchmark')
    assert page.status_code == 200
    assert b'Player Ranking Accuracy' in page.data
    assert b'Official-only evidence' in page.data
    assert b'lower-confidence workbook' in page.data
    assert client.get('/api/benchmark/player-ranking?source=official').json['source_policy'] == 'official_only'
    assert client.get('/api/benchmark/player-ranking?source=unknown').status_code == 400
