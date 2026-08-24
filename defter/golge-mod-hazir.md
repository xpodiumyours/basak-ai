---
kim:    opencode
tarih:  2026-08-24
konu:   Gölge mod — eşdeğerlik ölçümü canlıya hazır
tip:    karar
omur:   sonsuz
kaynak: chat.py golge fonksiyonları + tests/test_golge_mod.py + basak_app.py
---

ORKESTRA'nın ana yola geçişinden ÖNCE gereken eşdeğerlik kanıtı için
gölge mod kuruldu:

- ayarlar.json'da "golge_mod": true iken HER mesajdan sonra orkestra
  yolu sessizce koşturulur (kaydet_acik=False — geçmişe/hafızaya yazmaz)
- eski yolun cevabıyla kelime-Jaccard benzerliği hesaplanır ve
  data/orkestra_golge.log'a satır olarak düşer:
    ts | benzerlik=0.87 | eski=... | yeni=...
- Kullanıcıya dönen cevap HİÇ DEĞİŞMEZ — bu saf ölçümdür.
- basak_app._chat entegrasyonu: mesaj_isle sonrası otomatik koşar;
  kapalıyken hiçbir ek maliyet yok.

Yöntem: birkaç günlük normal kullanımda benzerlik dağılımı toplanır;
istisnasız yüksek çıkarsa "orkestra_ana_yol": true ile durum makinesi
ana yola geçer (B2 provalarıyla aynı taze-kota penceresinde).

KANIT: 9 yeni test (tests/test_golge_mod.py): benzerlik formülü uçları,
anahtar üç konumu, gölgede geçmiş dosyası oluşmadığı (yazma izolasyonu),
basak_app._chat entegrasyonunda açik/kapali davranışlar.
Toplam 475/475 yesil.
