# TFF Fantasy Optimizer v0.6

## Çalıştırma

```bash
pip install -r requirements.txt
python run.py
```

Tarayıcı: http://127.0.0.1:5000

**Fikstür ve takım formunu güncelle** butonu `GET /api/free/refresh` çağırır. API key gerekmez. `open-matchday` projesinin 2026/27 Süper Lig maç ve fikstür CSV dosyalarını otomatik indirir, geçmiş sonuçlardan FDR hesaplar. `open-matchday` verileri kişisel/ticari olmayan kullanım ve atıf koşuluyla paylaşılır: https://github.com/oladeeayo/open-matchday

Bir maç haftasının yalnızca 1-4 maçı kalmışsa sıradaki tam haftayı seçer. Sezon bilgisi yerel tarihten türetilir. Kaynak bağlantısı başarısız olursa açıklayıcı hata döner. FDR yalnızca son beş maçlık forma dayalı sezgisel bir puandır; henüz kalibre edilmemiştir.

**Önemli:** Otomatik oyuncu istatistikleri, xG/xA ve TFF Fantasy fiyatları henüz entegre değildir. Bu nedenle gerçek oyuncularla optimum kadro otomatik oluşturulamaz. Mevcut oyuncu CSV tahmin ve `/api/optimize` uç noktaları korunmuştur. Eski API-FOOTBALL bağlantısı kodda geriye dönük uyumluluk için durur ancak yeni ekranda kullanılmaz.

## Testler

```bash
python -m pytest -q
```

## v0.7 — ücretsiz oyuncu kaynağı (deneysel)

`GET /api/players/free` SportScore'un belgelenmiş `/api/widget/topscorers/` endpoint'ini gol ve asist için çağırır. API anahtarı gerekmez. `competition=super-lig` slug'ının gerçek kapsamı kullanıcının bağlantısında doğrulanmalıdır. Dönen veri yalnızca liderlik listeleridir; tüm Süper Lig oyuncularını, son beş maç performansını, xG/xA, fantasy pozisyonu veya fiyatını içerdiği varsayılmaz. Bilinmeyen alanlar `null` kalır. Oyuncu fiyatları olmadan optimum 15 kişilik kadro otomatik oluşturulmaz.

SportScore kullanımında kaynak bağlantısı gösterilmelidir: https://sportscore.com/ (attribution şartlarını kontrol edin). v0.6 fikstür ve CSV seçenekleri korunmuştur.

## v0.8 player data
SportScore 404 integration removed. `POST /api/players/import` accepts `stats` CSV (`Player,Club,Min,G,A,xG,xA`) and optional `prices` CSV (`name,team,price,position`). The dashboard displays imported data with explicit missing-value flags. This is NOT an automated xgEdge/Statz connector: public read access does not establish bulk extraction permission. Obtain a permitted export or permission before importing their data. No fabricated player data is bundled. Imported season totals are not used as last-five form or claimed to be calibrated fantasy projections. Existing v0.6 fixture sync remains available.

## v0.9 — xgEdge HTML parser (deneysel)

`GET /api/players/xgedge` önce `robots.txt` erişimini ve izinlerini kontrol eder; sonra halka açık HTML tablolarından oyuncu, takım, dakika, gol, asist, xG ve xA sezon toplamlarını okur. Sonraki sayfa bağlantılarını takip eder (en fazla 9 sayfa, sayfalar arasında en az 1 saniye bekleme). 403/429, robots engeli veya HTML değişikliğinde durur. CAPTCHA/oturum/paywall aşılmaz. Kullanım koşullarını ayrıca kontrol edin; robots izni tek başına sözleşmesel izin değildir.

**Canlı doğrulama sınırlaması:** Bu geliştirme ortamında xgEdge alan adına DNS bağlantısı sağlanamadı. Parser yerel HTML testiyle kontrol edildi, gerçek site HTML'iyle çalıştığı garanti edilmez. Oyuncu fiyatları ve resmî fantasy pozisyonları hâlâ yoktur; otomatik optimum kadro hazır değildir.

## v1.0 — Dashboard sadeleştirmesi

Ön yüzdeki manuel CSV yükleme formları kaldırıldı. Dashboard yalnızca otomatik fikstür/takım formu ve xgEdge oyuncu güncelleme butonlarını gösterir. Önceki CSV API uç noktaları geriye dönük uyumluluk için sunucu tarafında korunmuştur, ancak arayüzden erişilmez. Oyuncu fiyatları hâlâ otomatik sağlanmadığından optimum kadro henüz hesaplanmaz.

