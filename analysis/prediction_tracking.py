"""Append-only local prediction evidence. Timestamps are assigned by this process."""
import json
import sqlite3
import uuid
from datetime import datetime, timezone
from pathlib import Path

DEFAULT_DB = Path('historical_data/prediction_tracking.sqlite3')
OFFICIAL_DEADLINE_URL = 'https://tfffantezilig.com/api/backend/projection/stats/fixtures?league-id=1'


def utc_now():
    return datetime.now(timezone.utc).isoformat()


def parse_time(value):
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(str(value).replace('Z', '+00:00'))
    except ValueError:
        return None
    return parsed.astimezone(timezone.utc) if parsed.tzinfo else None


def connect(path=DEFAULT_DB):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    db = sqlite3.connect(path)
    db.execute('PRAGMA foreign_keys=ON')
    db.executescript('''
    CREATE TABLE IF NOT EXISTS snapshots (
      id TEXT PRIMARY KEY, gameweek INTEGER NOT NULL, captured_at TEXT NOT NULL,
      deadline_at TEXT, deadline_source TEXT, source TEXT NOT NULL,
      classification TEXT NOT NULL, payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS predictions (
      id TEXT PRIMARY KEY, snapshot_id TEXT NOT NULL REFERENCES snapshots(id),
      gameweek INTEGER NOT NULL, created_at TEXT NOT NULL, status TEXT NOT NULL,
      model TEXT NOT NULL, model_version TEXT NOT NULL, risk_strategy TEXT NOT NULL,
      raw_expected_points REAL NOT NULL, risk_adjusted_objective REAL,
      payload TEXT NOT NULL);
    CREATE TABLE IF NOT EXISTS evaluation_runs (
      id TEXT PRIMARY KEY, snapshot_id TEXT NOT NULL REFERENCES snapshots(id),
      gameweek INTEGER NOT NULL, created_at TEXT NOT NULL,
      source_digest TEXT NOT NULL, status TEXT NOT NULL,
      source TEXT NOT NULL, payload TEXT NOT NULL,
      UNIQUE(snapshot_id, source_digest));
    CREATE TRIGGER IF NOT EXISTS snapshots_no_update BEFORE UPDATE ON snapshots BEGIN SELECT RAISE(ABORT, 'immutable snapshot'); END;
    CREATE TRIGGER IF NOT EXISTS snapshots_no_delete BEFORE DELETE ON snapshots BEGIN SELECT RAISE(ABORT, 'immutable snapshot'); END;
    CREATE TRIGGER IF NOT EXISTS predictions_no_update BEFORE UPDATE ON predictions BEGIN SELECT RAISE(ABORT, 'immutable prediction'); END;
    CREATE TRIGGER IF NOT EXISTS predictions_no_delete BEFORE DELETE ON predictions BEGIN SELECT RAISE(ABORT, 'immutable prediction'); END;
    CREATE TRIGGER IF NOT EXISTS evaluation_runs_no_update BEFORE UPDATE ON evaluation_runs BEGIN SELECT RAISE(ABORT, 'immutable evaluation'); END;
    CREATE TRIGGER IF NOT EXISTS evaluation_runs_no_delete BEFORE DELETE ON evaluation_runs BEGIN SELECT RAISE(ABORT, 'immutable evaluation'); END;
    ''')
    return db


def verification(captured_at, deadline_at, deadline_source=None, classification=None):
    if classification == 'historical_reconstruction':
        return 'historical_reconstruction_not_verified'
    captured, deadline = parse_time(captured_at), parse_time(deadline_at)
    if not captured:
        raise ValueError('Capture timestamp must include a timezone')
    if deadline and captured >= deadline:
        return 'post_deadline'
    if not deadline or deadline_source != OFFICIAL_DEADLINE_URL:
        return 'deadline_unknown'
    # An official deadline plus a local clock is not independent timestamp proof.
    return 'locally_recorded_pre_deadline_not_verified'


def save_snapshot(gameweek, players, fixtures, histories, source, *, deadline_at=None,
                  deadline_source=None, classification='live', data_quality=None, path=DEFAULT_DB):
    if not isinstance(gameweek, int) or gameweek < 1 or not isinstance(players, list) or not players:
        raise ValueError('Gameweek and player data required')
    if not isinstance(fixtures, list) or not isinstance(histories, list):
        raise ValueError('Fixtures and historical statistics must be lists')
    captured_at = utc_now()
    snapshot_id = str(uuid.uuid4())
    payload = {'gameweek': gameweek, 'players': players, 'fixtures': fixtures,
               'histories': histories, 'source': source, 'retrieved_at': captured_at,
               'deadline_at': deadline_at, 'deadline_source': deadline_source,
               'data_quality': data_quality}
    status = verification(captured_at, deadline_at, deadline_source, classification)
    with connect(path) as db:
        db.execute('INSERT INTO snapshots VALUES (?,?,?,?,?,?,?,?)',
                   (snapshot_id, gameweek, captured_at, deadline_at, deadline_source,
                    json.dumps(source, ensure_ascii=False), classification,
                    json.dumps(payload, ensure_ascii=False)))
    return {'id': snapshot_id, 'captured_at': captured_at, 'status': status}


def get_snapshot(snapshot_id, path=DEFAULT_DB):
    with connect(path) as db:
        row = db.execute('SELECT gameweek,captured_at,deadline_at,deadline_source,source,classification,payload FROM snapshots WHERE id=?',
                         (snapshot_id,)).fetchone()
    if row is None:
        return None
    keys = ('gameweek','captured_at','deadline_at','deadline_source','source','classification','payload')
    item = dict(zip(keys,row))
    item['id'] = snapshot_id
    item['source'] = json.loads(item['source'])
    item['payload'] = json.loads(item['payload'])
    return item


