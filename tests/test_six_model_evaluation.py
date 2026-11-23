from analysis.six_model_batch import NAMES
from analysis.six_model_evaluation import evaluate


def _predictions():
    xi = [{'id': i, 'xpts': float(i), 'captain': i == 1} for i in range(1, 12)]
    bench = [{'id': i, 'xpts': float(i)} for i in range(12, 16)]
    return {name: {'starting_xi': xi, 'bench': bench} for name in NAMES}


def test_common_player_metrics_and_captain_double_count():
    result = evaluate(_predictions(), {str(i): float(i) for i in range(1, 16)},
                      official_finalized=True)
    assert result['status'] == 'complete'
    assert len(result['common_player_ids']) == 15
    row = result['models']['short_form_3w']
    assert row['mae'] == 0
    assert row['rmse'] == 0
    assert row['spearman'] == 1
    assert row['actual_xi'] == 66
    assert row['actual_total'] == 67
    assert row['actual_bench'] == 54


def test_missing_or_unfinalized_actuals_never_become_zero():
    rows = _predictions()
    assert evaluate(rows, {}, official_finalized=False)['status'] == 'official_results_not_final'
    result = evaluate(rows, {'1': 1.0}, official_finalized=True)
    assert result['status'] == 'missing_actual_results'
    assert result['coverage'] < 1
