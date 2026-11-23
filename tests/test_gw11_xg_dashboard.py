from app import create_app


def test_dashboard_exposes_explicit_experimental_parameters():
    client = create_app().test_client()
    for route in ('/', '/lineup'):
        page = client.get(route).get_data(as_text=True)
        assert 'name="adjustment_model"' in page
        assert 'value="position_aware_xg"' in page
        assert 'name="sensitivity"' in page
        assert 'value="0.4"' in page
        if route == '/':
            assert 'experimental_lineup.js' in page
        else:
            assert "new URLSearchParams(new FormData(" in page
        if route == '/':
            script = client.get('/static/experimental_lineup.js').get_data(as_text=True)
            assert 'team_name' in script
            assert 'percentage_delta' in script
            assert 'Expected total fantasy points' in script
            assert 'Risk-adjusted optimization score' in script
            assert 'XI expected xPts' in script
            assert "['Base model', data.model]" in script
            assert "['Risk profile', data.risk_profile]" in script


def test_experimental_parameter_pair_must_be_explicit():
    client = create_app().test_client()
    response = client.get('/api/lineup/generate?week=11&model=short_form_3w'
                          '&adjustment_model=position_aware_xg&sensitivity=0')
    assert response.status_code == 400
    assert 'Invalid experimental adjustment' in response.get_json()['error']
