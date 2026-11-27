# v3.4 – TFF resmi API fikstür ablation

Resmi endpoint: `/api/backend/projection/stats/fixtures?league-id=1`.

Bu ZIP'in içindeki `analysis/verified_fixtures_v34.py`, `tests/test_verified_fixtures_v34.py` ve `historical_data/tff_fixtures_verified_v5.json` dosyalarını mevcut projenizin aynı klasörlerine kopyalayın. Diğer dosyaları değiştirmeyin.

Proje ana klasöründen:

```powershell
python -m analysis.verified_fixtures_v34
```

Sonuçlar `historical_data/walkforward_backtest_v34.json` ve `.csv` olarak çıkar. Önceki v3.2 raporunun üzerine yazılmaz.

**Uyarı:** API 28 Ekim'de alınmıştır; GW5–9 son tarihlerindeki hali kanıtlanmış değildir. Eski oyuncu-kulüp üyeliği ve fiyatlar da tarihsel olarak doğrulanmış değildir. Bu nedenle sonuç yalnızca *retrospective exploratory* olarak yorumlanmalı, gerçek pre-deadline yatırım/tahmin performansı gibi sunulmamalıdır.
