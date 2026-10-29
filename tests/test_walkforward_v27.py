from analysis.walkforward_v27 import fixture_multipliers, build_v27_pool, walk_forward


def records():
    players = []
    for i in range(18):
        pos = 'GK' if i < 2 else 'DEF' if i < 8 else 'MID' if i < 14 else 'FWD'
        p = {'id': i + 1, 'name': f'Player {i}', 'position': pos, 'team': str(i // 3)}
        rows = [{'gameweekOrder': w, 'points': 4 + (i % 3), 'minutesPlayed': 90,
                 'started': True, 'cost': 5, 'opponentClubId': str(w % 2)} for w in range(1, 7)]
        players.append((p, rows))
    return players


def test_fixture_excludes_target_points():
    r = records()
    a = fixture_multipliers(r, 5, min_samples=1)
    r[0][1][4]['points'] = 10000  # target week only
    b = fixture_multipliers(r, 5, min_samples=1)
    assert a == b


def test_fixture_fallback_and_coverage():
    r = records()
    pool, actual, coverage = build_v27_pool(r, 5, {'window': 3, 'shrinkage': 6, 'recent_mix': .6, 'recency': True})
    assert len(pool) == 18
    assert len(actual) == 18
    assert coverage['fixture_proxy_applied'] + coverage['fixture_proxy_unavailable'] == 18
    assert all(.925 <= p['fixture_factor'] <= 1.075 for p in pool)


def test_walk_forward_uses_prior_only():
    r = records()
    def fake_opt(pool):
        xi = pool[:11]
        return {'starting_xi': xi, 'captain': xi[0], 'formation': '4-4-2',
                'expected_points': round(sum(p['xpts'] for p in xi) + xi[0]['xpts'], 2),
                'squad_cost': 75, 'squad': pool[:15], 'formation_comparison': []}
    a = walk_forward(r, (4, 5), optimizer=fake_opt)
    selected = a['weeks'][1]['selected_model']
    r[0][1][4]['points'] = 999  # modify only current-week actual
    b = walk_forward(r, (4, 5), optimizer=fake_opt)
    assert b['weeks'][1]['selected_model'] == selected
    assert b['weeks'][1]['result']['predicted'] == a['weeks'][1]['result']['predicted']
