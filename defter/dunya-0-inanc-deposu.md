---
kim:    opencode
tarih:  2026-08-24
konu:   DUNYA-0 tamamlandi — sorgulanabilir inanç deposu
tip:    karar
omur:   sonsuz
kaynak: tools/dunya.py + tests/test_dunya.py
---

Kilitli hedefin "Dunya Modeli" organinin ilk halkasi kuruldu.

Tasarim ilkesi: YENI DEPO ACMAZ. Defter kayitlari zaten iddia, karne.json
kaynak guvenini tutuyor, bayat.py tazeligi olculyor. `tools/dunya.py` bu
ucunu tek sorgulanabilir inanc listesinde birlestirir; dosyalar kaynak
gercegi olmayi surdurur (motor hicbir seyi kendi basina degistirmez).

Inanc kaydi: {dosya, konu, kim, tarih, omur, kaynak,
durum(taze|bayat), guven(0-1), icerik}
- Guven kurali: karne'de kaynak verisi varsa dogru/(dogru+yanlis);
  yoksa notr 0.5 — bilinmedikce suclanmaz.
- Sorgu filtreleri: anahtar (konu/dosya/icerik), kim, tip(omur),
  kaynak, durum(taze|bayat), min_guven.
- dunya_ozet(): insan-okur ozet (taze/bayat sayimi + dusuk guvenliler).

KANIT: 8 yeni test (tests/test_dunya.py): taze/bayat ayrisma, karne
tabanli guven hesabi (3/1 -> 0.75) ve notr 0.5, anahtar/durum/kim/
min_guven filtreleri, ozet sayilari. Toplam 429/429 yesil.

Anlam: Basak artik "hatirlarim" demiyor — iddialari durumuyla
(taze/bayat), kaynak guveniyle ve icerigiyle birlikte SORGULAYABILIR
bir depoda tasiyor. Rapordaki "Iddia #483" ornegine ilk somut adim.

Sonraki dilimler: FAY-1 paralel juri, ORKESTRA-0 OBSERVE..LEARN dongusu
(on kosullari artik saglandi: DENEY-0 + DUNYA-0).
