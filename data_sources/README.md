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
