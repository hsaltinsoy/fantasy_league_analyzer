"""Opt-in live xG pool adjustments; production prediction remains the default."""
from statistics import mean

from analysis.football_data_team_features import team_features, fixture_features
from analysis.football_data_position_aware import signal, clamp
from analysis.football_data_midweek import adjustment as uniform_adjustment
from storage.football_data_repository import FootballDataRepository


def make_adjuster(engine, archive, week, cutoff, mode, strength):
    if mode not in ('position_aware_xg', 'uniform_xg') or strength not in (0.0, .4):
        raise ValueError('Unsupported experimental adjustment or sensitivity')
    matches = FootballDataRepository(engine).matches_before(cutoff)
    features = team_features(matches)
    if not features:
        raise ValueError('No pre-cutoff Football-Data matches available')
    reference = {
        'xg': mean(v['xg_for'] for v in features.values() if v['xg_for'] is not None),
        'sot': mean(v['shots_on_target_per_match'] for v in features.values()
                    if v['shots_on_target_per_match'] is not None),
    }
    home_teams = {str(match['homeClubId']) for match in archive['weeks'][str(week)]['matches']}
    def adjust(pool):
        updated = []
        for item in pool:
            evidence = fixture_features(features, item['team'], item['opponent'])
            if evidence is None:
                raise ValueError(f'Missing Football-Data team features for {item["team"]}')
            base = item['xpts']
            if mode == 'uniform_xg':
                delta, _ = uniform_adjustment(features, item['team'], item['opponent'], strength)
                drivers = {'uniform_xg_signal': delta / strength if strength else 0.0}
            else:
                raw, drivers = signal({**item, 'home': item['team'] in home_teams,
                                       'football_data': evidence}, reference)
                delta = clamp(strength * raw, .15)
            updated.append({**item, 'baseline_xpts': base,
                'xpts': round(max(.1, base * (1 + delta)), 3),
                'adjustment_fraction': delta, 'football_data': evidence,
                'position_drivers': drivers})
        return updated
    return adjust, {'source_matches': len(matches), 'feature_teams': len(features),
                    'cutoff_utc': cutoff.isoformat(), 'mode': mode, 'sensitivity': strength,
                    'experimental': True, 'trained_coefficients': False}
