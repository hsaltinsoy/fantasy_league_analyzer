# v3.3 — Fikstür ablasyonu ve ID doğrulama kapısı

Bu sürüm v3.2 üzerine eklenen `analysis/audit_v33.py` modülünü içerir. Kullanıcının gerçek v3.2 sonuç dosyası `historical_data/walkforward_backtest_v32.json` ve raporu `historical_data/v33_audit/` içindedir.

## Çalıştırma

```bash
python -m analysis.audit_v33 --report historical_data/walkforward_backtest_v32.json --out historical_data/v33_audit
python -m unittest tests.test_audit_v33 -v
```

## Yorumlama

`paired_ablation.csv` aynı tahmin modelinin fikstür ağırlığı 0 ve 0.5 sürümlerini karşılaştırır. Model seçimi farkından bağımsız olarak fikstür etkisini incelemek için kullanılır. Ancak rakip ID'leri doğrulanmadığından bu bir keşif analizidir; gerçek maç öncesi kanıt değildir.

## Resmî ID doğrulaması

`--candidate-mapping historical_data/club_id_mapping_candidates.json --official-mapping PATH` parametreleri ile bağımsız olarak alınmış resmî Fantasy API JSON'u karşılaştırılır. Resmî dosya şu alanları içermelidir:

```json
{"source_type":"OFFICIAL_FANTASY_API","source_url":"https://gercek-kaynak-adresi", "captured_utc":"2026-10-28T12:00:00Z", "clubs":[{"club_id":1,"team_name":"Takım adı"}]}
```

`clubs` listesi 18 takımın tamamını içermelidir. Örnek URL/isimleri gerçek kanıt yerine kullanmayın. Doğrulama gerçek API isteğini otomatik olarak yapmaz; alınmış yanıtı karşılaştırır. Bu sürümde **bağımsız API doğrulaması tamamlanmamıştır**.

## Sonraki aşama

Resmî eşleştirme ve tarihsel maç öncesi oyuncu/kadro verileri edinildikten sonra takım formu, rakip zorluğu ve ilk 11 olasılığı için ayrı özellik ablasyonları eklenebilir. Şu an bu yeni tahmin özelliklerinin eklendiği iddia edilmemektedir.
