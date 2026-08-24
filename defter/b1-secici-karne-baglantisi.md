---
kim:    opencode
tarih:  2026-08-24
konu:   B1 tamamlandi — secici karneyi okuyor (meta-ogrenme ilk halka)
tip:    karar
omur:   sonsuz
kaynak: brain/secici.py + brain/brain.py + tests/test_secici_karne.py
---

Kilitli hedefin ilk fazi B1 tamamlandi: secici artik DENEMIYI okuyor.

Politika (bilincli dar, guvenli):
- Kurallar temel sirayi verir (degismedi).
- Karne katmani yalnizca GERIYE itebilir: son 72 saatte >=5 cagrisi olan
  ve basari orani %50 altina dusen saglayici sona alinir.
- Gerekce seffaf: "karne: nvidia (%25.0) sona alindi".
- Orneklem esigi gurultuyu eler; stats hatasi sessizgecer (sohbet bozulmaz).
- Terfi (bandit tarzi one alma) bilinclì olarak SONRAKI dilimdir.
Uretimde brain.cevapla karne_kullan=True ile acar; sec()'in varsayilani
kapali kalir (geriye uyumluluk).

KANIT: 6 yeni test (tests/test_secici_karne.py): kotu karne sona alindi,
saglam karne sirayi degistirmez, az ornekleme ses cikarmaz, stats hatasi
sessiz, coklu zayif sirasi korunarak sona gider, kapaliyken eski davranis.
Toplam 396/396 yesil.

Anlami: Basak artik model seciminde SABIT KURALLARDAN deneyimle
degisen ilk katmana gecti. Siradaki dilimler: B2 borc provalari + Kilo
olcumu, B3 kota.py'nin gercek token butcesine gecisi.
