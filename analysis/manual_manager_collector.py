"""Local, offline-only experimental manager-squad records."""
import csv
import io
import json
import os
import re
import tempfile
import unicodedata
import uuid
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

from analysis.optimizer import valid_formations

ROOT = Path(__file__).resolve().parents[1]
DEFAULT_STORE = ROOT / 'experimental_data' / 'manual_manager_squads.json'
PLAYER_FILE = ROOT / 'historical_data' / 'players.json'
HISTORY_FILE = ROOT / 'docs' / 'phase28_official_histories.json'
PHASE36_FILE = ROOT / 'docs' / 'phase36_free_external_data.json'


def catalogue(path=PLAYER_FILE):
    if not Path(path).exists():
        raise ValueError('Local TFF player catalogue unavailable; import is disabled')
    players = json.loads(Path(path).read_text(encoding='utf-8'))
    result = {int(p['id']): {'id': int(p['id']), 'name': p['name'], 'match_name': p.get('match_name') or '',
                           'position': p['position'], 'club': str(p.get('team', '')),
                           'label': f"{p['name']} (club {p.get('team', '')}, ID {p['id']})"}
              for p in players if p.get('id') is not None}
    if not result:
        raise ValueError('Local TFF player catalogue is empty')
    return result


def _name_key(value):
    value = unicodedata.normalize('NFKD', str(value).casefold().replace('ı', 'i'))
    value = ''.join(c for c in value if not unicodedata.combining(c))
    return ' '.join(re.findall(r'[a-z0-9]+', value))


def resolve_name(value, players):
    """Resolve exact name/label/short match name; reject ambiguous matches."""
    key = _name_key(value)
    if not key:
        raise ValueError('Player name is missing')
    labelled = [p for p in players.values() if _name_key(p['label']) == key]
    matches = labelled or [p for p in players.values()
                           if key in (_name_key(p['name']), _name_key(p.get('match_name', '')))]
    if len(matches) == 1:
        return matches[0]['id']
    if len(matches) > 1:
        raise ValueError('Ambiguous player name: ' + str(value) + '. Choose: ' + '; '.join(p['label'] for p in matches[:8]))
    from difflib import get_close_matches
    suggestions = get_close_matches(key, [_name_key(p['name']) for p in players.values()], n=4, cutoff=.55)
    names = [p['label'] for p in players.values() if _name_key(p['name']) in suggestions][:4]
    raise ValueError('Player not found: ' + str(value) + ('. Possible: ' + '; '.join(names) if names else ''))


def _validate_named_item(item, players, *, now=None):
    if not isinstance(item, dict):
        raise ValueError('object required')
    xi = item['starting_xi_names']
    bench = item['bench_names']
    if not isinstance(xi, list) or len(xi) != 11 or not isinstance(bench, list) or len(bench) != 4:
        raise ValueError('11 starting and four bench names required')
    converted = {k: v for k, v in item.items() if k not in
                 ('starting_xi_names', 'bench_names', 'captain_name', 'vice_captain_name', 'weekly_points')}
    for field, names in (('starting_xi_ids', xi), ('bench_ids', bench)):
        converted[field] = []
        for slot, name in enumerate(names, 1):
            try:
                converted[field].append(resolve_name(name, players))
            except ValueError as exc:
                raise ValueError(f'{"Starting XI" if field == "starting_xi_ids" else "Bench"} slot {slot}: {exc}') from exc
    for field, output_field in (('captain_name', 'captain_id'), ('vice_captain_name', 'vice_captain_id')):
        try:
            converted[output_field] = resolve_name(item[field], players)
        except ValueError as exc:
            raise ValueError(f'{field}: {exc}') from exc
    record = validate(converted, players, now=now)
    points = item.get('weekly_points')
    if points not in (None, ''):
        if type(points) not in (int, float) or points < 0 or points > 1000:
            raise ValueError('weekly_points must be a nonnegative number')
        record['weekly_points_displayed'] = points
    else:
        record['weekly_points_displayed'] = None
    return record


def _validate_batch_identity(output):
    if len({r['manager_key'] for r in output}) != 10 or len({r['gameweek'] for r in output}) != 1:
        raise ValueError('Ten distinct pseudonyms for one gameweek are required')
    if any(r['rank_at_capture'] > 10 for r in output):
        raise ValueError('Initial batch is limited to ranks 1-10')


