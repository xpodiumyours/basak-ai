---
kim:    freebuff
tarih:  2026-08-22
konu:   od1
tip:    olcum
omur:   30g
kaynak: tools/notes.py, tests/test_od1.py, pytest 122/122
---

OD-1 (Defter iki yön) tamamlandı. `tools/notes.py`'e `deftere_kaydet` fonksiyonu eklendi — ORTAK-DEFTER.md §3 biçiminde frontmatter (kim/tarih/tip/ömür/kaynak) + içerik yazar, `defter/INDEX.md` otomatik güncellenir. Tool 17'e çıktı, 10 yeni test yazıldı (122/122 yeşil). Artık Başak "deftere yaz" dediğinde ortak deftere kayıt düşebiliyor.
