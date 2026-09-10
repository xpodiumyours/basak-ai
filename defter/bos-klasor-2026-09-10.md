---
kim:    opencode
tarih:  2026-09-10
konu:   basak
tip:    olcum
omur:   sonsuz
kaynak: arac.log hata satirlari + canli gorev provasi + pytest (534 yesil)
---

Casper'in suphesi dogru cikti: canli iki yolda da araclara klasorler BOS gidiyordu (tool_calling_multi cagrilari knowledge_dir/gorevler_file tasimiyordu). Sonuc: gorev ekleme cokup kokte ".tmp" curufu birakiyordu, listeleme "yok" diyordu, not kaydi patliyordu; salt-okunur araclar cwd sansiyla calisiyordu. Duzeltme: flow.py iki cagri + orkestra deney_kos gercek klasorleri tasir; tasks/notes bos-yola acik hata doner; .tmp silindi. Canli kanit (gercek dosya, yedekli): ekle (yarin->2026-09-11 cozumlu) + listele calisti, dosya geri yuklendi. 4 kilit testi eklendi, 534 yesil.
