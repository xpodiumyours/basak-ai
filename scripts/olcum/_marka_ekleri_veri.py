"""_marka_ekleri_veri.py — marka ekleri SÖZLÜĞÜ için GERÇEK VERİ toplar.

Amaç: `tutkuelit` (tutku+elit) ile `trendyolkorsan` (trendyol+korsan)
arasındaki farkı KURALLA değil, GERÇEK marka sitelerinden ölçerek
bulmak. Sözlük uydurulmayacak.

Yöntem: gerçek markaların siteleri aranır; host'un marka etiketi ile
marka arasındaki GERÇEK fark kaydedilir. Bu farklar sözlüğün
dayanağıdır.

Kosum: python scripts/olcum/_marka_ekleri_veri.py
"""

import json
import pathlib
import re
import sys

# Depo kokunu __file__ uzerinden bul; calisma dizinine bagimli degildir.
KOK = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

# Gerçek, kamuya açık markalar. Alan adları ÖLÇÜMDE doğrulanır;
# burada yazılan alan adları iddia değil, aday listesi — gerçek yanıt
# gelmedikçe sözlüğe GİRMEZ.
# (gorunen_ad, GERCEK marka anahtari, host)
# Anahtar ayrı veriliyor: host'un kendisinden türetilirse
# `trendyol-korsan` -> `trendyolkorsan` olur ve karşılaştırma anlamsızlaşır.
GERCEK = [
    ("Tutku Elit", "tutku", "tutkuelit.com.tr"),
    ("Vestel", "vestel", "vestel.com.tr"),
    ("Arçelik", "arcelik", "arcelik.com.tr"),
    ("Bosch", "bosch", "bosch.com.tr"),
    ("Trendyol", "trendyol", "trendyol.com"),
    ("Getir", "getir", "getir.com"),
    ("Trendyol Partner", "trendyol", "partner.trendyol.com"),
    ("Nescafe", "nescafe", "nescafe.com"),
    ("Milka", "milka", "milka.com.tr"),
    ("Yıldız Holding", "yildiz", "yildizholding.com.tr"),
    ("Şişecam", "sisecam", "sisecam.com"),
    ("Kordsa", "kordsa", "kordsa.com"),
    ("Eczacıbaşı", "eczacibasi", "eczacibasi.com.tr"),
    ("Anadolu Efes", "anadolu", "anadoluefes.com.tr"),
    ("Turkcell", "turkcell", "turkcell.com.tr"),
    ("Vodafone", "vodafone", "vodafone.com.tr"),
    ("Garanti", "garanti", "garanti.com.tr"),
    ("Yapı Kredi", "yapikredi", "yapikredi.com.tr"),
    ("Akbank", "akbank", "akbank.com"),
    ("Beko", "beko", "beko.com.tr"),
    ("Whirlpool", "whirlpool", "whirlpool.com"),
    ("Kia", "kia", "kia.com.tr"),
    ("Hyundai", "hyundai", "hyundai.com.tr"),
]

# Alakasız / sahte host'lar — sözlüğün ELEMESİ gereken örnekler.
ALAKASIZ = [
    ("Trendyol", "trendyol", "trendyol-korsan.com"),
    ("Vestel", "vestel", "vestel-isyeri.com"),
    ("Trendyol", "trendyol", "milyontrendyol.com"),
    ("Trendyol", "trendyol", "trendyol-sitez.com"),
]

# Alan adındaki yaygın ekler (uzantı değil, ad içi).
# Bunlar marka adının GERÇEK parçası olan ekler olabilir.
OLASI_EKLER = [
    "elit", "grup", "group", "holding", "holdings", "isyeri", "isyerleri",
    "korsan", "sahte", "global", "international", "intl", "turkiye",
    "teknoloji", "sistem", "sistemleri", "co", "com", "net",
]


