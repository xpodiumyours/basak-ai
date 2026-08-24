---
kim:    opencode
tarih:  2026-08-24
konu:   B3 tamamlandi — kota gercek token butcesine gecti
tip:    karar
omur:   sonsuz
kaynak: brain/kota.py + brain/registry.py + tests/test_kota_token_butcesi.py
---

Kilitli hedefin B3 fazi: groq'un 200.000 token/gun limiti eskiden
"80 istek" diye TAHMIN edilerek takip ediliyordu. Artik:

- registry groq kartinda `gunluk_token: 200000` (429 mesajindan olculmus
  gercek deger); tahmini gunluk_istek=80 kaldirildi.
- kota.engel_nedeni kartta gunluk_token gordugunde BUGUNUN gercek token
  toplamini stats.py'den sorar (token_bugun()); harcanan >= butce ise
  "gunluk token butcesi doldu (X/Y)" ile engeller.
- Olcum hatasi engel KURMAZ — olcum sohbeti bozmasin prensibi.
- gunluk_token tanimli olmayan araclar istek sayaciyla surer (glm/nvidia/
  kilo gibi limiti bilinmeyenler etkilenmez).
- stats.py'ye token_bugun(model) eklendi (UTC gun siniri — saglayici
  resetleriyle uyumlu).

KANIT: 7 yeni test (tests/test_kota_token_butcesi.py): butce alti gecer,
dolunca "(510/500)" mesajiyla engel, baska saglayicinin butcesi karismaz,
gunluk_token'siz arac istek yoluyla surer, istek limiti bagimsiz calisir,
stats cokurse engel kurulmaz, registry'de gercek butce dogrulanir.
Mevcut router testinin bir beklentisi groq->gemini tasindi (groq artik
istek-limitli DEGIL). Toplam 403/403 yesil.

Bilinen sinir: butce sorgusu her engel kontrolünde DB okur (ucuz SQLite);
coklu surec yazici yok — tek surec kilidi yeterli.
