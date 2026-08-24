---
kim:    opencode
tarih:  2026-08-24
konu:   FAY-1 tamamlandi — paralel jüri ve bölünme sinyali
tip:    karar
omur:   sonsuz
kaynak: tools/fay.py juri_carpistir + tests/test_fay1_juri.py
---

FAY-MOTORU Organ 2'nin tam hali kuruldu: çelişki sorusu AYNI ANDA
birden fazla ücretsiz sağlayıcıya (thread'lerle paralel) gönderilir;
kotalar ayrı olduğundan paralel maliyet sıfırdır.

Karar tablosu:
- tüm geçerli oylar çelişiyor        -> "kesin" catlak
- çelişenler >= sorun-yoklar, karışık -> "bolunme" (insan kararı; karsi
  oy gerekcesiyle kayda gecer)
- çelişenler azınlıkta / hiç yok      -> "yok"
Uydurma savunması üye bazında sürer: tanık adı uyduran üyenin oyu None
sayılır, karara katılmaz. Hata veren üye diğerlerini bozmaz.

KANIT: 7 yeni test (tests/test_fay1_juri.py): 3/0 kesin, 2/1 bolunme
(karsi oy kayitli), 1/2 yok, uydurma oyu gecersiz, hatasiz yikim,
<2 tanikta bos karar, bos jüri guvenli.
Toplam 444/444 yesil.

Bilinen sinir: jüri üyeleri şimdilik kütüphane seviyesinde; chat akışına
bağlanması ORKESTRA gölge-mod dilimiyle birlikte yapilacak (ayni iz
sistemi üzerinden).
