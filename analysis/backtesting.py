"""Evaluate an immutable pre-round squad snapshot against that round's fantasy points.

Never use a post-round snapshot as evidence of predictive accuracy.
"""
from datetime import datetime, timezone
from math import isfinite


def evaluate_snapshot(snapshot, actual_players, round_number):
    if not isinstance(snapshot, dict) or not isinstance(actual_players, list):
        raise ValueError('Geçersiz tahmin kaydı veya sonuç listesi')
    if int(snapshot.get('round', -1)) != int(round_number):
        raise ValueError('Tahmin haftası ile sonuç haftası farklı')
    if not snapshot.get('pre_round_confirmed'):
        raise ValueError('Tahminin maçlardan önce kaydedildiği doğrulanmadı')
    xi = snapshot.get('starting_xi')
    captain = snapshot.get('captain_id')
    if not isinstance(xi, list) or len(xi) != 11 or len(set(map(str, xi))) != 11:
        raise ValueError('İlk 11 kaydı eksik veya tekrarlı')
    if str(captain) not in set(map(str, xi)):
        raise ValueError('Kaptan ilk 11 içinde değil')
    predictions = snapshot.get('predictions', {})
    if not isinstance(predictions, dict):
        raise ValueError('Tahmin puanları eksik')
    actual = {str(p['id']): p.get('round_points') for p in actual_players if isinstance(p, dict) and p.get('id') is not None}
    missing = [str(i) for i in xi if actual.get(str(i)) is None]
    if missing:
        return {'status':'incomplete', 'missing_player_ids':missing, 'warning':'Bazı oyuncuların gerçekleşen puanı yok. Yanlış sonuç üretmemek için karşılaştırma yapılmadı.'}
    expected = 0.0
    realized = 0.0
    rows=[]
    for player_id in xi:
        key=str(player_id)
        if key not in predictions: raise ValueError(f'Tahmin eksik: {key}')
        pred=float(predictions[key]); pts=float(actual[key])
        if not (isfinite(pred) and isfinite(pts)): raise ValueError('Geçersiz sayısal puan')
        multiplier=2 if key==str(captain) else 1
        expected+=pred*multiplier
        realized+=pts*multiplier
        rows.append({'id':key,'predicted':round(pred*multiplier,2),'actual':round(pts*multiplier,2),'error':round((pred-pts)*multiplier,2),'captain':multiplier==2})
    return {'status':'complete','round':int(round_number),'predicted_total':round(expected,2),'actual_total':round(realized,2),'difference':round(realized-expected,2),'mae_xi':round(sum(abs(r['error']) for r in rows)/11,2),'players':rows,
            'warning':'Bu değerlendirme yalnızca kaydedilmiş ilk 11 ve kaptan çarpanını içerir; otomatik yedek, chip ve özel oyun kuralları dahil değildir.'}
