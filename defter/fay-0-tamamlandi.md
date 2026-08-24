---
kim:    opencode
tarih:  2026-08-24
konu:   FAY-0 tamamlandi — uc olcen tanik, uydurmaya kapali carpistirici
tip:    karar
omur:   sonsuz
kaynak: tools/fay.py + tests/test_fay0.py + canli kart uretimi
---

Kilitli hedefin FAY hattinin ilk fazi kuruldu (FAY-MOTORU.md §FAY-0):
TEK konu, UC tanik (belge/git/dosya), jurisiz.

Tasarimin iki kritik kurali kodda savunuldu:
1. TANIKLAR OLCER, URETIMEZ: iddialar yalnizca salt-okunur olcum araclari
   ciktisindan gelir (git_durum/belge_ara/dosya_bilgi); basarisiz tanik
   sessizce atlanir.
2. UYDURMA CELISKI KARTA GIREMEZ: modelin isaret ettigi tanik adlari
   gercek listede yoksa yanit reddedilir (_yanit_coz); [SORUN YOK] ve
   anlasilmayan yanitlar catlak sayilmaz.
Motor hicbir seyi duzeltmez; kart gosterir, karar Casper'in.

CANLI KANIT: gercek vixrex deposu uzerinde kart uretildi:
  git diyor: Dal fix/v50-sharedpreferences-localstorage,
  son commit a93e34e (2026-08-24 03:20)
Belge/dosya taniklari bu sorgu icin veri dondurmeyince sessizce dustu
(davranis dogru); tek tanik kalincia catisma aranmadi (>=2 gerekir).
Kabul olcutunun son halkasi ("Casper git'e bakip evet diyecek") Casper'a
aittir — a93e34e commit'i onun dogrulamasi icin kayit altinda.

KANIT: 10 yeni test (tests/test_fay0.py): uc tanigin toplandigi,
basarisiz taniğin atlandigi, uydurma tanik adi reddedildigi, SORUN YOK /
anlasilmayan / hata durumlarinda None doneuldugu, kart bicimi ve
uctan-uca akisin calistigi. Toplam 421/421 yesil.

Sonraki dilimler: FAY-1 paralel juri -> DUNYA-0 belief store ->
ORKESTRA-0 OBSERVE..LEARN dongusu. B2 borc provalari taze kotalarda.
