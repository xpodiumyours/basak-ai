---
kim:    opencode
tarih:  2026-08-24
konu:   "Hafiza temizlendi" yalani kapandi + hafizaya yasam dongusu
tip:    karar
omur:   sonsuz
kaynak: kod incelemesi + tests/test_hafiza_yasam_dongusu.py
---

Casper'in buldugu guven/UX acigi: UI "hafiza temizlendi" diyordu ama
Api.clear() yalnizca gecmis.json siliyordu; episodic anilar basak.db'de
kaliyor ve sonraki konusmalarda bulunabiliyordu.

Casper'in istegi: tamamen silmeden, sisme engellenerek cozmek.

Cozum uc parcali:
1. DURUSTLUK — clear() artik sohbetten ogrenilen EPISODIC anilari da
   unutturur ve kac kayit silindigini dondurur; UI gercegi soyler
   ("sohbet temizlendi, N ani unutuldu").
2. SINIR — knowledge/defter/obsidian indekslerine (kind='semantic')
   DOKUNULMAZ: onlar dosyalardan turetilir, sohbet degil. Casper'in
   "tamamen silmesin" sarti boylece saglanir.
3. SISME ENGELI — engine'de yasam dongusu:
   - EPISODIK_LIMIT=1000 satir tavani; asilinca EN ESKILER otomatik
     budanir (_budu, her yazimda calisir)
   - birebir ayni soru-cevap cifti tekrar yazilmaz (dedupe)
   - budama FTS + vektor tablolarini da senkron siler

KANIT: 9 yeni test (tests/test_hafiza_yasam_dongusu.py): dedupe, budama
(en eski gider en yeni kalir, dogrudan DB icerigiyle), episodik_temizle'nin
semantic'e dokunmadigi, Api.clear'in gecmis+anilari birlikte unutup motoru
olmayan kurulumda da ayakta kaldigi. Toplam 331/331 yesil.

Bilinen sinir: budama satir sayisina gore; kayit basi boyut siniri yok
(zaten episodik metinler 1000+1000 karakterle kesiliyor). Semantic indeks
buyumesi dosya boyutuna bagli, mtime takibiyle mukerrer degil.
