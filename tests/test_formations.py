from analysis.optimizer import optimize, FORMATIONS, FORMATION_POLICIES, LEGACY_FORMATIONS

def test_formation_joint_optimization():
    players=[]
    ident=1
    for position,n in [('GK',4),('DEF',9),('MID',9),('FWD',6)]:
        for i in range(n):
            players.append(dict(id=ident, name=f'{position}{i}', position=position, team=str(ident), price=4, xpts=10 if (position=='MID' and i<5) else (8 if position=='FWD' else 3)))
            ident+=1
    result=optimize(players)
    assert 'error' not in result, result
    assert result['formation'] in {'-'.join(map(str,f)) for f in FORMATIONS}
    assert len(result['starting_xi'])==11 and len(result['squad'])==15
    assert sum(p['position']=='GK' for p in result['starting_xi'])==1
    assert result['formation']=='3-5-2'
    assert len(result['formation_comparison'])==len(FORMATIONS)
    assert result['captain']['id'] in {p['id'] for p in result['starting_xi']}


def test_each_formation_keeps_its_own_squad():
    players = []
    for position, count in [('GK', 4), ('DEF', 9), ('MID', 9), ('FWD', 6)]:
        for i in range(count):
            ident = len(players) + 1
            players.append(dict(id=ident, name=f'{position}{i}', position=position,
                                team=str(ident), price=4, xpts=2+i))
    result = optimize(players)
    assert len(result['formation_solutions']) == len(FORMATIONS)
    for name, solution in result['formation_solutions'].items():
        assert solution['formation'] == name
        assert len(solution['squad']) == 15
        assert len(solution['starting_xi']) == 11
        assert sum(p['price'] for p in solution['squad']) <= 100
        d, m, f = map(int, name.split('-'))
        for pos, expected in [('GK',1),('DEF',d),('MID',m),('FWD',f)]:
            assert sum(p['position']==pos for p in solution['starting_xi']) == expected
        assert solution['captain']['id'] in {p['id'] for p in solution['starting_xi']}


def test_formation_policies():
    # Current TFF rules: 1 GK, 3-5 DEF, 2-5 MID, 1-3 FWD -> eight legal formations.
    assert set(FORMATIONS) == {(3,4,3), (3,5,2), (4,3,3), (4,4,2), (4,5,1), (5,2,3), (5,3,2), (5,4,1)}
    assert FORMATION_POLICIES['legacy_pre39_v1'] == LEGACY_FORMATIONS
    assert len(LEGACY_FORMATIONS) == 7 and (5,2,3) not in LEGACY_FORMATIONS
