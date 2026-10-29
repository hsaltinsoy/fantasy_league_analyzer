from ortools.sat.python import cp_model
from collections import Counter


FORMATIONS = ((3,4,3), (3,5,2), (4,3,3), (4,4,2), (4,5,1), (5,3,2), (5,4,1))


def _optimize_formation(players, formation, budget=100.0, max_per_team=3, time_limit=4, risk_profile="balanced"):
    """Maximise projected starting XI + captain bonus under fantasy squad rules.

    Each player: id, name, team, position (GK/DEF/MID/FWD), price, xpts.
    """
    requirements = {'GK': 2, 'DEF': 5, 'MID': 5, 'FWD': 3}
    counts = Counter(p['position'] for p in players)
    shortages = [f"{pos}: {counts[pos]}/{needed}" for pos, needed in requirements.items() if counts[pos] < needed]
    if shortages:
        return {'error': 'Yeterli oyuncu yok — ' + ', '.join(shortages), 'position_counts': dict(counts)}
    minimum_cost = sum(sum(sorted(float(p['price']) for p in players if p['position'] == pos)[:needed]) for pos, needed in requirements.items())
    if minimum_cost > budget + 1e-7:
        return {'error': f'En ucuz 15 oyuncu bile {minimum_cost:.2f} milyon; bütçe {budget:.2f} milyon.', 'minimum_cost': round(minimum_cost,2)}
    model = cp_model.CpModel()
    squad = {p['id']: model.NewBoolVar(f"s_{p['id']}") for p in players}
    start = {p['id']: model.NewBoolVar(f"x_{p['id']}") for p in players}
    captain = {p['id']: model.NewBoolVar(f"c_{p['id']}") for p in players}
    model.Add(sum(squad.values()) == 15)
    model.Add(sum(start.values()) == 11)
    model.Add(sum(captain.values()) == 1)
    for p in players:
        i = p['id']
        model.Add(start[i] <= squad[i])
        model.Add(captain[i] <= start[i])
    for position, count in [('GK', 2), ('DEF', 5), ('MID', 5), ('FWD', 3)]:
        model.Add(sum(squad[p['id']] for p in players if p['position'] == position) == count)
    model.Add(sum(start[p['id']] for p in players if p['position'] == 'GK') == 1)
    for position, count in zip(('DEF','MID','FWD'), formation):
        model.Add(sum(start[p['id']] for p in players if p['position'] == position) == count)
    teams = {p['team'] for p in players}
    for team in teams:
        model.Add(sum(squad[p['id']] for p in players if p['team'] == team) <= max_per_team)
    model.Add(sum(round(p['price'] * 100) * squad[p['id']] for p in players) <= round(budget * 100))
    # Maximize XI + captain first; use bench quality as a secondary tie-breaker.
    # 1/100 bench weight is intentionally small so it cannot dominate the XI.
    # Match-level dependence: opposing attackers vs defenders cannot both
    # realise all of their clean-sheet/attacking upside in the same scenario.
    # This is a *risk preference* adjustment, not a claim that expected points
    # are mathematically lower. Only starting-XI pairs are penalised.
    risk_scale={'aggressive':0.0,'balanced':1.0,'cautious':2.0}
    if risk_profile not in risk_scale:
        raise ValueError('Unknown risk profile')
    conflict_terms=[]
    conflict_pairs=[]
    for idx, defender in enumerate(players):
        if defender['position'] not in ('GK','DEF'): continue
        opponent=str(defender.get('opponent',''))
        if not opponent: continue
        for attacker in players:
            if attacker['position'] not in ('MID','FWD') or str(attacker['team'])!=opponent: continue
            if str(attacker.get('opponent',''))!=str(defender['team']):continue
            both=model.NewBoolVar(f"conflict_{defender['id']}_{attacker['id']}")
            model.Add(both <= start[defender['id']])
            model.Add(both <= start[attacker['id']])
            model.Add(both >= start[defender['id']] + start[attacker['id']] - 1)
            # 0.18 points per opposing starter pair at balanced profile.
            # No absolute prohibition; higher projected upside may outweigh it.
            coefficient=round(0.18*risk_scale[risk_profile]*10000)
            if coefficient:
                conflict_terms.append(coefficient*both)
            conflict_pairs.append((defender,attacker,both))
    model.Maximize(sum(round(p['xpts'] * 10000) * start[p['id']] + round(p.get('captain_bonus_xpts', p['xpts']) * 10000) * captain[p['id']] + round(p['xpts'] * 100) * (squad[p['id']] - start[p['id']]) for p in players) - sum(conflict_terms))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = time_limit
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {'error': f'Kadro oluşturulamadı. Pozisyon sayıları: {dict(counts)}; pozisyon bazında teorik en düşük maliyet: {minimum_cost:.2f} milyon. Takım başına {max_per_team} sınırı veya bütçe nedeniyle mümkün olmayabilir.'}
    selected_conflicts=[{'defender':d['name'],'attacker':a['name'],'fixture':f"{d['team']} vs {a['team']}"} for d,a,v in conflict_pairs if solver.Value(v)]
    risk_penalty=round(0.18*risk_scale[risk_profile]*len(selected_conflicts),2)
    return {
        'risk_profile':risk_profile,'risk_penalty':risk_penalty,'opposing_pairs':selected_conflicts,
        'risk_adjusted_objective':round(sum(float(p['xpts'])*solver.Value(start[p['id']]) + float(p.get('captain_bonus_xpts',p['xpts']))*solver.Value(captain[p['id']]) + .01*float(p['xpts'])*(solver.Value(squad[p['id']])-solver.Value(start[p['id']])) for p in players)-risk_penalty,4),
        'squad': [p for p in players if solver.Value(squad[p['id']])],
        'starting_xi': [p for p in players if solver.Value(start[p['id']])],
        'captain': next(p for p in players if solver.Value(captain[p['id']])),
        'expected_points': round(sum(float(p['xpts']) * solver.Value(start[p['id']]) + float(p.get('captain_bonus_xpts', p['xpts'])) * solver.Value(captain[p['id']]) for p in players), 2),
        'status': 'optimal' if status == cp_model.OPTIMAL else 'feasible',
        'formation': '-'.join(map(str, formation)),
        'squad_cost': round(sum(float(p['price']) * solver.Value(squad[p['id']]) for p in players), 2),
    }


