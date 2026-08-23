---
kim:    freebuff
tarih:  2026-08-22
konu:   olcu1
tip:    olcum
omur:   30g
kaynak: chat.py, tests/test_olcu1.py, pytest 112/112
---

Ö-1 (Ölçümden önce, sonra konuş) kod olarak tamamlandı. `chat.py`'de `_OLCUM_TOOLLARI` sabiti eklendi — `git_durum`, `belge_ara`, `dosya_bilgi` araçları keyword eşleşmesi beklenmeksizin her zaman modele sunuluyor. `OLCU_YONLENDIRME` promptu "ÖLÇÜM ÖNCE GELİR — ZORUNLU AKIŞ" olarak güçlendirildi. 5 yeni test yazıldı (`tests/test_olcu1.py`), 112/112 test yeşil. Bilinen sınır: measurement tool kullanmama davranışı promptla engelleniyor, yapısal olarak zorunlu kılınmıyor (prompt bağımlılığı).
