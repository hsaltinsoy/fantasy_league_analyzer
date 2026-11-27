"""Common-player scoring of one complete, finalized six-model batch."""
from math import sqrt
from statistics import mean

from analysis.six_model_batch import NAMES, NAMES_V2


def _ranks(values):
    order = sorted(range(len(values)), key=lambda i: values[i])
    ranks = [0.0] * len(values)
    i = 0
    while i < len(order):
        j = i + 1
        while j < len(order) and values[order[j]] == values[order[i]]:
            j += 1
        for index in order[i:j]:
            ranks[index] = (i + 1 + j) / 2
        i = j
    return ranks


def _spearman(a, b):
    if len(a) < 2 or len(set(a)) < 2 or len(set(b)) < 2:
        return None
    ar, br = _ranks(a), _ranks(b)
    am, bm = mean(ar), mean(br)
    numerator = sum((x-am)*(y-bm) for x,y in zip(ar,br))
    denominator = sqrt(sum((x-am)**2 for x in ar)*sum((y-bm)**2 for y in br))
    return round(numerator/denominator, 4) if denominator else None


def evaluate(predictions, actuals, *, official_finalized):
    if set(predictions) not in (set(NAMES), set(NAMES_V2)):
        return {'status': 'incomplete_batch'}
    if not official_finalized:
        return {'status': 'official_results_not_final'}
    pools = [{str(p['id']) for p in row['starting_xi'] + row['bench']}
             for row in predictions.values()]
    common = set.intersection(*pools)
    all_selected = set.union(*pools)
    missing = sorted(pid for pid in all_selected if pid not in actuals)
    if missing:
        return {'status': 'missing_actual_results', 'missing_player_ids': missing,
                'coverage': round((len(all_selected)-len(missing))/len(all_selected), 4)}
    result = {}
    for name, row in predictions.items():
        by_id = {str(p['id']): p for p in row['starting_xi'] + row['bench']}
        ids = sorted(common)
        predicted = [float(by_id[pid]['xpts']) for pid in ids]
        observed = [float(actuals[pid]) for pid in ids]
        errors = [p-a for p,a in zip(predicted,observed)]
        xi = row['starting_xi']
        captain = next((p for p in xi if p.get('captain')), None)
        if captain is None or len(xi) != 11 or len(row['bench']) != 4:
            return {'status': 'incomplete_lineup', 'model': name}
        xi_points = sum(float(actuals[str(p['id'])]) for p in xi)
        result[name] = {'common_player_n': len(ids),
                        'mae': round(mean(abs(e) for e in errors), 3) if errors else None,
                        'rmse': round(sqrt(mean(e*e for e in errors)), 3) if errors else None,
                        'spearman': _spearman(predicted, observed),
                        'actual_xi': round(xi_points, 2),
                        'actual_captain_bonus': float(actuals[str(captain['id'])]),
                        'actual_total': round(xi_points + float(actuals[str(captain['id'])]), 2),
                        'actual_bench': round(sum(float(actuals[str(p['id'])]) for p in row['bench']), 2)}
    return {'status': 'complete', 'common_player_ids': sorted(common),
            'coverage': 1.0, 'models': result}
