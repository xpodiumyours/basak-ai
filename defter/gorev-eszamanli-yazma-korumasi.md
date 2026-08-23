---
kim:    opencode
tarih:  2026-08-24
konu:   Gorev dosyasinda eszamanli yazma korumasi
tip:    karar
omur:   sonsuz
kaynak: tools/tasks.py + tests/test_gorev_eszamanlilik.py
---

Casper'in bulgusu dogrulandi: Api.mesaj() her mesaji ayri thread'de
kosturuyor; add_task/complete_task ise gorevler.json'u oku-degitir-tumuyle-
yaz yapiyordu ve KILITSIZDI. Iki islem cakisirsa:
- ayni ID uretimi (ikisi de len+1 okur)
- son yazan kazanir -> digerinin ekledigi/duzelttigi kayit KAYBOLUR
- yarim yazma aninda okuyan taraf bozuk JSON'a takilabilir

Cozum (`tools/tasks.py`):
1. _KILIT (threading.Lock): add_task ve complete_task'in oku-degitir-yaz
   bolumlerini sarar. Tek Python surecindeki tum yazicilar icin yeterlidir
   (coklu surec yazicisi yok).
2. ID uretimi max(mevcut)+1 — len+1'in kirilganligi giderildi.
3. _atomik_yaz: once .tmp'e yaz, os.replace ile tek hamlede degistir.
   Ayni surucude atomiktir; baska thread'ler yarim JSON asla goremez.
   list_tasks/reminders gibi okuyucular da boylece guvende.

KANIT: 3 yeni test (tests/test_gorev_eszamanlilik.py): 10 thread barierle
paralel ekleme -> 10 kayit, ID'ler 1..10 benzersiz sirali; ekleme+tamamlama
karisik yarista hic istisna yok ve mukerrer ID yok; .tmp artigi birakilmaz.
Toplam 371/371 yesil.

Bilinen sinir: kilit sadece bu sureci kapsar — gelecekte coklu surec
yazicisi (orn. ayri bir servis) eklenirse dosya kilidine (msvcrt.locking)
gecilmesi gerekir; simdiki mimaride gerek yok.
