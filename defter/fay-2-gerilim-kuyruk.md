---
kim:    opencode
tarih:  2026-08-24
konu:   FAY-2 tamamlandi — gerilim puani + dirdirmayan kuyruk
tip:    karar
omur:   sonsuz
kaynak: tools/gerilim.py + tests/test_fay2_gerilim.py
---

FAY-MOTORU Organ 3 kuruldu. Formul (spesifikasyondan birebir):
    gerilim = yayilma x tazelik x maliyet

- yayilma  : 0..1 (yanlis tarafa kac sey yaslanmis)
- tazelik  : yari omru 7 gunluk dusus (ustune is yapiliyorsa 1'e yakin)
- maliyet  : yerel .25 < commit .50 < birlesmis .75 < yayinda 1.00
             (yanlis taraf ne kadar ileri gitmise o kadar agir)

DIRDIRMAYAN KUYRUK kurallari:
1. Gunde EN FAZLA 1 kart; ayni gun tekrar cagri AYNI karti verir.
2. Esik (0.30) altindaki catlak GOSTERILMEZ AMA SILINMEZ — her bekleme
   gununde birikmesi artar (%10/gun carpan) ve sonunda yuzeye cikar.
   Deprem modelinin kod karsiligi.
3. cozuldu_isaretle ile catlak kapanir; silinmez, arsivde kalir.
4. Durum data/fay_kuyruk.json'da atomik yazilir (.tmp + os.replace).

KANIT: 9 yeni test (tests/test_fay2_gerilim.py): formul sinirlari,
maliyet siralamasi, tazelik dususu, birikme carpani, gunde tek kart ve
ayni-gun ayni-kart garantisi, yuksek gerilimin onceligi, cozulenin
artik cikmamasi, esik-alti catlagin gunler icinde yuzeye cikmasi
(14 gunluk simulasyon), .tmp artigi yok. Toplam 453/453 yesil.

Bilgin sinir: yayilma su an cagiran tarafin verdigi sayi; defter/hafiza
atif grafiginden otomatik hesap ORKESTRA baglantisinda eklenecek dilim.