## v1.0.2 — xgEdge sütun güvenliği
Oyuncu istatistikleri artık sadece tam olarak eşleşen HTML başlıklarından alınır;
önceki sürümdeki oyuncu hücresine göre otomatik sütun kaydırma kaldırıldı.
Hücre sayısı, sayısal tipler ve dakika/gol/asist tutarlılığı kontrol edilir.
Şüpheli veri sessizce kaydedilmez, API hata verir.
**Canlı xgEdge HTML erişimi bu geliştirme ortamında mümkün değildi.**
Eğer tablo farklı başlıklar kullanıyorsa HTML örneğiyle uyarlama gerekir.

## v1.1 — Gelecek hafta deneysel puan tahminleri

1. Dashboard'da **Fikstür ve takım formunu güncelle** butonuna basın.
2. **Oyuncuları internetten getir** butonuna basın.
3. **Tahmini puanları hesapla** butonuna basın.

Bu hesaplama sezon xG/xA toplamlarını takımın oynadığı maç sayısına böler;
sezon dakika toplamından beklenen oynama süresini tahmin eder ve FDR ile
hücum katkısını ayarlar. Resmî TFF Fantasy puan tahmini değildir: clean sheet,
kaleci kurtarışları, kartlar, bonuslar ve diğer kurallar dahil edilmemiştir.
Eksik istatistik veya eşleşmeyen pozisyon için tahmin boş bırakılır. Veri
sayfa yenilenince yeniden çekilmelidir; manuel CSV giriş alanı yoktur.

Yeni JSON API: `POST /api/projections/next-week` (`players`, `fixtures`,
`team_matches`). Kaynakların çevrimiçi çalışması yerel kurulumda doğrulanmalıdır.


## v1.2 — Pozisyon ve fikstür eşleştirmesi

Oyuncu yenileme artık `?positions=1` ile, xgEdge oyuncu profillerinde **açıkça yazılmış** pozisyonları sınırlı sayıda ve robots.txt kurallarına uyarak kontrol eder. Kaynakta pozisyon yoksa uydurulmaz. Profil URL'leri yalnızca aynı alan adındaki `/players/` bağlantılarından alınır. Bir yenilemede en fazla 60 profil kontrol edilir; profil alanları bulunamazsa pozisyonlar eksik kalır. Takım alias'larına `Başakşehir FK` ve `Amed Sportif Faaliyetler` eklendi. `fixture_missing` için neden açıklaması ve özet sayaçları eklendi. Bir takım seçili haftada fikstürde yoksa başka haftadan maç uydurulmaz.


### v1.2.1 pozisyon bağlantısı düzeltmesi
Önceki sürüm `profile_url` alanını üretmediği için profil taraması hiç çalışmıyordu. Artık oyuncu profil bağlantısı kaydediliyor ve kontrol sayısı gösteriliyor. Profil sayfası pozisyon bilgisi içermiyorsa tahmin yapılmaz.


## v1.2.2 — Pozisyon düzeltmesi
xgEdge oyuncu tablosunun `Pos` sütunundaki G/D/M/F kodları GK/DEF/MID/FWD olarak eşleştirilir. Pozisyon için profil taraması gerekmez. Oyuncuları ve tahminleri yeniden güncelleyin. xgEdge pozisyonu resmi TFF Fantasy pozisyonundan farklı olabilir.


## v1.3: pozisyon kaynak kontrolü
- xgEdge pozisyonu tahmini kabul edilir; doğrulanmış örneklerde Fantasy Süper Lig ana sayfasında gösterilen pozisyon önceliklidir.
- Doğrulanmış örnekler: Eldor Shomurodov, Gift Orban, Adrian Benedyczak. Sadece tam isim + normalize takım eşleşmesinde kullanılır.
- Tahmin tablosu pozisyonun kaynağını ve xgEdge ile çelişip çelişmediğini gösterir.
- fantasysuperlig.com kullanım şartları izinsiz scraping/otomasyonu yasaklar; bu sürüm o siteyi otomatik taramaz. Bu nedenle tüm 415 oyuncunun fantasy pozisyonu veya fiyatı doğrulanmış değildir.
- xgEdge verileri ve puan tahminleri aynı şekilde korunur.


## v1.4 — TFF resmî oyuncu verileri (yerel oturum)