def validate_named_batch(items, players, *, now=None):
    if not isinstance(items, list) or len(items) != 10:
        raise ValueError('Exactly ten manager squads are required')
    output = []
    for index, item in enumerate(items, 1):
        try:
            output.append(_validate_named_item(item, players, now=now))
        except (KeyError, TypeError, ValueError) as exc:
            raise ValueError(f'Manager {index}: {exc}') from exc
    _validate_batch_identity(output)
    return output


def preview_named_batch(items, players, *, now=None):
    """Return per-manager blockers; an unconfirmed Attack Card is not a hard failure."""
    if not isinstance(items, list) or len(items) != 10:
        raise ValueError('Exactly ten manager squads are required')
    results = []
    records = []
    for index, item in enumerate(items, 1):
        try:
            record = _validate_named_item(item, players, now=now)
            results.append({'manager': index, 'status': 'valid', 'record': record})
            records.append(record)
        except (KeyError, TypeError, ValueError) as exc:
            message = str(exc)
            if (isinstance(item, dict) and item.get('manager_card') == 'attack'
                    and item.get('attack_rules_unverified_confirmed') is not True
                    and 'Confirm the displayed squad manually' in message):
                try:
                    proposed = _validate_named_item({**item, 'attack_rules_unverified_confirmed': True}, players, now=now)
                    proposed['manual_confirmation'] = False
                    proposed['attack_rules_unverified_confirmed'] = False
                    results.append({'manager': index, 'status': 'needs_confirmation',
                                    'field': 'attack_rules_unverified_confirmed',
                                    'message': 'Confirm the displayed Attack Card squad in Manager ' + str(index),
                                    'record': proposed})
                    records.append(proposed)
                    continue
                except (KeyError, TypeError, ValueError) as confirm_exc:
                    message = str(confirm_exc)
            results.append({'manager': index, 'status': 'invalid', 'message': message})
    if len(records) == 10:
        try:
            _validate_batch_identity(records)
        except ValueError as exc:
            results.append({'manager': None, 'status': 'invalid', 'message': str(exc)})
    return {'managers': results, 'can_save': len(results) == 10 and all(r['status'] == 'valid' for r in results)}


def save_batch(records, path=DEFAULT_STORE):
    """Commit a confirmed ten-record batch atomically."""
    if len(records) != 10:
        raise ValueError('Exactly ten validated records required')
    path = Path(path)
    existing = read_records(path)
    keys = {(r['gameweek'], r['manager_key']) for r in existing}
    if any((r['gameweek'], r['manager_key']) in keys for r in records):
        raise ValueError('A pseudonym already has a record for this gameweek')
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.manager_batch_', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(existing + records, stream, ensure_ascii=False, indent=2)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return records


def _utc(value, field):
    if not isinstance(value, str):
        raise ValueError(f'{field} must be an ISO timestamp with timezone')
    try:
        parsed = datetime.fromisoformat(value.replace('Z', '+00:00'))
    except ValueError as exc:
        raise ValueError(f'{field} must be an ISO timestamp with timezone') from exc
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError(f'{field} must include a timezone')
    return parsed.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')


