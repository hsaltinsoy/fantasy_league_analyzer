"""Auditable TFF to xgEdge identity resolution; no guessed statistics."""
import hashlib
import json
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from data_sources.team_names import normalize_team

DEFAULT_CROSSWALK = Path('historical_data/player_identity_crosswalk.json')


def normalize(value):
    text = str(value or '').casefold().replace('ı', 'i')
    text = unicodedata.normalize('NFKD', text)
    return re.sub(r'[^a-z0-9]', '', ''.join(c for c in text if not unicodedata.combining(c)))


def load_crosswalk(path=DEFAULT_CROSSWALK):
    path = Path(path)
    if not path.exists():
        return {'version': 1, 'entries': []}
    obj = json.loads(path.read_text(encoding='utf-8'))
    if not isinstance(obj, dict) or not isinstance(obj.get('entries'), list):
        raise ValueError('Invalid identity crosswalk')
    return obj


def crosswalk_version(crosswalk):
    content = json.dumps(crosswalk, sort_keys=True, ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(content).hexdigest()


def add_verified_identity(tff_id, profile_url, evidence, *, aliases=(), path=DEFAULT_CROSSWALK):
    """Record a manually reviewed stable-ID link with revision history."""
    if not str(tff_id).isdigit() or not str(profile_url).startswith('https://www.xg-edge.com/players/') or not evidence:
        raise ValueError('TFF ID, xgEdge profile URL and evidence are required')
    path = Path(path)
    crosswalk = load_crosswalk(path)
    existing = [e for e in crosswalk['entries'] if str(e.get('tff_id')) == str(tff_id)]
    if existing and existing[-1].get('profile_url') == profile_url:
        raise ValueError('Identity link already exists')
    if any(e.get('profile_url') == profile_url and str(e.get('tff_id')) != str(tff_id)
           for e in crosswalk['entries']):
        raise ValueError('Profile URL is linked to another TFF player')
    entry = {'tff_id': int(tff_id), 'profile_url': profile_url, 'aliases': list(aliases),
             'verified': True, 'evidence': evidence,
             'recorded_at': datetime.now(timezone.utc).isoformat()}
    crosswalk['entries'].append(entry)
    crosswalk['version'] = int(crosswalk.get('version', 0)) + 1
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(crosswalk, ensure_ascii=False, indent=2), encoding='utf-8')
    return crosswalk_version(crosswalk)


def resolve_players(tff_players, external_players, crosswalk=None):
    crosswalk = crosswalk or {'version': 1, 'entries': []}
    entries = {str(e['tff_id']): e for e in crosswalk['entries'] if e.get('tff_id') is not None}
    by_url = {}
    by_name = {}
    for external in external_players:
        url = external.get('profile_url')
        if url:
            by_url.setdefault(url, []).append(external)
        by_name.setdefault(normalize(external.get('name')), []).append(external)
    used = set()
    resolved = []
    counts = {'verified': 0, 'high_confidence': 0, 'ambiguous': 0, 'unmatched': 0}
    for player in tff_players:
        key = str(player['id'])
        entry = entries.get(key)
        candidate = []
        level = 'unmatched'
        if entry and entry.get('profile_url'):
            candidate = by_url.get(entry['profile_url'], [])
            if len(candidate) == 1 and entry.get('verified'):
                level = 'verified'
        if not candidate:
            aliases = [player.get('name'), player.get('match_name')]
            if entry:
                aliases += entry.get('aliases', [])
            candidate = list({id(x): x for name in aliases for x in by_name.get(normalize(name), [])}.values())
        if len(candidate) > 1:
            club_name = normalize_team(player.get('club_name'))
            if club_name:
                candidate = [x for x in candidate if normalize_team(x.get('team')) == club_name]
        if len(candidate) == 1:
            external = candidate[0]
            # A name-only match must agree on club; persistent provider IDs survive transfers.
            stable = bool(entry and entry.get('profile_url') == external.get('profile_url'))
            club_name = normalize_team(player.get('club_name'))
            if not stable and (not club_name or normalize_team(external.get('team')) != club_name):
                level = 'ambiguous'
            elif id(external) in used:
                level = 'ambiguous'
            else:
                level = 'verified' if stable and entry.get('verified') else 'high_confidence'
                used.add(id(external))
        elif candidate:
            level = 'ambiguous'
        counts[level] += 1
        row = dict(player)
        row['identity_confidence'] = level
        row['external_statistics'] = candidate[0] if level in ('verified', 'high_confidence') else None
        row['missing_external_statistics'] = row['external_statistics'] is None or any(
            row['external_statistics'].get(k) is None for k in ('xg', 'xa'))
        resolved.append(row)
    report = {'total_tff_players': len(tff_players), 'matched_players': counts['verified'] + counts['high_confidence'],
              'ambiguous_matches': counts['ambiguous'], 'unmatched_players': counts['unmatched'],
              'missing_statistics': sum(p['missing_external_statistics'] for p in resolved),
              'confidence': counts, 'crosswalk_version': crosswalk_version(crosswalk)}
    return resolved, report


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser(description='Record a reviewed TFF/xgEdge identity link')
    parser.add_argument('tff_id', type=int)
    parser.add_argument('profile_url')
    parser.add_argument('--evidence', required=True, help='Review source or note')
    parser.add_argument('--alias', action='append', default=[])
    args = parser.parse_args()
    print(add_verified_identity(args.tff_id, args.profile_url, args.evidence, aliases=args.alias))
