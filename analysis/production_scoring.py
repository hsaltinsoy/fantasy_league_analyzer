"""Production player scoring, kept separate from squad optimization."""
import math

from analysis.multiweek_backtest import MODELS, project


def lineup_player_points(player, past, model, fixture_factor=1.0, availability_factor=1.0):
    """The /lineup form forecast before captain and risk preferences."""
    return round(max(.1, project(player, past, MODELS[model]) * fixture_factor * availability_factor), 3)


def _js_number(value):
    if value is None or value == '':
        return 0.0
    try:
        return float(value)
    except (TypeError, ValueError):
        return float('nan')


def dashboard_player_points(player, prediction, fixture, decision, completed_rounds=9):
    """Port of index.html's final TFF/xgEdge blend; None means insufficient signal."""
    minutes = max(0, _js_number(player.get('minutes')) or 0)
    ppm = _js_number(player.get('points_per_match'))
    total = _js_number(player.get('total_points'))
    form = _js_number(player.get('form'))
    estimated_minutes = prediction.get('expected_minutes') if prediction else None
    expected_minutes = (max(0, min(90, _js_number(estimated_minutes)))
                        if estimated_minutes is not None else min(90, minutes / completed_rounds))
    minutes_factor = min(1, expected_minutes / 75)
    season_average = total / completed_rounds if math.isfinite(total) and total >= 0 else None
    historical = season_average if season_average is not None else ppm if math.isfinite(ppm) and ppm >= 0 else None
    attacking = prediction.get('expected_points') if prediction else None
    if historical is None and attacking is None:
        return None
    recent = min(9, form) if math.isfinite(form) and form >= 0 else None
    base = min(9, max(0, (historical or 0) * .8 +
                      (recent if recent is not None else historical or 0) * .2))
    estimate = base * (.55 + .45 * min(1, minutes / 540)) * minutes_factor
    if attacking is not None and math.isfinite(_js_number(attacking)):
        attacking = max(0, _js_number(attacking))
        estimate = .7 * estimate + .3 * min(9, attacking +
            (1.2 if player.get('position') in ('GK', 'DEF') else .5) * minutes_factor)
    fdr = _js_number(fixture.get('fdr')) if fixture else float('nan')
    if fixture and fixture.get('opponent') and math.isfinite(fdr) and 1 <= fdr <= 5:
        estimate *= max(.75, min(1.25, 1 + (3 - fdr) * .08))
    estimate *= _js_number(decision.get('factor', 1) if decision else 1)
    if expected_minutes < 15:
        estimate *= .35
    return math.floor(max(0, estimate) * 100 + .5) / 100
