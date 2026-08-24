---
kim:    opencode
tarih:  2026-08-24
konu:   FAY-3 tamamlandi — aktarici (kendi kulliyatindan mekanizma transferi)
tip:    karar
omur:   sonsuz
kaynak: tools/aktarici.py + tests/test_aktarici.py
---

FAY-MOTORU Organ 4 kuruldu: en yuksek gerilimli catlak raporlanmakla
kalmaz, COZULMEYE calisilir.

Yontem: cozumlu celiski havuzu = defter'deki tip=karar kayitlari
(Casper'in verdigi kararlar = kanitlanmis mekanizmalar). Catlagin konu+
gerekce+cift metni ile eski kararlarin kelime kumeleri Jaccard
benzerligiyle karsilastirilir; en benzer sekildeki eski cozumun
mekanizmasi onerilir (icerik degil SEKIL aktarimi).

v0 bilincli secimler:
- Eslestirme deterministik (kelime benzerligi) — LLM'siz calisir,
  test edilebilir. LLM destekli sekil-esleştirme sonraki dilim.
- Aday yoksa dis arama YAPILMAZ — o karari Casper verir.
- min_benzerlik=0.10 esigi tamamen alakasiz onerileri eler.

KANIT: 5 yeni test (tests/test_aktarici.py): karar tipi kayitlar havuza
duser (alinti ayiklanir), "izin alinamiyor" catlagina Xses'teki
"kullanici kendi onaylasin" mekanizmasinin onerildigi, eslesme yoksa bos
donuldugu, limit uygulandigi, bos kulliyatta guvenli davranis.
Toplam 458/458 yesil.

Not: kabul olcutu ("Casper bunu dusunmemistim der") canli kullanimda
gerceklesir — kod tarafindaki hazirlik tamamlanmistir.
