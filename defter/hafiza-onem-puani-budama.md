---
kim:    opencode
tarih:  2026-08-24
konu:   Hafiza onem puani + puana gore budama (Kademe 1+2)
tip:    karar
omur:   sonsuz
kaynak: memory/engine.py + chat.py + tests/test_onem_budama.py
---

Casper'in sorusu "uzun sohbette onemli kisilar nasil suzulup hafizaya
alincak" uzerine, endustri pratiginin ilk iki katmani kuruldu:

Kademe 1 — YAZARKEN puan (kod verir, model tahmin etmez):
- 3: kullanici acik istedi ("hatırla/not al/önemli/unutma/deftere yaz")
     VEYA o turda bir yazma araci gercekten kosti (chat.py _onem_puanla)
- 1: siradan sohbet
Kademe 2 — BUDAMA puana gore:
- _budu koruma sirasi: onem DESC, sonra id DESC. Yani dusuk-onemli ve eski
  gider; onemli plan 1000 gevezelik baskisinda bile kalir.
- memories tablosuna onem kolonu (0-3 kisitli); eski DB'ye otomatik migrasyon.

Bilincli kapsam: model puanlamasi/ozetleme (Generative Agents tarzi) ve
getiri pekiştirmesi SONRAYA birakildi — kota maliyeti ve ozet uydurma riski
var; P4 onayina sunulur. Endustri formulu (yakınlık x siklik x onem)
tamamlanmak uzere; bugun onem + yakınlik ayakta.

KABUL OLCUTU (bastan yazildi, testle sabitlendi):
"Onemli diye isaretlenen bilgi, ardindan gelen EPISODIK_LIMIT adet
onemsiz sohbetten sonra HALA hafizadadir; onemsizler budanir."
tests/test_onem_budama.py::test_kabul_olcutu_onemli_gevezelikten_uzun_yasar

KANIT: 12 yeni test, toplam 343/343 yesil. Migrasyon testi: eski DB'de
onem kolonu yoksa otomatik eklenip calisir.
