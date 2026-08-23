---
kim:    opencode
tarih:  2026-08-24
konu:   Kapanista hafiza DB'si gercekten kapanir oldu
tip:    karar
omur:   sonsuz
kaynak: kod incelemesi + tests/test_kapanis_db.py
---

Casper'in buldugu hata: Api.quit() DB kapatma blogunda self._hafiza'ya
bakıyordu; gercek hafiza nesnesi chat.py modul-globalinde (_hafiza) ve Api
uzerinde boyle bir alan HIC olusturulmuyordu. Blog oluyordu; hemen
ardindan os._exit(0) DB'yi acik birakiyordu — WAL dosyasi buyuyerek kaliyordu.

Cozum (`basak_app.py`): DB kapatma cikarildi -> `_hafizayi_kapat()` metni;
gercek globale dogrudan bakar (getattr(chat, "_hafiza")). Onemli ayrinti:
kapanis sirasinda motor YOKSA _hafiza_al() CAGRILMAZ — o fonksiyon motoru
yaratir, kapatmak icin yenisini acmak saçma olur.

KANIT: 3 yeni test (tests/test_kapanis_db.py): gercek motorun kapatildigi,
motor yoksa (None/False) istisna firlamadigi ve eski hatanin regresyonu
(self._hafiza yokken bile gercek motorun kapanmasi). quit()'in tamami test
edilmez — sureci oldurur; cikarilan metin denetlenir. Toplam 346/346 yesil.
