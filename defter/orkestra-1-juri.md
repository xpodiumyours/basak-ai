---
kim:    opencode
tarih:  2026-08-24
konu:   ORKESTRA-1 — DIVERSIFY ve CRITICIZE dolduruldu (paralel jüri)
tip:    karar
omur:   sonsuz
kaynak: brain/orkestra.py + chat.py orkestra_bilesenleri + tests/test_orkestra_juri.py
---

ORKESTRA'nın v0'da boş olan iki istasyonu dolduruldu; iskeletin enjeksiyon
felsefesi korundu:

- **DIVERSIFY**: yeni OPSIYONEL `ek_adaylar` bileşeni. Anahtar
  ("orkestra_juri", varsayılan KAPALI) açıkken birincilden BAŞKA ücretsiz
  sağlayıcılar PARALEL olarak aynı soruyu yanıtlar (en fazla 2 aday).
  Kurallar: araç çağrılan turda koşmaz; ücretli ve 429 soğumasındakiler
  seçilmez; kota.engel_nedeni her aday için yeniden bakılır.
- **CRITICIZE**: yeni OPSIYONEL `aday_puanla` bileşeni — DETERMINISTIK
  puan (OLCU ilkesi: AI yorumu YOK). Üretim politikası: boş/"Bunu
  ölçemedim." adayı -50, kapıdan elenen her cümle -5. Araç cevabı
  değiştirirse puan tazelenir.
- **SELECT**: en yüksek puan kazanır; EŞİTLİKTE BİRİNCİL kazanır — jüri
  kapalıyken davranış birebir v0'dır. Kazananın kaynağı rapora taşınır.
- İz sırası sözleşmesi korundu (CRITICIZE, EXPERIMENT'ten önce); jüri
  kurulum hatası dürüstçe ATLANDI+sebep olarak düşer.

Jüri adayları brain.cevapla'yı BYPASS eder (zincir retry'si istenmez)
ama karne doğru kalsın diye stats.kaydet YAZILIR (B1 bağımlılığı).

KANIT: 11 yeni test (tests/test_orkestra_juri.py): paralel koşum, hata
veren/kurulumu patlayan jüri, eşitlikte birincil, boş aday eleme, kapı
cezası, arac_var sinyali, LEARN kazananla. Mevcut iz sözleşmesi
test_orkestra.py'de v1'e güncellendi (CRITICIZE artık koşar).
Canlı prova: gerçek zincirde cevap + karne devrede ("cloudflare %20 →
sona alindi"). Toplam 493/493 yesil.
