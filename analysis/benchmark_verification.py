"""Read-only provenance labels; local clocks never create independent proof."""
from data_sources.tff_official import BASE
from analysis.prediction_tracking import parse_time

FIXTURE_ENDPOINT='/api/backend/projection/stats/fixtures?league-id=1'
OFFICIAL_DEADLINE_URL=BASE+FIXTURE_ENDPOINT


def provenance(prediction, snapshot):
    """Describe evidence without rewriting an immutable stored status."""
    source=snapshot.get('source') or {}
    captured=parse_time(snapshot.get('captured_at'))
    created=parse_time(prediction.get('created_at'))
    deadline=parse_time(snapshot.get('deadline_at'))
    retrieved=parse_time(source.get('deadline_retrieved_at') or source.get('fixtures_retrieved_at'))
    url=source.get('deadline_source_url') or snapshot.get('deadline_source') or source.get('fixtures')
    if url==FIXTURE_ENDPOINT:
        url=OFFICIAL_DEADLINE_URL
    if snapshot.get('classification')=='historical_reconstruction':
        status='historical_reconstruction_not_verified'
        reason='Retrospective input reconstruction'
    elif deadline and created and created>=deadline:
        status='post_deadline'
        reason='Local creation timestamp is at or after the recorded deadline'
    elif not deadline:
        status='deadline_unknown'
        reason='No valid timezone-aware deadline in the immutable snapshot'
    elif url==OFFICIAL_DEADLINE_URL and retrieved and captured and created and retrieved<=captured<=created<deadline:
        status='locally_recorded_pre_deadline_not_verified'
        reason='Official deadline was retrieved before locally recorded creation; no independent timestamp receipt exists'
    else:
        status='deadline_unknown'
        reason='Deadline provenance or local timestamp ordering is incomplete'
    return {'status':status,'stored_status':prediction.get('status'),'reason':reason,
            'deadline_at':snapshot.get('deadline_at'),
            'deadline_source_url':url if url==OFFICIAL_DEADLINE_URL else None,
            'deadline_retrieved_at':source.get('deadline_retrieved_at') or source.get('fixtures_retrieved_at'),
            'deadline_timezone':source.get('deadline_timezone') or ('UTC' if str(snapshot.get('deadline_at') or '').endswith('Z') else None),
            'independently_verified':False}