def save_prediction(snapshot_id, result, *, model_version='1', path=DEFAULT_DB):
    created_at = utc_now()
    with connect(path) as db:
        row = db.execute('SELECT gameweek,captured_at,deadline_at,deadline_source,classification FROM snapshots WHERE id=?',
                         (snapshot_id,)).fetchone()
        if row is None:
            raise ValueError('Unknown snapshot')
        gameweek, captured, deadline, deadline_source, classification = row
        status = verification(created_at, deadline, deadline_source, classification)
        if status != 'post_deadline' and verification(captured, deadline, deadline_source, classification) != 'verified_pre_deadline':
            status = verification(captured, deadline, deadline_source, classification)
        xi = result.get('starting_xi', [])
        if len(xi) != 11 or sum(bool(p.get('captain')) for p in xi) != 1 or len(result.get('bench', [])) != 4:
            raise ValueError('A complete XI, captain and bench are required')
        raw_expected = sum(float(p['xpts']) * (2 if p.get('captain') else 1) for p in xi)
        prediction_id = str(uuid.uuid4())
        db.execute('INSERT INTO predictions VALUES (?,?,?,?,?,?,?,?,?,?,?)',
                   (prediction_id, snapshot_id, gameweek, created_at, status,
                    result['model'], model_version, result['risk_profile'],
                    raw_expected, result.get('risk_adjusted_objective'),
                    json.dumps(result, ensure_ascii=False)))
    return {'id': prediction_id, 'snapshot_id': snapshot_id, 'created_at': created_at, 'status': status}


def get_prediction(prediction_id, path=DEFAULT_DB):
    with connect(path) as db:
        row = db.execute('SELECT snapshot_id,gameweek,created_at,status,model,model_version,risk_strategy,raw_expected_points,risk_adjusted_objective,payload FROM predictions WHERE id=?',
                         (prediction_id,)).fetchone()
    if row is None:
        return None
    keys = ('snapshot_id','gameweek','created_at','status','model','model_version','risk_strategy','raw_expected_points','risk_adjusted_objective','payload')
    item = dict(zip(keys, row))
    item['id'] = prediction_id
    item['payload'] = json.loads(item['payload'])
    return item


def save_evaluation_run(snapshot_id, gameweek, source_digest, status, source, payload, path=DEFAULT_DB):
    """Append once for identical official evidence; never update earlier evaluations."""
    if not isinstance(source_digest,str) or len(source_digest)!=64:
        raise ValueError('A SHA-256 source digest is required')
    with connect(path) as db:
        row=db.execute('SELECT gameweek FROM snapshots WHERE id=?',(snapshot_id,)).fetchone()
        if row is None or row[0]!=gameweek:
            raise ValueError('Evaluation snapshot/gameweek mismatch')
        run_id=str(uuid.uuid4())
        db.execute('INSERT OR IGNORE INTO evaluation_runs VALUES (?,?,?,?,?,?,?,?)',
                   (run_id,snapshot_id,gameweek,utc_now(),source_digest,status,
                    json.dumps(source,ensure_ascii=False),json.dumps(payload,ensure_ascii=False)))
        existing=db.execute('SELECT id FROM evaluation_runs WHERE snapshot_id=? AND source_digest=?',
                            (snapshot_id,source_digest)).fetchone()
    return get_evaluation_run(existing[0],path)


def get_evaluation_run(run_id, path=DEFAULT_DB):
    with connect(path) as db:
        row=db.execute('SELECT snapshot_id,gameweek,created_at,source_digest,status,source,payload FROM evaluation_runs WHERE id=?',
                       (run_id,)).fetchone()
    if row is None:
        return None
    item=dict(zip(('snapshot_id','gameweek','created_at','source_digest','status','source','payload'),row))
    item['id']=run_id
    item['source']=json.loads(item['source'])
    item['payload']=json.loads(item['payload'])
    return item


def latest_evaluation_run(snapshot_id, path=DEFAULT_DB):
    with connect(path) as db:
        row=db.execute('SELECT id FROM evaluation_runs WHERE snapshot_id=? ORDER BY created_at DESC,id DESC LIMIT 1',
                       (snapshot_id,)).fetchone()
    return get_evaluation_run(row[0],path) if row else None


def evaluate_prediction(prediction_id, actual_points, path=DEFAULT_DB):
    item = get_prediction(prediction_id, path)
    if item is None:
        raise ValueError('Unknown prediction')
    if not isinstance(actual_points, dict):
        raise ValueError('Actual points must be keyed by player ID')
    prediction = item['payload']
    xi = prediction['starting_xi']
    captain = next((p for p in xi if p.get('captain')), None)
    if len(xi) != 11 or captain is None:
        raise ValueError('Saved lineup is incomplete')
    missing = [p['id'] for p in xi if str(p['id']) not in actual_points]
    if missing:
        return {'status': 'incomplete', 'missing_player_ids': missing,
                'verification_status': item['status']}
    realized = sum(float(actual_points[str(p['id'])]) * (2 if p['id'] == captain['id'] else 1) for p in xi)
    return {'status': 'complete', 'prediction_id': prediction_id,
            'verification_status': item['status'], 'raw_expected_points': item['raw_expected_points'],
            'risk_adjusted_objective': item['risk_adjusted_objective'],
            'actual_points': round(realized, 2),
            'error_actual_minus_expected': round(realized - item['raw_expected_points'], 2)}
