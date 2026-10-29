from io import BytesIO

from app import create_app


def test_json_array_is_rejected_without_server_error():
    client = create_app().test_client()
    for path in ('/api/projections/next-week', '/api/availability/check',
                 '/api/backtest/evaluate', '/api/optimize'):
        response = client.post(path, json=[])
        assert response.status_code == 400, path


def test_results_upload_without_fixtures_returns_client_error():
    client = create_app().test_client()
    response = client.post('/api/fixtures/analyze', data={
        'results': (BytesIO(b'Date,HomeTeam,AwayTeam,FTHG,FTAG\n'), 'results.csv')
    })
    assert response.status_code == 400
