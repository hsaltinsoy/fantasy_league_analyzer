from analysis.benchmark_verification import OFFICIAL_DEADLINE_URL, FIXTURE_ENDPOINT, provenance


def test_local_predeadline_is_not_independently_verified():
    snapshot={'captured_at':'2026-10-29T12:58:28Z',
              'deadline_at':'2026-10-30T16:00:00Z','deadline_source':None,
              'classification':'live',
              'source':{'fixtures':FIXTURE_ENDPOINT,
                        'fixtures_retrieved_at':'2026-10-29T12:58:25Z'}}
    prediction={'created_at':'2026-10-29T13:42:39Z','status':'deadline_unknown'}
    result=provenance(prediction,snapshot)
    assert result['status']=='locally_recorded_pre_deadline_not_verified'
    assert result['stored_status']=='deadline_unknown'
    assert result['deadline_source_url']==OFFICIAL_DEADLINE_URL
    assert result['deadline_timezone']=='UTC'
    assert result['independently_verified'] is False
    # A historical stored label cannot be upgraded without independent evidence.
    prediction['status']='verified_pre_deadline'
    assert provenance(prediction,snapshot)['status']=='locally_recorded_pre_deadline_not_verified'


def test_postdeadline_historical_and_unknown_are_distinct():
    snapshot={'captured_at':'2026-10-29T12:00:00Z',
              'deadline_at':'2026-10-30T16:00:00Z','deadline_source':OFFICIAL_DEADLINE_URL,
              'classification':'live',
              'source':{'deadline_source_url':OFFICIAL_DEADLINE_URL,
                        'deadline_retrieved_at':'2026-10-29T11:59:00Z'}}
    prediction={'created_at':'2026-10-31T12:00:00Z','status':'post_deadline'}
    assert provenance(prediction,snapshot)['status']=='post_deadline'
    snapshot['classification']='historical_reconstruction'
    assert provenance(prediction,snapshot)['status']=='historical_reconstruction_not_verified'
    snapshot['classification']='live'
    snapshot['deadline_at']=None
    assert provenance(prediction,snapshot)['status']=='deadline_unknown'
    snapshot['deadline_at']='2026-10-30T16:00:00Z'
    snapshot['source']['deadline_retrieved_at']='invalid'
    prediction['created_at']='2026-10-29T13:00:00Z'
    assert provenance(prediction,snapshot)['status']=='deadline_unknown'
