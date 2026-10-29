# v3.9 — Maç bazlı risk tercihleri

Windows: `python -m pip install -r requirements.txt` ardından `python run.py`, tarayıcıda `http://127.0.0.1:5000/lineup`.

**Maç riski** menüsü: Agresif (ceza yok; v3.8 davranışına en yakın), Dengeli (her karşıt defans-hücum ilk 11 çifti için 0.18 xPts tercih cezası), Düşük risk (0.36 xPts). Sadece rakip takımların **ilk 11'deki** DEF/GK ile MID/FWD oyuncuları için uygulanır. Aynı takımdan iki defans oyuncusunu otomatik yasaklamaz.

Bu ceza beklenen puanın matematiksel tahmini değil, riski azaltmak için kullanılan bir **tercih fonksiyonudur**. Ekrandaki beklenen puan risk cezasından önceki tahmindir; risk cezası ayrıca gösterilir. Her formasyon risk ayarlı amaç fonksiyonuna göre sıralanır.

CLI: `python -m analysis.predict_next_week --week 10 --risk-profile balanced`.

**Sınırlamalar:** Tarihsel backtest bu sürümde henüz çalıştırılmadı. Özellikle GW6–GW9'daki gerçek geçmiş kulüp üyelikleri, fiyatlar ve deadline öncesi uygunluk doğrulanmadan sızıntısız performans karşılaştırması yapılamaz. Daha gelişmiş skor senaryoları için takım bazlı gol olasılıkları gerekecektir.
