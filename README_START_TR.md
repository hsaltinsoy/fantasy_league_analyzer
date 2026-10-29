# TFF Fantasy — temiz, çalıştırılabilir proje

## Windows PowerShell

```powershell
cd C:\Users\Said\Documents\GitHub\fantasy_league_analyzer
py -m pip install -r requirements.txt
py -m playwright install chromium
py -m data_sources.tff_official login
py -m analysis.predict_next_week --week 10 --live
```

Daha sonra `RUN_GW10.bat` dosyasına çift tıklayabilirsin.

Çevrimdışı (kayıtlı, güncelliği belirsiz oyuncu fiyatlarıyla):

```powershell
py -m analysis.predict_next_week --week 10
```

Kadro terminalde 11 + 4 oyuncu, kaptan, diziliş ve beklenen puanla gösterilir.
JSON dosyası: `historical_data/next_week_gw10.json`.

**Önemli:** Canlı mod yalnızca oyuncu fiyatı, kulüp ve uygunluk bilgisini günceller. Fikstür dosyası ve oyuncu geçmişi arşivden okunur. Bu sürüm mevcut gerçek takımını, transfer sınırlarını, transfer cezasını ve kartları hesaba katmaz. Varsayılan Haftanın Takımı ağırlığı, küçük backtestte avantaj sağlamadığı için 0'dır; `--tow-weight 0.05` ile deneyebilirsin.

Temizlikte `.git`, `.venv`, IDE ayarları, önbellekler, iç içe kopya projeler ve eski raporlar çıkarılmıştır. Geçmiş oyuncu JSON'ları, fikstür, Haftanın Takımı ve çalışan modüller korunmuştur.
