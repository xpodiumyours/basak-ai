---
kim:    opencode
tarih:  2026-08-24
konu:   Baglam diyeti ADIM 2 — kilavuz sikilastirma (dogrulama yarim)
tip:    olcum
omur:   30g
kaynak: tools/definitions.py + _taban_olcum provalari + audit.log
---

Adim 2: `tools/definitions.py` aciklamalari kisa emirlere indirildi. Isim ve
parametre yapisi AYNEN korundu; yalniz metin kisaldi.

KESIN KAZANC (deterministik, olculmus):
- Tam set JSON : 8.384 -> 5.780 karakter (%31 az)
- Olcum sorusu dinamik seti: 1.517 -> 1.049 karakter
- Testler: 303/303 yesil

DAVRANIS DOGRULAMASI BELIRSIZ — olcum yontemi hatasi bulundu:
Ayni gece uc probe kosuldu: %80 (adim1 kodu) -> %50 (adim2, 1. kosu) ->
%0 (adim2, 2. kosu). %0 turunun teshisi:
1. groq 429 sonrasi sogumadaydi (~26 dk), HER TUR atlandi
2. 10 turun HEPSINI glm cevapladı; glm'in modeli bu soruda arac cagirmadi
3. Gecmis dosyasinda biriken 20 "Bunu olcemedim" cifti model tarafindan
   taklit edildi (kalip devami)
Yani oranlar buyuk olcude HANGI SAGLAYICININ cevapladigini olcuyordu,
prompt degisikligini degil. n=10 ardısık tur saglayici turbulansinde
kiyaslama icin yetersiz.

YONTEM DUZELTMELERI (yapildi):
- _taban_olcum.py artik IZOLE gecmis dosyasi kullanir (gercek gecmise
  yazmaz/okumaz); kaynak_beyin artik yakalanir
- gecmis.json'daki probe kirliligi temizlendi (yedek: gecmis.json.yedek-probe)

KARAR: Adim 2 kodu dursun (kazanc kesin, testler yesil); davranis etkisinin
kesin hukmu YARIN taze kotalarla (groq sogumasi bitmis, bos gecmisle)
ayni probe ile verilecek. %30 tabanin altina inerse geri alinir.
