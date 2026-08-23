---
kim:    opencode
tarih:  2026-08-23
konu:   Baglam diyeti ADIM 1 — dinamik arac sunumu
tip:    olcum
omur:   30g
kaynak: _taban_olcum.py oncesi/sonrasi + tests/test_dinamik_araclar.py
---

Baglam diyetinin 1. adimi: tek anahtar kelime eskiden 18 aracin TAM kilavuzunu
aciyordu (~8.384 karakter / ~3.000 token her istekte). Artik soru yalniz
ilgili arac ailesinin kilavuzunu acar (`chat.py` _dinamik_araclar):
- olcum uclusu (git_durum/belge_ara/dosya_bilgi) HER ZAMAN acik (O-1 kurali)
- hava->web_search+sayfa_oku, hatirla->save_note+deftere_kaydet,
  dosya->okuma/yazma/listeleme, video/fotograf/model-stats tetikleyicileri eklendi
- yetki tavani aynen gecer: dongu dinamik seti asamaz (test_yetki_tavani guncel)

KANIT (ayni gece, ayni soru, 10 tur gercek zincir):
- Kilavuz yuku : olcum sorusunda 8.384 -> 1.517 karakter (%82 azaldi)
- ARAC CALISTI : %30 -> %80  (8/10) — DISETTIGIMIZ halde DISIPLIN ARTTI;
  sebebi: 18 kilavuz yerine 3'u goren model dogru araci daha kolay seciyor
- Durust red   : %60 -> %20 ; olcumsuz bilgi sizintisi 1 -> 0 ; hata 0
- Testler      : 9 yeni test, toplam 303/303 yesil

Not: test_yetki_tavani'nin "tam set" beklentisi yeni mimariye uyarlandi —
tavan INVARIANT'I (dongu seti buyutmez) degismedi, yalniz setin icigi dinamiklesti.
Bilinen sinir: tetikleyici kelime listesi kapali; listeye girmeyen bir ifade
araci sunmaz (model o araci O TURDA kullanamaz). ASCII yazim farkliliklari
("hatirla"/"hatırla") tetiklemez — mevcut liste Turkce klavye varsayar.
