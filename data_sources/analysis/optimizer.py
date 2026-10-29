from ortools.sat.python import cp_model
from collections import Counter


def optimize(players, budget=100.0, max_per_team=3):
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
    model.Add(sum(start[p['id']] for p in players if p['position'] == 'DEF') >= 3)
    model.Add(sum(start[p['id']] for p in players if p['position'] == 'FWD') >= 1)
    model.Add(sum(start[p['id']] for p in players if p['position'] == 'DEF') <= 5)
    model.Add(sum(start[p['id']] for p in players if p['position'] == 'MID') <= 5)
    model.Add(sum(start[p['id']] for p in players if p['position'] == 'FWD') <= 3)
    teams = {p['team'] for p in players}
    for team in teams:
        model.Add(sum(squad[p['id']] for p in players if p['team'] == team) <= max_per_team)
    model.Add(sum(round(p['price'] * 100) * squad[p['id']] for p in players) <= round(budget * 100))
    # Maximize XI + captain first; use bench quality as a secondary tie-breaker.
    # 1/100 bench weight is intentionally small so it cannot dominate the XI.
    model.Maximize(sum(round(p['xpts'] * 10000) * (start[p['id']] + captain[p['id']]) + round(p['xpts'] * 100) * (squad[p['id']] - start[p['id']]) for p in players))
    solver = cp_model.CpSolver()
    solver.parameters.max_time_in_seconds = 15
    status = solver.Solve(model)
    if status not in (cp_model.OPTIMAL, cp_model.FEASIBLE):
        return {'error': f'Kadro oluşturulamadı. Pozisyon sayıları: {dict(counts)}; pozisyon bazında teorik en düşük maliyet: {minimum_cost:.2f} milyon. Takım başına {max_per_team} sınırı veya bütçe nedeniyle mümkün olmayabilir.'}
    return {
        'squad': [p for p in players if solver.Value(squad[p['id']])],
        'starting_xi': [p for p in players if solver.Value(start[p['id']])],
        'captain': next(p for p in players if solver.Value(captain[p['id']])),
        'expected_points': round(sum(float(p['xpts']) * (solver.Value(start[p['id']]) + solver.Value(captain[p['id']])) for p in players), 2),
        'status': 'optimal' if status == cp_model.OPTIMAL else 'feasible',
    }
