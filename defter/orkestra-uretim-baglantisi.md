---
kim:    opencode
tarih:  2026-08-24
konu:   ORKESTRA üretim bağlantısı — gölge mod kapısı açıldı
tip:    karar
omur:   sonsuz
kaynak: chat.py + tests/test_orkestra_yol.py
---

Kilitli hedefin son büyük bağlantısı: orkestra artık ÜRETİME
BAĞLANABİLİR durumda.

Mekanizma (gölge mod ilkesi):
- ayarlar.json'da "orkestra_ana_yol": true YAZILANA KADAR mesaj_isle
  eskisi gibi çalışır — davranış değişikliği sıfır.
- Anahtar yazıldığında basak_app mesaj_isle_orkestra()'ya yönlenir;
  akış 10 durumluk makineden geçer, iz loglanır, yetki tavanı ve
  çıkış kapısı AYNI savunmalarla korunur.
- deney_kos bileşeni QUESTION'da seçilen araç setini taşır — yetki
  tavani orkestra yolunda da geçerli.
- LEARN episodic kaydı onem puanıyla yazar.

KANIT: tests/test_orkestra_yol.py — anahtar üç konumuyla (false/true/
dosya-yok) doğru okunuyor. Tüm süit 468/468 yeşil.

Kabul kalan halka: canlı kullanımda birkaç gün gölge karşılaştırması;
eşdeğerlik gözlemlenince anahtar kalıcı açılır. SELF-1 hariç kilitli
planda kod tarafı tamamlanmış durumdadır.
