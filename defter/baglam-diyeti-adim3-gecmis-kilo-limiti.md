---
kim:    opencode
tarih:  2026-08-24
konu:   Baglam diyeti ADIM 3 — gecmis penceresine kilo limiti
tip:    karar
omur:   sonsuz
kaynak: chat.py _gecmis_pencere + tests/test_gecmis_pencere.py
---

Adim 3: "son 20 mesaj" kurali yerine KILO limitli pencere geldi
(`chat.py` `_gecmis_pencere`, butce 4.000 karakter):
- En yeni mesajdan geriye dogru toplanir, butce dolunca durur
- Mesajlar BUTUN halde alinir (ortasindan kesme yok)
- En az bir (en yeni) mesaj garantidir; kronoloji korunur; 20 mesaj
  ust siniri da yururur

Casper'in onarti: kesim hafizadan silmek DEGILDIR. Her soru-cevap cifti
pencereden once hafiza motoruna yazilir; dusen eski kisimlar ilgili
soru gelince motorun aramasiyla geri doner. Kesim yalnizca o turda
modele gonderilen cerceveyi daraltir.

Etki: tepe yuku artik gecmis uzunlugundan bagimsiz. Kabaca en kotu durum:
notlar(2.1k) + promptlar(~4.2k) + dinamik araclar(~1k) + anilar(~0.7k) +
gecmis(4k) = ~12k karakter (~4.500 token) — groq'un 8.000 TPM'i altinda.
Dunku tasiyan senaryo (9.313) mimarik olarak imkansizlasti.

KANIT: 8 yeni test (tests/test_gecmis_pencere.py), toplam 311/311 yesil.
Canli dogrulama yarinki temiz probe ile birlikte (Adim 2 hukmuyle ayni oturum).

Bilinen sinir: tek mesaj butceden buyukse yine de tam gider (en yeni
garantisi) — dev tek cevap pencereyi tek basina doldurabilir.
