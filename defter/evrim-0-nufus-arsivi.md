---
kim:    opencode
tarih:  2026-08-24
konu:   EVRIM-0 tamamlandi — hipotez havuzu + nufus arsivi
tip:    karar
omur:   sonsuz
kaynak: tools/evrim.py + tests/test_evrim.py
---

Kilitli hedefin "Evrim Motoru" organinin ilk halkasi: Darwin Gödel
Machine / AlphaEvolve yaklasimindaki NUFUS ARSIVI modeli.

Yapilar (`tools/evrim.py`):
- Arsiv: her hipotez {id, icerik, puan, olcum, nesil, ebeveynler, durum}
- Durumlar: yeni -> test_edildi -> hayatta | elenmis (SILME YOK —
  elenenler kanit zinciri olarak arsivde kalir)
- kombinasyon(a, b, yeni): iki hipotezin guclu yanlari birlesir,
  cocuk nesil = max+1
- mutasyon(id, yeni_icerik): kaynak varyantin devam varyanti
- evrim_turu(): uret -> degerlendir (DENEY-0 motoru sarmalanir) ->
  hayatta_kalanlar(limit) -> kalanmayanlari 'elenmis' isaretle

Kritik ayrim: puan LLM'in sozunden DEGIL, deney motorunun olcumunden
gelir (DENEY-0 ile baglantili; uretimde degerlendirici sarmalayici
deney_yurut'u cagiracak).

KANIT: 9 yeni test (tests/test_evrim.py): ekle/puanla/sirali en-iyiler,
kombinasyonda ebeveyn+nesil takibi, mutasyon, eleme dongusunde en iyilerin
hayatta kaliplarinin elenmis isaretlenmesi (6 aday -> 2 hayatta + 4
elenmis), dosyadan yeniden acilis kaliciligi, .tmp artigi yok.
Toplam 467/467 yesil.

Bilinen sinir: uretici ve degerlendirici stratejileri su an cagiranin
verdigi fonksiyonlar; bunlarin ORKESTRA durumlarina (HYPOTHESIZE/
EXPERIMENT) baglanmasi bir sonraki dilimdir.
