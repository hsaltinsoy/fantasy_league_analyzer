# v3.6: TFF Haftanın Takımı + walk-forward ablation

ZIP içindeki `data_sources/`, `analysis/`, `tests/` dosyalarını mevcut projenin aynı klasörlerine kopyalayın. v3.5 dosyalarını silmeyin.

## 1. Haftanın takımlarını çekin

```powershell
python -m data_sources.team_of_week --weeks 1 2 3 4 5 6 7 8 9
```

API: `/api/backend/projection/stats/dream-team?leagueId=1&type=week&gameweekId={week}`

Dosya: `historical_data/team_of_week_verified.json`. Bazı haftalar bulunamazsa `errors` alanında görünür; eksik haftalar negatif örnek sayılmaz. Gerekirse `python -m data_sources.tff_official login` çalıştırın.

## 2. Walk-forward ablation

```powershell
python -m analysis.verified_fixtures_v36
```

Varsayılan 4 model x 2 fikstür x 2 kaptan x 2 dakika x 3 TOW = **96 aday x 5 hafta**. Bu çok uzun sürebilir. Daha hızlı ilk test:

```powershell
python -m analysis.verified_fixtures_v36 --captain-risks 0.2 --minutes-risks 0.15 --tow-weights 0 0.05 0.10
```

Çıktılar: `historical_data/walkforward_backtest_v36.json` ve `.csv`.

**Önemli:** TOW verisi yalnızca tahmin haftasından ÖNCEKİ haftalardan kullanılır. Fikstürler, oyuncu kulüpleri ve fiyatlar için v3.5'in retrospektif veri sınırlamaları devam eder. TOW 0 ağırlığı kontrol grubudur. 5. hafta warmup; GW6–9 test.
