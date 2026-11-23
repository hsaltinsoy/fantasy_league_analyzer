function renderExperimentalLineup(data, box) {
  box.replaceChildren();
  const add = (parent, tag, className, value) => {
    const el = document.createElement(tag);
    if (className) el.className = className;
    if (value != null) el.textContent = String(value);
    parent.append(el);
    return el;
  };
  const fmt = (value, places = 2) => value == null || !Number.isFinite(Number(value)) ? 'Unavailable' : Number(value).toFixed(places);
  const captain = (data.starting_xi || []).find(player => player.captain);
  const xi = (data.starting_xi || []).reduce((sum, player) => sum + Number(player.xpts || 0), 0);
  const total = data.expected_fantasy_points ?? (captain ? xi + Number(captain.xpts) : null);
  const summary = add(box, 'div', 'experimental-summary');
  const fields = [
    ['Gameweek', `GW${data.week ?? '—'}`], ['Base model', data.model],
    ['Adjustment model', data.display_model || data.experimental_adjustment?.mode],
    ['Sensitivity', data.experimental_adjustment?.sensitivity == null ? 'Unavailable' : `${Math.round(data.experimental_adjustment.sensitivity * 100)}%`],
    ['Risk profile', data.risk_profile], ['Formation', data.formation],
    ['Captain', captain?.name || data.captain || 'Unavailable'], ['Status', 'Experimental · untrained'],
    ['XI expected xPts', `${fmt(xi)} xPts`],
    ['Expected captain bonus', `${fmt(captain?.xpts)} xPts`],
    ['Expected total fantasy points', `${fmt(total)} xPts`],
    ['Risk-adjusted optimization score', fmt(data.risk_adjusted_objective)]
  ];
  for (const [label, value] of fields) {
    const card = add(summary, 'div', '');
    add(card, 'strong', '', label);
    add(card, 'span', '', value ?? 'Unavailable');
  }
  const advanced = add(box, 'details', 'experimental-advanced');
  add(advanced, 'summary', '', 'Advanced scoring details');
  add(advanced, 'p', '', `Risk-adjusted captain bonus: ${fmt(data.captain_bonus_xpts, 3)} xPts. Optimizer total before bench and fixture penalties: ${fmt(data.expected_points)}.`);
  const details = player => {
    const baseline = player.baseline_xpts;
    const adjusted = player.xpts;
    const absolute = player.absolute_delta ?? (baseline == null || adjusted == null ? null : Number(adjusted) - Number(baseline));
    const percent = player.percentage_delta ?? (baseline == null || !Number(baseline) || absolute == null ? null : 100 * absolute / Number(baseline));
    return `${player.name || 'Unknown player'} · ${player.team_name || `Club ${player.team ?? 'unknown'}`} · ${player.position || 'Unknown position'} · Baseline ${fmt(baseline, 3)} xPts · Adjusted ${fmt(adjusted, 3)} xPts · Change ${fmt(absolute, 3)} xPts (${fmt(percent)}%) · ${data.display_model || 'No model adjustment'}`;
  };
  const playerCard = (player, bench = false) => {
    const card = document.createElement('button');
    card.type = 'button';
    card.className = bench ? 'experimental-bench-player' : 'dashboard-player';
    card.title = details(player);
    card.setAttribute('aria-label', details(player));
    add(card, 'strong', '', player.name || 'Unknown player');
    if (player.captain) add(card, 'span', 'captain-mark', 'C');
    if (player.vice_captain || player.viceCaptain) add(card, 'span', 'vice-captain-mark', 'VC');
    add(card, 'small', '', player.team_name || `Club ${player.team ?? 'unknown'}`);
    add(card, 'span', '', `${fmt(player.xpts)} xPts`);
    const popup = add(card, 'span', 'experimental-player-detail', details(player));
    popup.hidden = true;
    card.addEventListener('click', () => { popup.hidden = !popup.hidden; });
    return card;
  };
  add(box, 'h3', '', 'Starting XI');
  const pitch = add(box, 'div', 'dashboard-pitch experimental-pitch');
  pitch.setAttribute('aria-label', `${data.formation || 'Unknown formation'} football pitch`);
  for (const position of ['FWD', 'MID', 'DEF', 'GK']) {
    const line = add(pitch, 'div', 'dashboard-line');
    line.dataset.position = position;
    for (const player of (data.starting_xi || []).filter(item => item.position === position)) line.append(playerCard(player));
  }
  add(box, 'h3', '', 'Bench');
  const bench = add(box, 'div', 'experimental-bench');
  for (const player of data.bench || []) {
    const item = add(bench, 'div', 'experimental-bench-item');
    add(item, 'small', '', `Substitute ${player.position || 'unknown'}`);
    item.append(playerCard(player, true));
  }
}

const form = document.getElementById('squad-form');
if (form) form.addEventListener('submit', async event => {
  event.preventDefault();
  const button = form.querySelector('button[type=submit]');
  const status = document.getElementById('squad-status');
  button.disabled = true;
  status.textContent = 'Generating and saving the lineup…';
  try {
    const response = await fetch('/api/lineup/generate?' + new URLSearchParams(new FormData(form)));
    const data = await response.json();
    if (!response.ok) throw Error(data.error || 'Lineup generation failed');
    if (!data.experimental_adjustment) {
      status.textContent = 'Prediction saved. Loading the lineup';
      window.location.reload();
      return;
    }
    let box = document.getElementById('experimental-lineup');
    if (!box) {
      box = document.createElement('section');
      box.id = 'experimental-lineup';
      box.className = 'panel';
      form.after(box);
    }
    renderExperimentalLineup(data, box);
    status.textContent = `Showing ${data.display_model || 'experimental adjustment'} on input ${data.experimental_adjustment.input_snapshot_sha256?.slice(0, 12) || 'unavailable'}. Saved report ${data.report_id || 'unavailable'}.`;
  } catch (error) {
    status.textContent = error.message;
    status.classList.add('error');
  } finally {
    button.disabled = false;
  }
});
