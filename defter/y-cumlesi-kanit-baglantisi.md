---
kim:    opencode
tarih:  2026-08-23
konu:   Y cumlesi kanit baglantisi (sozcuk capasi)
tip:    karar
omur:   sonsuz
kaynak: kod incelemesi + tests/test_y_baglantisi.py
---

Casper'in buldugu dorduncu acik: [Y] cumlesi, cevapta HERHANGI bir [Ö]/[A]
ayakta kaldigi surece geciyordu — kod baglantiyi GLOBAL bayrakla kontrol
ediyordu, cumle bazinda degil. Gercek bir git ciktisinin altina alakasiz
bir iddia "[Y]" rozetiyle sizabiliyordu.

Cozum (`olcu.py`): kapı semantik anlamaz ama sozcuk capasi denetleyebilir.
Hayatta kalan [Ö] varsa her [Y], o olcum alintisiyla en az bir icerik kokku
paylasmali (Turkce ek toleransli: dal ↔ dalinda; hash de capas olur).
Paylasmayan [Y] "kanitla baglantisi yok" gerekcesiyle elenir.

Sinir bilincli dar tutuldu: salt-[A] durumunda capas ARA NM AZ — cunku
alinti belgeyi kanitlar, iddia baglamdaki genis notlardan gelebilir
(test_olcu.py'deki Caykur sozlesmesi korundu). Olcum duserse eski kural:
tum [Y] dusler.

KANIT: 7 yeni test (tests/test_y_baglantisi.py): alakasiz [Y] elendi;
kok eslesmesi (dal/dalinda) ve hash capasi gecti; karisik cevabda sadece
baglis [Y] hayatta kaldi; salt-[A] serbestisi korundu. Mevcut tum testler
bozulmadan gecti (63/63 olcu ailesi). Toplam 294/294 yesil.

Bilinen sinir: capas tek ortak jenerik sozcukle de saglanabilir ("dosya"
gibi) — tam semantik denetim degil, kacinilir riskin kucultulmusu.
