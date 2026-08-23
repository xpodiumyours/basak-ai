---
kim:    opencode
tarih: 2026-08-24
konu:   Dosya whitelist'inde path kacislari kapandi (Casper'in 3 bulgusu)
tip:    karar
omur:   sonsuz
kaynak: kod incelemesi + tests/test_path_guvenligi.py (gercek junction)
---

Casper'in buldugu uc acik (`tools/file_ops.py`):
1. KOMSU-ONEK KACISI: dis proje kontrolu `abspath(...).startswith(realpath(kok))`
   yapiyordu; ayrac yoktu. "vixrex/../vixrex2/gizli.txt" gibi BENZER ISIMLI
   komsu klasor okunabiliyordu.
2. ABSPATH/REALPATH KARISIMI: ic klasor kontrolunde abspath kullaniliyordu;
   symlink/junction cozulmuyordu. knowledge/ icine konan bir junction
   disariyi OKUTUYOR ve YAZDIRIYORDU.
3. KOD IKILEMESI: read_file/list_files yolu kontrolden SONRA kendileri
   tekrar turetiyordu — kontrol edilen yol ile acilan yol farklilasabilirdi.

Cozum: tek merkezli cozucu `_guvenli_yolu_coz`:
- tum kararlar os.path.realpath uzerinden (baglantilar cozulur)
- sinir normcase + commonpath ile (onek oyunlarina/komsu klasore kapali)
- donus artik COZULMUS mutlak yolu tasir; acan fonksiyon baska yol
  uretmez (ikileme kaldirildi)
- eski `_klasor_kontrol` iki degerli imzasi uyumluluk icin korundu

KANIT (tests/test_path_guvenligi.py, 11 test): gercek Windows junction'i
(mklink /J) knowledge/ icine kuruldu — junction'a yazim denendiginde dosyanin
disariya ULASMADIGI monkeypatch+dosya varligi kontroluyle kanitlandi;
"vixrex/../vixrex2/gizli.txt" okumasi engellendi; pozitif akislar (knowledge
oku/yaz, buyuk harf klasor, dis proje okuma/listeleme, salt-okunur yazma
yasagi) bozulmadi. Toplam 322/322 yesil.

Not: olcu.py'deki _guvenli_yol zaten realpath+ayrac ile yapiyor (onek oyunu
gecmez); kapsam disi birakildi. Bilinen sinir: kontrol-ile-acma arasi TOCTOU
yarisi hala kuramsal olarak acik (tek surecli akista pratik risk dusuk).