1. `pip install -r requirements.txt`
2. `python -m playwright install chromium`
3. `python -m data_sources.tff_official login` — açılan tarayıcıda kendi hesabınızla giriş yapın, ardından terminalde Enter.
4. `python run.py` — arayüzde **TFF oyuncularını getir** düğmesine basın.
5. Fikstür ve xgEdge verilerini de güncelleyin, tahminleri ve optimum kadroyu hesaplayın.

Tarayıcı oturumu yalnızca bilgisayarınızda `~/.tff-optimizer-browser` içinde saklanır. Bu klasörü kimseyle paylaşmayın; ZIP'e eklemeyin. Oturum süresi dolarsa yeniden giriş yapın. Site kullanım koşullarına uyun; istekler manuel tetiklenir.

**Sınırlar:** TFF API yanıtının tamamı doğrulanmadı; `players`, `data`, `results` gibi yaygın JSON dizileri destekleniyor. xgEdge ile eşleştirme isim üzerinden ve yalnızca tekil eşleşmeler için yapılır; isim varyasyonları bazı oyuncuları dışarıda bırakabilir. Takım kimliği optimizasyonda kulüp sınırını korur. Tahminler resmî puanlama modelini tam kapsamaz.


### v1.5 estimation limitations
Players without xgEdge projections use a conservative heuristic based on TFF `pointsPerMatch` or `form`, season minutes and optional availability percentage. These fallback estimates do not include opponent difficulty and should not be interpreted as calibrated predictions. Players with no usable performance signal are excluded from optimization, rather than assigned 0. The optimizer prioritizes starting XI + captain, with bench quality used as a small secondary objective.


## v1.9 — 10. hafta uygunluk kontrolü

TFF API `availabilityStatus` ve `availabilityPercent` alanları değerlendirilir.
API kesin oynayamaz diyorsa oyuncu dışlanır. DOUBTFUL veya yüzdelik durum
beklenen puanı azaltır. UNKNOWN statüsü kesin sağlıklı demek değildir.

Resmî ceza/sakatlık kaynağı henüz otomatik entegre değildir. Doğrulanmış
10. hafta kararları arayüzdeki JSON kutusuna `player_id`, `round`, `status`,
`source` ve isteğe bağlı `checked_at` / `expires` ile girilebilir.
Örneğin `[{"player_id": 123, "round": 10, "status": "OUT", "source": "PFDK karar URL"}]`.
Bu örnekteki ID gerçek bir oyuncuya işaret etmez; TFF API ID'sini kullanın.
Manuel `AVAILABLE` kararı, TFF'nin kesin `UNAVAILABLE` durumunu geçersiz kılamaz.

Bu sürümde harici haber/PFDK otomatik sorgusu bulunmamaktadır;
manuel veri girilmezse TFF'nin bildirmediği cezalar tespit edilemez.

## v2.4: Geçmiş haftalar için retrospektif backtest

Önce TFF tarayıcı oturumunu açın (bir kez):

```powershell
python -m data_sources.tff_official login
```

9. hafta için 572 oyuncunun haftalık geçmişini indirip backtest çalıştırın:

```powershell
python -m analysis.historical_backtest --collect --round 9
```

İndirme yarıda kalırsa aynı komut eksik dosyalardan devam eder. Verileri yeniden çekmek için `--force` kullanın. Daha sonra internet bağlantısı olmadan:

```powershell
python -m analysis.historical_backtest --round 9
```

Çıktı: `historical_data/backtest_gw9.json` ve terminal özeti. `historical_data` klasörü kullanıcı bilgisayarında kalır; oturum çerezleri veya kullanıcı profili rapora eklenmez. Çok sayıda oyuncu isteği için yaklaşık birkaç dakika bekleyin; siteye aşırı yük bindirmemek amacıyla istekler arasında kısa aralık vardır.

**Dikkat:** Bu sonuç *retrospektif simülasyondur*, maç öncesi kaydedilmiş tahmin değildir. Geçmiş fiyatlar önceki hafta kayıtlarından alınır, ancak geçmiş sakatlık/ceza ve tam oyuncu havuzu doğrulanamaz. Ayrıca bu modül canlı xgEdge+FDR tahminini değil, geçmiş puanlar ve oynanan dakika üzerinden Bayesian form tahminini kullanır. Menajer kartları ve otomatik yedekler dahil değildir. Bunlar tamamlanana kadar sonucu tam tarihsel doğrulama olarak yorumlamayın.

## v2.5 — Çok haftalı backtest (5–9)

Önce `python -m data_sources.tff_official login` ile TFF oturumunu açın.

