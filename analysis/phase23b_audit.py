"""Read-only audit of what Phase 23B can evaluate without later-week inputs."""
import hashlib
import json
from pathlib import Path

from analysis.historical_walkforward import audit_coverage


def build(store=Path('historical_data')):
    store = Path(store)
    coverage = audit_coverage(store, store / 'walkforward_snapshots')
    recovered = store / 'recovered' / 'model_cumulative_matched.csv'
    return {
        'classification': 'phase23b_input_availability_audit',
        'completed_week_outcome_coverage': coverage['weeks'],
        'player_history_file_count': coverage['history_file_count'],
        'current_player_catalog_count': coverage['current_player_catalog_count'],
        'eligible_full_squad_evaluation_weeks': [row['week'] for row in coverage['weeks']
                                                  if row['input_snapshot_path'] is not None],
        'requested_ablations': {name: {'status': 'blocked',
                                        'reason': 'No complete predeadline player, fixture and feature snapshot'}
                                 for name in ('recent_form', 'fixture_difficulty', 'team_attacking_xg',
                                              'team_defensive_xg', 'home_away', 'rest_days',
                                              'availability', 'combined')},
        'existing_form_component_report': {'path': str(recovered),
                                           'sha256': hashlib.sha256(recovered.read_bytes()).hexdigest()
                                           if recovered.exists() else None,
                                           'classification': 'retrospective_form_component_only_not_predeadline_verified'},
        'warning': 'Current player catalog cannot reconstruct historical eligibility or prices. '
                   'Do not rank full models or optimize historical squads from this archive.'}


if __name__ == '__main__':
    print(json.dumps(build(), ensure_ascii=False, indent=2))