def validate(payload, players, *, now=None):
    """Reject incomplete records; never infer a missing player or field."""
    if not isinstance(payload, dict):
        raise ValueError('JSON object required')
    allowed = {'gameweek', 'manager_key', 'rank_at_capture', 'rank_basis_gameweek',
               'starting_xi_ids', 'bench_ids', 'captain_id', 'vice_captain_id',
               'formation', 'captured_at_utc', 'observation_kind', 'provenance_note',
               'deadline_at_utc', 'manager_card', 'attack_rules_unverified_confirmed'}
    extra = set(payload) - allowed
    if extra:
        raise ValueError('Unrecognized fields are not stored: ' + ', '.join(sorted(extra)))
    try:
        week = int(payload['gameweek'])
        rank = int(payload['rank_at_capture'])
        basis = int(payload['rank_basis_gameweek'])
        key = str(payload['manager_key'])
        uuid.UUID(key, version=4)
        if str(uuid.UUID(key)) != key:
            raise ValueError()
    except (KeyError, TypeError, ValueError, AttributeError) as exc:
        raise ValueError('Gameweek, rank, rank-basis week and UUIDv4 pseudonym are required') from exc
    if not 1 <= week <= 34 or rank < 1 or not 0 <= basis < week:
        raise ValueError('Invalid gameweek or rank; rank basis must predate the target week')
    xi = payload.get('starting_xi_ids')
    bench = payload.get('bench_ids')
    if not isinstance(xi, list) or not isinstance(bench, list) or len(xi) != 11 or len(bench) != 4:
        raise ValueError('starting_xi_ids/bench_ids: exactly 11 starters and four bench IDs are required')
    if any(type(pid) is not int for pid in xi + bench) or len(set(xi + bench)) != 15:
        raise ValueError('starting_xi_ids/bench_ids: player IDs must be distinct integers')
    unknown = set(xi + bench) - set(players)
    if unknown:
        raise ValueError('starting_xi_ids/bench_ids: Unknown official player IDs: ' + ', '.join(map(str, sorted(unknown))))
    captain, vice = payload.get('captain_id'), payload.get('vice_captain_id')
    if type(captain) is not int or type(vice) is not int or captain == vice or captain not in xi or vice not in xi:
        raise ValueError('captain_id/vice_captain_id: distinct captain and vice captain must start')
    counts = Counter(players[pid]['position'] for pid in xi)
    bench_counts = Counter(players[pid]['position'] for pid in xi + bench)
    card = payload.get('manager_card', 'unknown')
    if card not in ('none', 'unknown', 'triple_captain', 'quadruple_captain', 'bench_boost', 'attack', 'unlimited_budget'):
        raise ValueError('Unknown manager card')
    if type(payload.get('attack_rules_unverified_confirmed', False)) is not bool:
        raise ValueError('Attack Card manual confirmation must be a boolean')
    required = {'GK': 2, 'DEF': 5, 'MID': 5, 'FWD': 3}
    standard_squad = all(bench_counts[pos] == required[pos] for pos in required)
    if card != 'attack' and not standard_squad:
        differences = []
        excess_names = []
        for pos, expected in required.items():
            actual = bench_counts[pos]
            if actual != expected:
                differences.append(f'{pos} {actual}/{expected} ({"missing" if actual < expected else "excess"} {abs(actual-expected)})')
                if actual > expected:
                    excess_names.append(pos + ': ' + ', '.join(players[pid]['name'] for pid in xi + bench
                                                               if players[pid]['position'] == pos))
        raise ValueError('15-player position mismatch: ' + ', '.join(differences) +
                         '. Check the selected names and their official positions.' +
                         (' Excess-position entries: ' + '; '.join(excess_names) if excess_names else ''))
    formation = f"{counts['DEF']}-{counts['MID']}-{counts['FWD']}"
    standard = (counts['DEF'], counts['MID'], counts['FWD']) in valid_formations()
    if counts['GK'] != 1:
        raise ValueError(f'Starting XI must include exactly one GK; found {counts["GK"]}')
    rules_unverified = card == 'attack' and (not standard_squad or not standard)
    if card != 'attack' and not standard:
        detail = ', '.join(f'{pos}={counts[pos]}' for pos in ('GK', 'DEF', 'MID', 'FWD'))
        raise ValueError(f'Starting XI formation invalid for {card} card ({detail})')
    if rules_unverified and payload.get('attack_rules_unverified_confirmed') is not True:
        detail = ', '.join(f'{pos}={bench_counts[pos]}' for pos in ('GK', 'DEF', 'MID', 'FWD'))
        raise ValueError('Attack Card rules are undocumented for this composition (' + detail +
                         '). Confirm the displayed squad manually to store it as rules_unverified; it cannot enter training or leakage-safe evaluation.')
    if payload.get('formation') != formation:
        raise ValueError(f'Formation must match selected XI: {formation}')
    captured = _utc(payload.get('captured_at_utc'), 'captured_at_utc')
    deadline = _utc(payload.get('deadline_at_utc'), 'deadline_at_utc') if payload.get('deadline_at_utc') else None
    current = now or datetime.now(timezone.utc)
    if datetime.fromisoformat(captured.replace('Z', '+00:00')) > current:
        raise ValueError('Capture timestamp cannot be in the future')
    kind = payload.get('observation_kind')
    if kind not in ('pre_deadline_observed', 'retrospective_screenshot', 'timing_unverified'):
        raise ValueError('Observation kind must be explicit')
    if kind == 'pre_deadline_observed' and (not deadline or captured >= deadline):
        raise ValueError('Pre-deadline observation needs a verified later deadline')
    note = payload.get('provenance_note', '')
    if not isinstance(note, str) or len(note) > 300:
        raise ValueError('Provenance note must be at most 300 characters')
    if re.search(r'@|https?://|www\.|\b(?:profile|account|user)[-_/ ]?id\b', note, re.I):
        raise ValueError('Provenance note cannot contain account or contact identifiers')
    received = current.astimezone(timezone.utc).isoformat().replace('+00:00', 'Z')
    eligible = bool(not rules_unverified and kind == 'pre_deadline_observed' and deadline and captured < deadline and received < deadline)
    return {'gameweek': week, 'manager_key': key, 'rank_at_capture': rank,
            'rank_basis_gameweek': basis, 'starting_xi_ids': xi, 'bench_ids': bench,
            'captain_id': captain, 'vice_captain_id': vice, 'formation': formation,
            'captured_at_utc': captured, 'recorded_at_utc': received, 'deadline_at_utc': deadline,
            'observation_kind': kind, 'provenance_note': note, 'manager_card': card,
            'rules_status': 'rules_unverified' if rules_unverified else 'standard_rules_verified',
            'validation_status': 'rules_unverified' if rules_unverified else 'validated',
            'manual_confirmation': bool(rules_unverified and payload.get('attack_rules_unverified_confirmed')),
            'attack_rules_unverified_confirmed': bool(rules_unverified and payload.get('attack_rules_unverified_confirmed')),
            'position_counts': {pos: bench_counts[pos] for pos in ('GK', 'DEF', 'MID', 'FWD')},
            'feature_eligible': eligible}