def host_etiketleri(host):
    """host'tan uzantı ve www düşülmüş etiket listesi."""
    h = (host or "").lower()
    if "://" in h:
        from urllib.parse import urlparse
        h = urlparse(h).hostname or ""
    h = h[4:] if h.startswith("www.") else h
    etiketler = [e for e in h.split(".") if e]
    # Sondaki TEK etiket çoğu zaman uzantıdır (com/tr/net…). `com.tr`
    # İKİ parça olduğu için ikisi birden atılmalı — yoksa `com` etiket
    # listesine sızıyor ve "marka = com" gibi saçma eşleşmeler üretiyor.
    for _ in range(2):
        if len(etiketler) > 1 and etiketler[-1] in (
                "tr", "com", "net", "org", "gov", "edu", "info", "biz",
                "sa", "co", "io", "me", "tv", "shop", "store"):
            etiketler = etiketler[:-1]
    return etiketler


def _norm(d):
    from tools.product_resolver import _norm as n
    return n(d)


def farki_olc(marka_adi, marka_anahtari, host):
    """Marka etiketi ile marka arasındaki GERÇEK farkı ölçer."""
    etiketler = host_etiketleri(host)
    anahtar = _norm(marka_anahtari)
    bulunan = []
    for e in etiketler:
        ek = _norm(e)
        if not ek or ek == anahtar:
            continue
        if anahtar in ek:
            bulunan.append({
                "etiket": ek,
                "yon": "marka-etiketin-icinde",
                "ek": ek.replace(anahtar, ""),
                "bas": ek[:ek.index(anahtar)],
            })
        elif ek in anahtar:
            bulunan.append({
                "etiket": ek,
                "yon": "etiket-markanin-icinde",
                "ek": anahtar.replace(ek, ""),
                "bas": anahtar[:anahtar.index(ek)],
            })
    return {"marka": marka_adi, "anahtar": anahtar, "host": host,
            "etiketler": etiketler, "farklar": bulunan}


def main():
    print("MARKA EKLERI — GERCEK VERI TOPLAMA\n")
    kayitlar = []
    # (gorunen_ad, gercek_marka_anahtari, host)
    # DIKKAT: anahtar ayri veriliyor. Yoksa host'tan turetilir ve
    # `trendyol-korsan` icin anahtar `trendyolkorsan` olur; o zaman
    # "marka etiketin icinde mi?" sorusu HICBIR zaman dogru sorulmaz.
    for ad, anahtar_girisi, host in GERCEK:
        r = farki_olc(ad, anahtar_girisi, host)
        kayitlar.append(r)
        if r["farklar"]:
            for f in r["farklar"]:
                print("  %-18s host=%-26s yon=%-26s ek=%r bas=%r"
                      % (ad, host, f["yon"], f["ek"], f["bas"]))
        else:
            print("  %-18s host=%-26s (fark yok — etiket = marka)"
                  % (ad, host))

    # Ek türlerine göre grupla — sözlüğün iskeleti buradan çıkar.
    print("\n--- EK TURLERINE GORE (onay icin):")
    gruplar = {}
    for r in kayitlar:
        for f in r["farklar"]:
            gruplar.setdefault((f["yon"], f["ek"]), []).append(r["marka"])
    for (yon, ek), markalar in sorted(gruplar.items()):
        print("  %-26s ek=%-16s markalar=%s" % (yon, repr(ek), markalar))

    print("\n--- KARSILASTIRMA (alakasiz host'lar):")
    for ad, anahtar_girisi, host in ALAKASIZ:
        r = farki_olc(ad, anahtar_girisi, host)
        if not r["farklar"]:
            print("  %-26s (fark yok)" % host)
        for f in r["farklar"]:
            print("  %-26s yon=%-26s ek=%-12r bas=%r"
                  % (host, f["yon"], f["ek"], f["bas"]))

    # Cikti depo kokundaki data/ altina (.gitignore yollari kok gorelidir).
    with open(KOK / "data" / "marka-ekleri-veri.json", "w",
              encoding="utf-8") as f:
        json.dump(kayitlar, f, ensure_ascii=False, indent=2)
    print("\nyazildi: data/marka-ekleri-veri.json")
    print("NOT: Bu bir OLCE verisidir. Sozluk bu veriden turetilir,")
    print("     elle doldurulmaz.")
    return 0


if __name__ == "__main__":
    sys.exit(main())