---
kim:    opencode
tarih:  2026-08-24
konu:   ORKESTRA-0 tamamlandi — muhakeme cekirdegi iskeleti
tip:    karar
omur:   sonsuz
kaynak: brain/orkestra.py + defter/orkestra-0-tasarim.md + tests/test_orkestra.py
---

Kilitli hedefin merkezi yerlesti: `brain/orkestra.py` — 10 durumlu
(OBSERVE..LEARN) muhakeme cercevesi.

Tasarim ilkeleri (orkestra-0-tasarim.md):
1. mesaj_isle yeniden yazilmadi; Orkestra dogrulanmis parcalari durumlarina
   baglayan ENJEKTE EDILEBILIR cercevedir (11 bilesen disaridan girer).
2. Her kosum IZ birakir: {durum, atlandi, sebep, ozet} — sessiz atlama yok.
3. v0 davranisi bugunku akisla esdeger; DIVERSIFY/CRITICIZE bilinclì
   atlanir ve sebebi yazilir ("FAY-1 bekleniyor").
4. Uretim anahtari SONRA: once gölge mod/eşdeğerlik kanıtı, sonra ana yol.
5. LEARN yalnizca olcuden gecen cevapta calisir.

KANIT: 8 yeni test (tests/test_orkestra.py): tam iz dizilimi
(OBSERVE..LEARN sirali), atlama sebepleri izde yazili, arac cagrisinda
EXPERIMENT'in gercekten kostugu ve MEASURE'un ham olcum fallback'ini
devraldigi, LEARN'un tek kez kostugu, bos soruda erken donus, aday uretici
hatasinin rapora dustugu, eksik bilesen reddedilmesi.
Toplam 437/437 yesil.

Sonraki dilimler: gölge mod üretim denemesi (eşdeğerlik kanıtı) ->
ana yol geçisi -> DIVERSIFY'i FAY-1 jürisine baglama.