def read_records(path=DEFAULT_STORE):
    path = Path(path)
    if not path.exists():
        return []
    data = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(data, list):
        raise ValueError('Experimental store must be a JSON list')
    return data


def save_record(record, path=DEFAULT_STORE):
    path = Path(path)
    rows = read_records(path)
    if any(r['gameweek'] == record['gameweek'] and r['manager_key'] == record['manager_key'] for r in rows):
        raise ValueError('This pseudonym already has a record for the gameweek')
    rows.append(record)
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temp = tempfile.mkstemp(dir=path.parent, prefix='.manager_squads_', suffix='.tmp')
    try:
        with os.fdopen(fd, 'w', encoding='utf-8') as stream:
            json.dump(rows, stream, ensure_ascii=False, indent=2)
        os.replace(temp, path)
    finally:
        if os.path.exists(temp):
            os.unlink(temp)
    return record


def export_csv(rows):
    out = io.StringIO()
    fields = ['gameweek', 'manager_key', 'rank_at_capture', 'rank_basis_gameweek',
              'starting_xi_ids', 'bench_ids', 'captain_id', 'vice_captain_id',
              'formation', 'captured_at_utc', 'recorded_at_utc', 'deadline_at_utc', 'observation_kind',
              'feature_eligible', 'manager_card', 'rules_status', 'position_counts',
              'attack_rules_unverified_confirmed', 'validation_status', 'manual_confirmation', 'provenance_note']
    writer = csv.DictWriter(out, fieldnames=fields)
    writer.writeheader()
    for row in safe_export_rows(rows):
        writer.writerow({k: json.dumps(row[k]) if isinstance(row.get(k), (list, dict)) else row.get(k) for k in fields})
    return out.getvalue()


def rules_unverified(row):
    # Older experimental Attack Card rows have no rules_status; treat them conservatively.
    return row.get('rules_status') == 'rules_unverified' or (row.get('manager_card') == 'attack' and row.get('rules_status') != 'standard_rules_verified')


