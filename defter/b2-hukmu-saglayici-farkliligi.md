---
kim:    opencode
tarih:  2026-08-24
konu:   B2 hukmu + Kilo bulgusu — saglayici bazli disiplin farki olculdu
tip:    olcum
omur:   30g
kaynak: _taban_olcum.py 10 tur (izole gecmis) + kaynak dagilimi analizi
---

Bekleyen-isler maddeleri 2 ve 4'un olcumu (baglam diyeti Adim 2 hukmu ile
birlikte).

SONUC (ayni soru x 10 tur, izole gecmis):
- groq   : 1 tur  -> ARAC_CALISTI (%100)
- glm    : 1 tur  -> DURUST_RED
- nvidia : 8 tur  -> 3 ARAC_CALISTI, 3 DURUST_RED, 2 OLCUMSUZ
- kilo   : 0 tur  -> hic devralmadi

TOPLAM DISIPLIN: %40 (Adim 1'deki tek-kosum %80 ile kiyasla dusuk;
AMA asil bulgu saglayici bazinda buyuk fark olmasi)

BULGU A — SAGLAYICI FARKLILIGI GERCEK VE OLCULUR:
Ayni prompt, ayni arac seti -> davranis hangi modelin cevapladigina gore
degisiyor. Bu dogrudan B1 karne katmanini dogruluyor: secicinin
saglayici basina DISIPLIN verisi biriktirmesi gerekli ve mumkun.
Not: nvidia 8 turla agir yuk tasidi; orneklem kucuk ama yon net.

BULGU B — KILO HIC DEVRALMIYOR (madde 4):
Juri sirasinda en genis kontingentli kilo, zincir siralamasi nedeniyle
hic oyuna gelmiyor. Secici sirasi gozden gecirilmeli (Casper karari).

BULGU C — 2 OLCUMSUZ TURun icerigi: model, olcmedigi halde "hassas
anahtarlarin guvenli depolamasi" gibi PLAUZIBIL ama olculmemis icerik
uretti — hafiza/baglam ezbiri. Tam da [B]-eylem denetiminin yakaladigi
turden; kapı bunlari YAKALADI (kullaniciya ulasmadi), ama disiplin
eksigi olarak kayda gecti.

SONUC: Baglam diyeti Adim 2'nin kodu yerinde kaliyor (regresyon yok);
disiplin verisi artik SAGLAYICI BAZINDA birikiyor — B1 karne katmani
bu veriyle beslenecek sekilde tasarlandi.

Kalan borclar: Kilo sira mantigi degerlendirmesi (Casper), EVRIM-1
DIVERSIFY baglantisi.
