"""scripts/kullanici_ekle.py — Web kullanıcı ekleme (interaktif).

Kullanım (proje kökünden):
    python scripts/kullanici_ekle.py

Ad + şifre sorar; şifre düz metin DEĞİL pbkdf2 hash olarak
data/kullanicilar.json'a yazılır. Script'e sabit şifre KOYMAZ.
"""

import getpass
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)

import kullanici  # noqa: E402
from chat.kimlik import slugla  # noqa: E402


def main():
    print("Basak web kullanicisi ekle")
    ad = (input("Kullanici adi (orn. ayse): ") or "").strip()
    if not ad:
        print("Ad bos olamaz.")
        return 1
    sifre = getpass.getpass("Sifre: ")
    if not sifre:
        print("Sifre bos olamaz.")
        return 1
    tekrar = getpass.getpass("Sifre (tekrar): ")
    if sifre != tekrar:
        print("Sifreler ayni degil.")
        return 1

    slug = slugla(ad)
    if slug in kullanici.kullanici_listesi():
        cevap = input("'%s' zaten var. Guncellensin mi? [e/H]: " % slug)
        if cevap.strip().lower() not in ("e", "evet", "y"):
            print("Vazgildin.")
            return 1
        sonuc = kullanici.kullanici_ekle(ad, sifre, varsa_guncelle=True)
    else:
        sonuc = kullanici.kullanici_ekle(ad, sifre)

    if sonuc == "sifre bos olamaz":
        print(sonuc)
        return 1
    print("Tamam: %s" % sonuc)
    print("Artik web girisi zorunlu. Giris: POST /api/giris")
    return 0


if __name__ == "__main__":
    sys.exit(main())
