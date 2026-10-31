from app import create_app


def test_dashboard_exposes_explicit_experimental_parameters():
    client = create_app().test_client()
    for route in ('/', '/lineup'):
        page = client.get(route).get_data(as_text=True)
        assert 'name="adjustment_model"' in page
        assert 'value="position_aware_xg"' in page
        assert 'name="sensitivity"' in page
        assert 'value="0.4"' in page
        assert "new URLSearchParams(new FormData(" in page
        if route == '/':
            assert 'team_name' in page
            assert 'percentage_delta' in page
            assert 'Captain-adjusted total' in page
            assert 'XI before captain' in page
            assert "['Base model',data.model]" in page
            assert "['Risk',data.risk_profile]" in page


def test_experimental_parameter_pair_must_be_explicit():
    client = create_app().test_client()
    response = client.get('/api/lineup/generate?week=11&model=short_form_3w'
                          '&adjustment_model=position_aware_xg&sensitivity=0')
    assert response.status_code == 400
    assert 'Invalid experimental adjustment' in response.get_json()['error']