def safe_export_rows(rows):
    exported = []
    for row in rows:
        item = dict(row)
        if rules_unverified(item):
            item['rules_status'] = 'rules_unverified'
            item['validation_status'] = 'rules_unverified'
            item['manual_confirmation'] = bool(item.get('manual_confirmation', item.get('attack_rules_unverified_confirmed', False)))
            item['feature_eligible'] = False
        exported.append(item)
    return exported


def dashboard(rows, players, *, week=None):
    selected = [r for r in rows if week is None or r['gameweek'] == week]
    output = {'count': len(selected), 'weeks': sorted({r['gameweek'] for r in rows}),
              'pre_deadline_count': sum(r.get('feature_eligible', False) and not rules_unverified(r) for r in selected),
              'retrospective_count': sum(not r.get('feature_eligible', False) or rules_unverified(r) for r in selected),
              'rules_unverified_count': sum(rules_unverified(r) for r in selected),
              'tiers': {}, 'weekly_comparisons': []}
    # Rank is used only at the capture time, never imputed backward.
    for tier in (10, 25, 50):
        group = [r for r in selected if r['rank_at_capture'] <= tier]
        picks = Counter(pid for r in group for pid in r['starting_xi_ids'])
        captains = Counter(r['captain_id'] for r in group)
        output['tiers'][str(tier)] = {
            'manager_weeks': len(group),
            'players': [{'id': pid, 'name': players[pid]['name'], 'count': n, 'share': round(n / len(group), 3)}
                        for pid, n in picks.most_common(30)] if group else [],
            'captains': [{'id': pid, 'name': players[pid]['name'], 'count': n, 'share': round(n / len(group), 3)}
                         for pid, n in captains.most_common(20)] if group else []}
    if PHASE36_FILE.exists() and HISTORY_FILE.exists():
        phase36 = json.loads(PHASE36_FILE.read_text(encoding='utf-8'))['historical_experiments']
        history = json.loads(HISTORY_FILE.read_text(encoding='utf-8'))['rows_by_player']
        for row in selected:
            if rules_unverified(row):
                continue
            gw = str(row['gameweek'])
            if gw not in phase36:
                continue
            model = phase36[gw]['variants']['baseline']
            actual = {int(pid): next((h.get('points') for h in hist if str(h.get('gameweekOrder')) == gw), None)
                      for pid, hist in history.items()}
            ids = row['starting_xi_ids']
            points = (sum(actual[pid] for pid in ids) + actual[row['captain_id']]
                      if all(actual.get(pid) is not None for pid in ids) else None)
            output['weekly_comparisons'].append({
                'gameweek': row['gameweek'], 'manager_key': row['manager_key'],
                'observation_kind': row['observation_kind'], 'feature_eligible': row.get('feature_eligible', False),
                'xi_overlap': len(set(ids) & set(model['xi_ids'])),
                'xi_plus_captain_actual': points,
                'optimizer_xi_plus_captain_actual': model.get('actual_squad_points'),
                'note': 'Retrospective XI+captain only; manager cards and automatic substitutions excluded.'})
    return output


def screenshot_hints(image_bytes, players):
    """Best-effort optional OCR. Returns only exact visible-name candidates, never a squad."""
    try:
        from PIL import Image
        import pytesseract
    except ImportError:
        return {'status': 'ocr_unavailable', 'candidates': []}
    try:
        image = Image.open(io.BytesIO(image_bytes))
        if image.width * image.height > 12_000_000:
            raise ValueError('Screenshot resolution too large')
        text = pytesseract.image_to_string(image, config='--psm 11')
    except Exception:
        return {'status': 'ocr_unavailable', 'candidates': []}
    lines = {_name_key(line) for line in text.splitlines()}
    candidates = []
    match_name_counts = Counter(_name_key(p.get('match_name', '')) for p in players.values())
    for p in players.values():
        name = _name_key(p['name'])
        short = _name_key(p.get('match_name', ''))
        if (name and name in lines) or (short and short in lines and match_name_counts[short] == 1):
            candidates.append({'id': p['id'], 'name': p['name'], 'position': p['position']})
    return {'status': 'suggestions_only', 'candidates': candidates, 'points_extracted': False,
            'warning': 'OCR is incomplete; verify every player and point manually before saving.'}
