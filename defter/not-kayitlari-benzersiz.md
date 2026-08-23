---
kim:    opencode
tarih:  2026-08-24
konu:   Ayni adli not/defter kayitlari artik ezilmiyor
tip:    karar
omur:   sonsuz
kaynak: tools/notes.py + tests/test_not_benzersiz.py
---

Casper'in bulgusu dogrulandi: save_note ve deftere_kaydet basliktan slug
uretip dosyayi "w" modunda aciyordu — ayni slug tekrar gelirse eski kayit
EZILIYOR. Daha kotusu: INDEX guncelleyicisi "bu dosya adi index'te zaten
varsa satir ekleme" kontrolu yuzunden ezilen kaydin ikinci satiri da
dusmuyordu; kayip tamamen sessizce gerceklesiyordu. ORTAK-DEFTER'in
"silme yok, uzerine yazilmaz" felsefesi kodda hic savunulmuyordu.

Cozum (`tools/notes.py`):
- `_benzersiz_yol(klasor, dosya_adi)`: hedef varsa '-2', '-3'... sonekiyle
  bos ad bulunur (999'u asarsa zaman damgali garantili benzersiz)
- iki fonksiyon da bu cozucuyu kullanir; eski kayit HER ZAMAN yasardi
- slug uretimi ortak `_slug()` yardimcisina alindi (kod ikilemesi giderildi);
  tumu ozel karakterse varsayilan ad ("not"/"kayit") kullanilir
- INDEX'e her yeni dosya kendi satiriyla duser — iki kayit da gorunur

KANIT: 6 yeni test (tests/test_not_benzersiz.py): ayni baslikla iki kayit ->
iki dosya, icerikler saglam; ucuncude -3; defterde iki frontmatter'li dosya
ve INDEX'te iki satir; bos-slug varsayilan adi. Toplam 368/368 yesil.

Not: slug Turkce karakterleri korur (eski davranis) — testler buna gore
yazildi; degisiklik yapilmadi.
