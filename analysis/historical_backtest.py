"""Retrospective TFF round backtest. Run: python -m analysis.historical_backtest --round 9

Only player history entries strictly BEFORE target round are model inputs. This is
NOT a verified point-in-time simulation: historic availability, transfer pool and
past fixture difficulty are not fully reconstructed.
"""
import argparse
import json
import math
import time
from datetime import datetime, timezone
from pathlib import Path

from data_sources.tff_official import BASE, ENDPOINT, PROFILE, _browser, _extract, TFFFeedError

STORE = Path('historical_data')


def fetch_json(request, url):
    response = request.get(url, timeout=45000)
    if response.status in (401, 403):
        raise TFFFeedError('TFF oturumu geçersiz; python -m data_sources.tff_official login çalıştırın.')
    if not response.ok:
        raise TFFFeedError(f'TFF HTTP {response.status}: {url.split("?")[0]}')
    payload = response.json()
    if isinstance(payload, dict) and payload.get('status') is False:
        raise TFFFeedError('TFF API hata yanıtı verdi')
    return payload.get('data', payload) if isinstance(payload, dict) else payload


def collect(force=False, pause=0.12):
    STORE.mkdir(exist_ok=True)
    if not PROFILE.exists():
        raise TFFFeedError('Önce python -m data_sources.tff_official login çalıştırın.')
    with _browser() as pw:
        context = pw.chromium.launch_persistent_context(str(PROFILE), headless=True)
        try:
            raw = fetch_json(context.request, BASE + ENDPOINT)
            players = _extract(raw)
            (STORE / 'players.json').write_text(json.dumps(players, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f'{len(players)} oyuncu bulundu. Haftalık geçmişler indiriliyor...')
            ok = 0
            errors = []
            for idx, player in enumerate(players, 1):
                pid = str(player['id'])
                target = STORE / f'player_{pid}.json'
                if target.exists() and not force:
                    ok += 1
                    continue
                url = f'{BASE}/api/backend/projection/stats/players/{pid}/history?league-id=1'
                try:
                    data = fetch_json(context.request, url)
                    if not isinstance(data, list):
                        raise ValueError('history data list değil')
                    target.write_text(json.dumps(data, ensure_ascii=False), encoding='utf-8')
                    ok += 1
                except Exception as exc:
                    errors.append({'player_id': pid, 'error': str(exc)[:160]})
                if idx % 50 == 0:
                    print(f'{idx}/{len(players)} işlendi, {ok} geçmiş kaydı hazır, {len(errors)} hata')
                time.sleep(pause)
            (STORE / 'download_report.json').write_text(json.dumps({
                'collected_utc': datetime.now(timezone.utc).isoformat(),
                'players': len(players), 'history_files': ok, 'errors': errors,
            }, ensure_ascii=False, indent=2), encoding='utf-8')
            print(f'Tamamlandı: {ok}/{len(players)}. Hatalar: {len(errors)}')
        finally:
            context.close()


def number(value, default=None):
    try:
        v = float(value)
        return v if math.isfinite(v) else default
    except (TypeError, ValueError):
        return default


def build_pool(round_number):
    players_file = STORE / 'players.json'
    if not players_file.exists():
        raise ValueError('Önce --collect çalıştırın.')
    players = json.loads(players_file.read_text(encoding='utf-8'))
    pool, actual, coverage = [], {}, {'players': len(players), 'history_files': 0, 'with_pre_round': 0, 'with_target_round': 0, 'missing_historical_price': 0}
    for p in players:
        file = STORE / f"player_{p['id']}.json"
        if not file.exists():
            continue
        coverage['history_files'] += 1
        rows = json.loads(file.read_text(encoding='utf-8'))
        if not isinstance(rows, list):
            continue
        past = sorted((r for r in rows if isinstance(r, dict) and int(r.get('gameweekOrder') or -1) < round_number), key=lambda r: int(r.get('gameweekOrder') or -1))
        target = next((r for r in rows if isinstance(r, dict) and int(r.get('gameweekOrder') or -1) == round_number), None)
        if target is None:
            continue
        coverage['with_target_round'] += 1
        actual[str(p['id'])] = number(target.get('points'))
        if not past:
            continue
        coverage['with_pre_round'] += 1
        # Historical cost: use final known price from before the target round.
        price = next((number(r.get('cost')) for r in reversed(past) if number(r.get('cost')) is not None), None)
        if price is None:
            coverage['missing_historical_price'] += 1
            continue
        recent = past[-5:]
        pts = [number(r.get('points'), 0) for r in recent]
        mins = [number(r.get('minutesPlayed'), 0) for r in recent]
        season_pts = [number(r.get('points'), 0) for r in past]
        season_minutes = [number(r.get('minutesPlayed'), 0) for r in past]
        # Bayesian shrinkage of recent form toward positional prior, plus minutes reliability.
        priors = {'GK': 3.1, 'DEF': 3.2, 'MID': 3.5, 'FWD': 3.6}
        prior = priors.get(p['position'], 3.0)
        weights = list(range(1, len(pts) + 1))
        form = sum(v * w for v, w in zip(pts, weights)) / sum(weights)
        season = sum(season_pts) / len(season_pts)
        shrink = len(past) / (len(past) + 4)
        expected_minutes = sum(mins) / len(mins)
        availability_factor = min(1, max(0.1, expected_minutes / 85))
        xpts = max(0.1, (0.55 * (shrink * form + (1-shrink) * prior) + 0.45 * season) * availability_factor)
        pool.append({
            'id': p['id'], 'name': p['name'], 'team': p['team'], 'position': p['position'],
            'price': price, 'xpts': round(xpts, 3), 'expected_minutes': round(expected_minutes, 1),
            'previous_round_points': number(past[-1].get('points'), 0),
            'actual_points': actual[str(p['id'])],
        })
    return pool, actual, coverage


def evaluate(round_number):
    pool, actual, coverage = build_pool(round_number)
    if len(pool) < 15:
        raise ValueError(f'Yeterli geçmiş verisi yok: {len(pool)} oyuncu. --collect çalıştırın.')
    from analysis.optimizer import optimize
    solution = optimize(pool)
    if 'error' in solution:
        raise ValueError(solution['error'])
    xi = solution['starting_xi']
    captain_id = str(solution['captain']['id'])
    missing = [p['id'] for p in xi if actual.get(str(p['id'])) is None]
    realized = None if missing else round(sum(actual[str(p['id'])] * (2 if str(p['id']) == captain_id else 1) for p in xi), 2)
    rows = [{k: p[k] for k in ('id', 'name', 'team', 'position', 'price', 'xpts', 'previous_round_points', 'actual_points')} | {'captain': str(p['id']) == captain_id} for p in xi]
    report = {
        'round': round_number, 'created_utc': datetime.now(timezone.utc).isoformat(),
        'classification': 'RETROSPECTIVE / NOT POINT-IN-TIME VERIFIED',
        'limitations': [
            '9. hafta sonrası oyuncu havuzunda kalan isimler kullanılıyor; geçmişteki tam transfer/oyuncu havuzu doğrulanmadı.',
            'Tarihsel cezalı/sakat durumları yeniden kurulamadı; uygunluk filtresi eksik.',
            'Geçmiş fiyat için hedef haftadan önceki son kaydedilen fiyat kullanıldı; son transfer deadline fiyatı doğrulanmadı.',
            'FDR, geçmiş bahis oranları ve geçmiş xgEdge tahminleri dahil değil; bu, mevcut canlı optimizer modelinin birebir backtesti değil.',
            'Otomatik yedek değişikliği, menajer kartları ve transfer cezaları uygulanmadı.',
        ],
        'coverage': coverage, 'eligible_players': len(pool),
        'formation': solution['formation'], 'captain': solution['captain']['name'],
        'budget_used': solution['squad_cost'], 'predicted_points': solution['expected_points'],
        'actual_points': realized, 'difference_actual_minus_predicted': None if realized is None else round(realized - solution['expected_points'], 2),
        'missing_actual_ids': missing, 'starting_xi': rows,
        'bench': [{k: p[k] for k in ('id', 'name', 'position', 'price', 'xpts', 'actual_points')} for p in solution['squad'] if p['id'] not in {x['id'] for x in xi}],
        'formation_comparison': solution['formation_comparison'],
    }
    STORE.mkdir(exist_ok=True)
    dest = STORE / f'backtest_gw{round_number}.json'
    dest.write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"\n{round_number}. hafta | {report['classification']}")
    print(f"Veri: {len(pool)} oyuncu, {coverage['history_files']} geçmiş dosyası")
    print(f"Formasyon: {solution['formation']} | Kaptan: {report['captain']} | Bütçe: {report['budget_used']}")
    print(f"Tahmin: {report['predicted_points']} | Gerçek: {realized if realized is not None else 'eksik'}")
    for row in rows:
        print(f"{'(K)' if row['captain'] else '   '} {row['name'][:28]:28} {row['position']:3} tahmin={row['xpts']:5.2f} gerçek={row['actual_points']}")
    print(f'Rapor: {dest}')
    return report


def main():
    parser = argparse.ArgumentParser(description='TFF historical retrospective backtest')
    parser.add_argument('--round', type=int, default=9)
    parser.add_argument('--collect', action='store_true', help='Tüm oyuncuların haftalık geçmişini indir')
    parser.add_argument('--force', action='store_true', help='Önbelleği yenile')
    args = parser.parse_args()
    if args.round < 2 or args.round > 34:
        parser.error('Hafta 2–34 arasında olmalı')
    if args.collect:
        collect(force=args.force)
    evaluate(args.round)


if __name__ == '__main__':
    main()
