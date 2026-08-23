---
kim:    opencode
tarih:  2026-08-24
konu:   E2E oturum senaryosu + gizli cift-cagri hatasi
tip:    olcum
omur:   30g
kaynak: tests/test_e2e_akis.py + canli tek tur duman testi
---

Push oncesi Casper'in talebiyle uctan uca dogrulama kuruldu. Senaryo testi
(tests/test_e2e_akis.py) alt sistemleri TEK SIRADA zincirler:
sohbet turu -> "hatirla" turu (yazma araci + onem=3) -> olcum turu
(git_durum + [O] kanitli cevap) -> temizlik (gecmis+episodic birlikte,
sayi raporlu) -> kapanista DB kapanisi.

E2E ILK TURDA GIZLI GERCEK HATA YAKALADI:
"olcum_aktif" kosulu 'sunulan sette olcum araci var' diye bakıyordu.
Baglam diyeti Adim 1 ile olcum uclusu HER TURDA sunulur olunca bu kosul
her sohbette dogru cikiyordu -> siradan sohbet de guclu-model RETRY'yla
IKINCI cagri yapiyordu. Sonuc: her mesajda ~2x gecikme ve kota harcamasi.
Duzeltme: retry kosulu artik sorunun KENDISINE bakar (olcum anahtar
kelimeleri); siradan sohbet TEK cagridir (testle sabit).

KANIT:
- E2E senaryo testi 2/2; tum suite 352/352 yesil
- Derleme taramasi: degisen tum .py dosyalari py_compile OK
- Canli duman testi (_taban_olcum.py 1): gercek zincirde 1/1 turda arac
  kostu, 0 hata, cevap kapidan gecti

Ders: parca testleri yesil dedirtiyor; E2E zinciri ancak alt sistemlerin
ETKILESIMindeki bozuklari goruyor. Buyuk degisikliklerden sonra E2E
kosulmali (yeni gelenek).
