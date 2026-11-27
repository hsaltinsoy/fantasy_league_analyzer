# TFF Fantasy Dashboard v3.7

## Kurulum / çalıştırma

```powershell
python -m pip install -r requirements.txt
python run.py
```

Tarayıcı: http://127.0.0.1:5000/lineup

**Kadroyu oluştur** seçeneğinde "Canlı veri" seçiliyse mevcut TFF oyuncu fiyatları ve kulüp bilgileri çekilir. Kulüp isimleri ve logoları resmi `/api/backend/projection/stats/club-stats?league-id=1` endpoint'inden alınır. Endpoint başarısız olursa son kaydedilmiş kulüp verisi veya "Kulüp ID" görünür; uydurma isim gösterilmez.

Kaptan alternatifleri ilk 11 oyuncularının xPts değerlerine göre sıralanır. Kaptan değiştirmek bu sürümde yalnızca karşılaştırma amaçlıdır; otomatik yeniden optimizasyon yapılmaz.

**Kendi ilk 11'inle karşılaştır** bölümüne 11 oyuncunun sayısal TFF playerId değerlerini virgülle ayırarak yaz. Bu, oyuncu örtüşmesini gösterir; mevcut takımın transfer kısıtlarını ve puanlarını hesaba katmaz. Oyuncu isimleri kaydedilmiş oyuncu verilerinden alınır ve güncel olmayabilir.

## Veri ve sınırlar
- Geçmiş maç verileri ve resmi fikstür kayıtlı arşivden gelir.
- Tahmin puanları garanti değildir.
- Gerçek kulüp logoları TFF API'den dönen URL'ler üzerinden tarayıcıda yüklenir.
- TFF tarayıcı oturumu yerel bilgisayarda tutulur, ZIP içinde yer almaz.
