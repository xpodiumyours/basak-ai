---
kim:    opencode
tarih:  2026-08-24
konu:   Faz 2 — canlı test hattı kuruldu; ilk gerçek koşum 11/11
tip:    karar
omur:   sonsuz
kaynak: conftest.py --live + tests/live/ + CANLI-KAPISI.md
---

Ünite testleri sözleşmeyi korur; canlı hat GERÇEĞİ kanıtlar (Casper
planı, CANLI-KAPISI.md sırası).

KURAL: tests/live/ normal pytest'te OTOMATİK ATLANIR (kök conftest.py
--live anahtarı); yalnız `pytest tests/live --live` ile koşar. Kota
harcar — günlük kullanım öncesi değil, bilinçli prova anında.

KURULAN SENARYOLAR (11 test):
- Açılış: Brain+zincir, Api.boot() sözleşmesi (UI'sız), SQLite
  kapat-aç kalırlığı
- Failover: canlı sohbet, GEÇERSİZ anahtarla gerçek 401 sonrası zincir
  devri, tüm modeller kapalıyken AÇIK RuntimeError ("Hicbir model"),
  ücretli sağlayıcı engelinin canlı teyidi
- Hafıza: kapat-aç sonra hatırlama, episodic temizliğin semantic'e
  dokunmaması + temizlenenin geri GELMEMESİ, 1000 kayıt tavanında
  önemli (onem=3) anıların korunması, birebir tekrar dedupe

SONUÇ: İlk gerçek koşum 11/11 (36 sn). Raporlar data/canli-rapor/.
Sonraki faz: mini job queue (görev kaybı=0 kabulü için).