```powershell
pip install -r requirements.txt
python -m analysis.multiweek_backtest --collect
```

Önceden `historical_data/players.json` ve `player_<id>.json` dosyaları mevcutsa
tekrar indirmek gerekmez:

```powershell
python -m analysis.multiweek_backtest --train-rounds 5 6 7 8 --test-round 9
```

Çıktılar: `historical_data/multiweek_backtest_gw9.json` ve `.csv`.
Dört model eğitim haftalarında karşılaştırılır, en düşük ortalama mutlak takım
puanı hatasına sahip model seçilir ve yalnızca bu model bağımsız 9. haftada
raporlanır. Hedef haftanın sonuçları model girdisine alınmaz. Ancak geçmiş
sakatlık/ceza ve oyuncu havuzu doğrulanamadığı için sonuç **retrospektiftir**;
tam bir geçmiş zaman simülasyonu değildir. Otomatik yedek değişimi ve kartlar
hesaplanmaz. Test haftası, eğitim haftalarının tamamından sonra olmalıdır.

## v2.6 — Expanding-window historical backtest

After collecting historical_data using the previous collector, run:

```powershell
python -m analysis.walkforward_backtest --weeks 5 6 7 8 9
```

To collect if necessary: `python -m analysis.walkforward_backtest --collect`.

Outputs: `historical_data/walkforward_backtest_v26.json` and `.csv`.

