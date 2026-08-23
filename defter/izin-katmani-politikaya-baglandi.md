---
kim:    opencode
tarih:  2026-08-23
konu:   Izin katmani gercek kontrol oldu (etiket artik politika)
tip:    karar
omur:   sonsuz
kaynak: kod incelemesi + tests/test_izin_politikasi.py
---

Casper'in buldugu ikinci guvenlik boslugu: permissions.py etiketler koyuyor
(yazma/internet/sistem) ama izinli_mi() yalnizca "arac tabloda var mi" diye
bakiyor; tum tanimli araçlar tablada oldugu icin etiket HICBIR sey zorunlu
kilmiyordu. ac_uygulama (sistem) otomatik kosabiliyordu.

Cozum (`tools/permissions.py` + `tools/executor.py`): etikete bagli politika
tablosu eklendi, executor artik calistirilabilir_mi() ile BU ANKI izne bakar:
- salt-okunur / internet / yazma -> otomatik (gunluk kullanim bozulmaz)
- sistem -> opt-in: VARSAYILAN KAPALI; ayarlar.json'da
  "sistem_araclari_acik": true dediginde acilir
- hassas -> onay ister (boyle arac su an yok; P4/P6 onay kuyusu icin durur)
- etiketsiz -> yasak (eski davranis korundu)

Engellenen arac modelye anlasilir hata dondurur ("varsayilan kapali, Casper
acabilir"), arac.log'a "izin engeli" yazilir.

KANIT: 10 yeni test (tests/test_izin_politikasi.py): varsayilan ayarla
executor'dan ac_uygulama cagrildiginda uygulama baslatma fonksiyonuna hic
ulasilmadigi monkeypatch ile kanitlandi; anahtar acilinca politika izin
verir; BOM'lu ayar dosyasi okunur (D-2). Toplam 278/278 yesil.

Bilinen sinir: "onay" politikasi henüz kullanıcı sorusu sormuyor — onay
kuyusu P4/P6 fazının isi; o gelene kadar hassas etiketli arac yok.
