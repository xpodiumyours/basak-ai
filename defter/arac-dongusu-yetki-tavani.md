---
kim:    opencode
tarih:  2026-08-23
konu:   Arac dongusunda yetki tavani (Casper'in buldugu acik)
tip:    karar
omur:   sonsuz
kaynak: kod incelemesi + tests/test_yetki_tavani.py
---

Casper'in buldugu guvenlik acigi: cok adimli arac dongusunde yetki genisliyordu.
Ilk model cagrisinda aktif_toollar suzuluyordu (anahtar kelime yoksa yalniz
olcum aracları), ama `_tool_calling_multi(..., tools)` HAM listeyi aliyordu ve
ikinci turda modele write_file_tool, deftere_kaydet, ac_uygulama dahil her
araci sunuyordu. Yani olcum sorusuyla baslayan bir is ortasinda yazma/sistem
yetkisine tirmanabiliyordu.

Neden tek kapı bu: `tools/permissions.py` tum tanimli araçlara etiket verdigi
icin executor izin katmani tanimli her araci geciriyor; modelin gorebildigi
araç setini YALNIZCA chat.py'deki sunum suzgu belirliyor.

Cozum (`chat.py`): donguye `aktif_toollar` girer, ham `tools` degil. Ilk turda
ne sunulduysa o tavandir; dongu seti asla buyutmez. Cok adimli is korunur:
kullanici eylem istediginde anahtar kelime tam seti BASTAN acar ("bul, sonra
kaydet" gibi), dolayisiyla meşru akislar ilk turdan itibaren tam yetkiye sahipti.

KANIT: 3 yeni test (tests/test_yetki_tavani.py) gercek mesaj_isle akisini
sahte beyinle kosar: (1) anahtarsiz soruda ikinci tur hala yalniz git_durum
gorur — duzeltme oncesi [git_durum, write_file_tool, ac_uygulama] goruyordu;
(2) anahtar kelimeli istekte tam set basta ve sonda ayni; (3) tools=None ise
dongu de None sunar. Toplam 268/268 yesil.

Bilinen sinir: "deftere yaz" gibi ifadeler anahtar kelime listesinde yok
("kaydet"/"not al" var) — bu degerler tam seti acmaz; olcum-suzugunde kalir.
Kelime listesi genisletme ayrı bir karardır (Casper'onayina sunulur).