GW5 is warm-up only (all models are evaluated but no winning model is picked using GW5's result). For GW6, model selection uses GW5 only; GW7 uses GW5–6; GW8 uses GW5–7; GW9 uses GW5–8. The selected model for each week is evaluated without incorporating that week's outcomes into its choice. The historical participation proxy filters players with very low appearances/minutes in preceding weeks, but is **not** an injury/suspension confirmation. Change threshold with `--min-participation 0.25`.

**Limitations:** historic player universe, historical eligibility, opponent strength and deadline prices are not point-in-time verified. No auto subs, manager cards or transfers. This does not establish the performance of the live FDR/xgEdge optimizer.

## v2.7 — Fixture proxy + calibrated walk-forward

Copy your existing `historical_data/` folder (players.json and player_*.json) into
this project, then run:

```bash
python -m analysis.walkforward_v27 --weeks 5 6 7 8 9
```

Outputs: `historical_data/walkforward_backtest_v27.json` and `.csv`.

v2.7 compares 4 existing form models against 4 variants with a conservative
opponent-strength proxy. For each target week, opponent strength is calculated
from **earlier** weeks' fantasy points conceded by position. Current-week
opponent identity is read from the retrospective history archive and has **not**
been verified as a pre-deadline fixture snapshot. Low-sample opponent factors
fall back to 1.0; others are heavily shrunk and clipped. The model is selected
using **previous weeks' realized points**, with raw prediction MAE as tie-breaker.
An additive calibration bias from prior weeks adjusts **reported forecasts only**;
it does not change optimized XI or captain. The existing minutes discount in
`project()` is retained without double-counting the participation proxy.

**This is not a point-in-time verified simulation.** No historical injury/
suspension verification, transfer availability, deadline prices, chip or
substitution scoring, and no true historical xG/odds snapshots. Do not infer
future performance from a handful of retrospective weeks.

## v2.8 — Risk-aware model selection and honest calibration comparison

Copy the same `historical_data` folder used for v2.7, then run:

```powershell
python -m analysis.walkforward_v28 --weeks 5 6 7 8 9
```

Outputs: `historical_data/walkforward_backtest_v28.json` and `.csv`.

Model selection uses only earlier weeks, maximizing **mean actual team points
minus 0.35 × standard deviation** (population SD); ties use prior raw MAE.
Use `--risk-penalty 0.5` to change the risk preference. With one training
week, a 15-point dispersion prior is used. This is a heuristic, not a
validated statistical confidence bound.

Calibration is separately reported, not used for lineup optimization:
prior-only additive bias is shrunk toward zero with four pseudo-observations
and capped at ±12 points. The report provides both **raw MAE** and
**calibrated MAE**, and both forecasts, without mixing the two.

**Caution:** The historical fixture opponent identifier comes from the
post-match archive, not a verified pre-deadline snapshot. Player eligibility,
injuries, prices, autosubs and chips are not fully reconstructed. This is
still a retrospective experiment, not a genuine point-in-time backtest.

## v2.9: Player form adjustment + captain risk

Copy your `historical_data/` directory into this project, then run:

```bash
python -m analysis.walkforward_v29 --weeks 5 6 7 8 9
```

Outputs `historical_data/walkforward_backtest_v29.json` and `.csv`.
Four predefined variants per v2.8 model/fixture candidate: `control`,
`player`, `captain`, and `combined` (32 total). The player adjustment is a
shrunk difference between recent and longer-run **historical realized points**;
it is not a learned forecast residual. The captain penalty is based on past
point volatility and only changes the captain bonus objective. These are
experimental heuristics, not proven improvements. The first week is warm-up.
The fixture opponent is still derived from a post-match archive, and historical
prices and availability are not verified at deadline. Backtest is retrospective.

## v3.0 — Conservative walk-forward and minutes audit

Default mode **disables the fixture adjustment** because previous versions used
opponent IDs from target-week post-match archives, which are not verified
pre-deadline. Player-level calibration and captain-risk experiment are also off.
This is a conservative comparison, **not a claim of higher points**.

```bash
python -m analysis.walkforward_v30 --weeks 5 6 7 8 9
```

Optional *retrospective-only* comparison (NOT deadline-verified):

```bash
python -m analysis.walkforward_v30 --weeks 5 6 7 8 9 --allow-retrospective-fixture
```

Outputs `historical_data/walkforward_backtest_v30.json` and `.csv`.
The minutes audit reports players in the selected XI who did not play or played
fewer than 60 minutes. Actual target-week minutes are used **only for the audit,
never to choose players**. Historical player pool, prices, injuries, suspensions
and lineup availability are still not point-in-time verified. Do not interpret
this as a fully leak-free production forecast.

## v3.1 — participation threshold walk-forward and fixture provenance audit

Keep your own `historical_data/players.json` and `player_<id>.json` files. Run:

```bash
pip install -r requirements.txt
python -m analysis.walkforward_v31 --weeks 5 6 7 8 9
```

Writes `historical_data/walkforward_backtest_v31.json` and `.csv`.
Compares participation thresholds 0.25 (v3.0 control), 0.45 and 0.65 for each of four
base models. Selection is made using **prior scored weeks only**. Current-week
minutes are inspected **after** selecting the lineup, for diagnostics only.

Optional fixture provenance audit (does not change predicted points):

```bash
python -m analysis.walkforward_v31 --weeks 5 6 7 8 9 --fixture-snapshot historical_data/fixtures_predeadline.json
```

The snapshot file format is:

```json
{"weeks":{"5":{"captured_utc":"2026-08-01T10:00:00Z","deadline_utc":"2026-08-02T10:00:00Z","source":"official-fixture-URL","matches":[{"home_club_id":1,"away_club_id":2}]}}}
```

Example dates/IDs are placeholders. **Do not invent historical snapshots.** Self-declared
timestamps cannot prove the data really existed before the deadline. Until independently
verifiable fixture and player snapshots exist, the report remains RETROSPECTIVE / NOT
POINT-IN-TIME VERIFIED. Fixture snapshot data is **audit-only** and never changes a lineup.
The default threshold is compared with other candidates but the selected model may change;
for a strict v3.0 baseline run v3.0 itself.

## v3.2 — fixture snapshot ablation (strict input)

Use **real pre-deadline fixture snapshots** for all requested weeks. See
`fixture_snapshot_v32.example.json` for the structure; replace placeholders and
include every team present in the player pool for each week. `home_club_id` and
`away_club_id` must use **the same identifier strings as the `team` field** in
`historical_data/players.json` (do not use opponentClubId if it uses another namespace).
The source and capture timestamp are user-declared and **not independently verified**.

```powershell
python -m analysis.walkforward_v32 --fixture-snapshot historical_data/fixtures_predeadline.json --weeks 5 6 7 8 9
```

Produces `historical_data/walkforward_backtest_v32.json` and `.csv`. Compares
four prior models with fixture weight 0 and 0.5, selecting each week's candidate
**using only earlier weeks**. A missing week, missing eligible team, duplicated
fixture, or post-deadline timestamp causes an error rather than silently using
post-match opponent data. Fixture difficulty is calculated from prior-round
fantasy points conceded by position, with shrinkage and clipping. A neutral
factor of 1.0 is used where prior-round opponent evidence is insufficient.

This is **not** a verified point-in-time backtest: historical player/team membership,
prices, suspensions, injuries and fixture capture provenance remain unverified.
Do not treat manually backdated fixtures as proven pre-deadline snapshots.
