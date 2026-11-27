# v3.8 – Deneysel model iyileştirmesi

## Kurulum
ZIP dosyasını yeni bir klasöre açın, terminalde:

```powershell
python -m pip install -r requirements.txt
python run.py
```

Tarayıcı: http://127.0.0.1:5000/lineup

Model menüsünde **Dengeli 5 hafta (deneysel)** seçeneği eklenmiştir. Önceki **Son 3 hafta formu** korunmuştur.

## Değişiklikler
- `robust_5w`: Son 5 haftalık oyuncu puanlarını kullanır, tek haftalık aşırı puanları sınırlar, daha yüksek shrinkage ve daha düşük kısa form ağırlığı kullanır.
- Kaptan alternatifleri, optimizasyonun kullandığı risk ayarlı kaptan bonusuna göre sıralanır. Önceki sürüm ham xPts'e göre sıraladığı için kaptan listesi yanıltıcıydı.
- Ekranda çözücü durumu ve kalan bütçe gösterilir. Kalan bütçenin bulunması tek başına optimizasyon hatası değildir.

## Doğrulama
`python -m pytest -q tests/test_robust_v38.py` komutu iki yeni birim testini çalıştırır.

**Önemli:** Bu deneysel modelin GW6–9 üzerinde 246 puanı aştığı henüz doğrulanmadı. Önceki 246 puan v3.6'nın walk-forward sonucudur. v3.8'i geçmiş haftalara karşı test etmeden performans artışı iddia etmeyin. Canlı maç kadroları ve sakatlık durumları kesin değildir.