def optimize(players, budget=100.0, max_per_team=3, risk_profile="balanced"):
    """Jointly choose 15 players, starting XI, captain, and best legal formation.

    Each formation is solved independently against the *entire* player pool.
    A time-limited feasible solution is not a proof of global optimality.
    """
    comparisons = []
    solutions = {}
    errors = []
    for formation in FORMATIONS:
        name = '-'.join(map(str, formation))
        result = _optimize_formation(players, formation, budget, max_per_team, risk_profile=risk_profile)
        if 'error' in result:
            errors.append(result['error'])
            comparisons.append({'formation': name, 'status': 'infeasible', 'expected_points': None})
        else:
            solutions[name] = result
            comparisons.append({'formation': name, 'status': result['status'],
                                'expected_points': result['expected_points'],
                                'squad_cost': result['squad_cost'], 'risk_penalty':result['risk_penalty'], 'risk_adjusted_objective':result['risk_adjusted_objective']})
    if not solutions:
        return {'error': errors[0] if errors else 'Geçerli formasyon bulunamadı',
                'formation_comparison': comparisons}
    best = max(solutions.values(), key=lambda r: r['risk_adjusted_objective'])
    # Keep the actual solutions returned by each solve; never re-solve the winner
    # because time-limited CP-SAT runs can yield different feasible squads.
    output = dict(best)
    output['formation_comparison'] = sorted(
        comparisons, key=lambda r: r.get('risk_adjusted_objective') if r.get('risk_adjusted_objective') is not None else -1,
        reverse=True)
    output['formation_solutions'] = solutions
    output['all_formations_proven_optimal'] = all(
        r['status'] == 'optimal' for r in solutions.values())
    return output
