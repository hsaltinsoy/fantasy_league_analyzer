# Futbol sahası üzerinde kadro UI

PowerShell:

```powershell
py -m pip install -r requirements.txt
py -m playwright install chromium
py -m data_sources.tff_official login
py run.py
```

Tarayıcıda `http://127.0.0.1:5000/lineup` adresine gidin. Alternatif: `RUN_UI.bat` dosyasına çift tıklayın.

- `Kadroyu oluştur`: 15 kişilik optimum kadroyu hesaplar ve ilk 11'i futbol sahasına yerleştirir.
- `Canlı veri`: güncel oyuncu fiyatı ve durumunu TFF API'den çeker; tarayıcı profiliyle giriş gerektirir.
- `Kayıtlı veri`: proje içindeki oyuncu anlık görüntüsünü kullanır (eski olabilir).
- `Son kaydı göster`: daha önce hesaplanan JSON'u açar.
- Model, hafta ve Haftanın Takımı ağırlığı UI'den seçilebilir.

Fikstür ve geçmiş oyuncu verileri hâlâ yerel arşivden gelir. Bu uygulama transfer hakları ve kullanıcının mevcut kadrosunu dikkate almadan sıfırdan ideal kadro üretir.
