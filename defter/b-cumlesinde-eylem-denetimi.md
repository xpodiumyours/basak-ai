---
kim:    opencode
tarih:  2026-08-23
konu:   B cumlesinde eylem denetimi (bekleyen-isler 1. madde kapandi)
tip:    olcum
omur:   30g
kaynak: pytest tests/test_olcu2.py + canli kapi provasi
---

Bekleyen-isler sirasindaki 1. madde kapatildi: "[B] cumleleri denetlenmiyor".
Model yapmadigi isi "[B] Bu bilgi ... deftere kaydedildi" diyebiliyordu; [B]
bilmiyorum/olculemez icin tasarlandigindan kapidan icerige bakilmadan geciyordu.

Cozum (`olcu.py`): [B] cumlesi EYLEM iddiasi tasiyorsa (kaydedildi, eklendi,
silindi, gonderildi...) ilgili aracin O TURDA hatasiz kosmus oldugu aranir;
kosmadiysa cumle elenir. Ayrintilar:
- Arac-esleme tablosu baglama gore: defter->deftere_kaydet, not->save_note,
  gorev ekleme->add_task, tamamlama->complete_task, dosya yazma->write_file_tool.
- Silme/gonderme iddiasi HICBIR aracla kanitlanamaz (boyle arac yok) — her
  kosulda elenir.
- "Hata: ..." donduren arac kanit sayilmaz.
- Olumsuz eylem ("eklenmedi") iddia degildir, elenmez.
- PROMPT_BLOGU'na tek cumlelik kural eklendi (prompt sismeden).

KANIT: 13 yeni test (tests/test_olcu2.py), toplam 265/265 yesil. Gercek olay
cumlesiyle iki uclu canli prova: (1) arac hic cagirilmayan turda olay cumlesi
oldu -> kullanici "Bunu olcemedim." gordu; (2) deftere_kaydet gercekten
kositildiginda ayni cumle yasadi. Bilinen sinir: esleme kelime tabanli —
tabloya girmeyen bir eylem fiili denetimsiz gecer; arac basariyla kostu ama
islevi yarim biraktiysa (orn. dosya olusturulamadi) cikti metnine bakilmadan
kanit sayilir.
