"""_olcum_arac_cagirma.py — Canli olcum: model araci GERCEKTEN cagiriyor mu?

Casper karari (2026-09-22): sozlesme guclendirildi; simdi olcum.
10 arac isteyen soru, gercek bulut zinciri, ayni mesaj_isle yolu (web/masaustu/telegram hepsi bunu kullanir).

Kosum (elle, kota harcar):
    python _olcum_arac_cagirma.py

Cikti: satir satir toolStatus olaylari + ozet (kac/10 soruda arac kostu).
"""

import json
import sys
import time

sys.path.insert(0, ".")

SORULAR = [
    ("masaustu_liste", "bilgisayarimin masasustunde ne var"),
    ("simdi_saat", "su an saat kac"),
    ("gorev_liste", "gorevlerime bak"),
    ("hafiza_ara", "hafizamda ne kayitli"),
    ("matris_liste", "matris tablolaim var mi"),
    ("hava_web", "bugun istanbulda hava nasil"),
    ("groq_ara", "groq nedir internette arastir"),
    ("git_durum", "basak-ai projesinin git durumu ne"),
    ("hesapla_yuzde", "240in yuzde 18 kac"),
    ("son_commit", "basak-ai reposunun son commitleri neler"),
]


def main():
    from basak_app import KISILIK, init_cache
    from brain import Brain
    from tools import TOOLS
    from chat.flow import mesaj_isle
    from chat import context as ctx

    init_cache()
    beyin = Brain()
    if not beyin.bulut_musait():
        print("BULUT YOK: ayarlar.json'a anahtar yaz (python doktor.py)")
        return 2

    sonuclar = []
    for ad, soru in SORULAR:
        # Her soru bagimsiz: gecmis temizlenir (misafir=False ->
        # AJAN_SOZLESMESI gonderilir; misafirde sozlesme gonderilmiyor).
        try:
            ctx.kaydet(ctx.gecmis_yolu(), [])
        except OSError:
            pass

        olaylar = []
        t0 = time.time()

        def cb(kod, _olaylar=olaylar, _ad=ad, _soru=soru):
            if not isinstance(kod, str):
                return
            if kod.startswith("BasakUI.toolStatus("):
                metin = kod[len("BasakUI.toolStatus("):-1]
                try:
                    metin = json.loads("[%s]" % metin)[0]
                except Exception:
                    pass
                _olaylar.append(str(metin))
            elif kod.startswith("BasakUI.error("):
                metin = kod[len("BasakUI.error("):-1]
                try:
                    metin = json.loads("[%s]" % metin)[0]
                except Exception:
                    pass
                _olaylar.append("ERROR: " + str(metin))
            elif kod.startswith("BasakUI.bitir("):
                _olaylar.append("BITTI")

        try:
            mesaj_isle(soru, beyin, KISILIK, cb, TOOLS, misafir=False)
        except Exception as e:
            olaylar.append("ISTISNA: %s" % e)

        sure = time.time() - t0
        gercek_arac = [o for o in olaylar if o not in ("BITTI",)
                       and not o.startswith("ERROR:")
                       and not o.startswith("ISTISNA:")]
        sonuclar.append({
            "soru": ad,
            "metin": soru,
            "arac_kostu": bool(gercek_arac),
            "olaylar": olaylar,
            "sure_sn": round(sure, 1),
        })
        durum = "ARAC VAR" if gercek_arac else "ARAC YOK"
        print("[%s] %s (%.1f sn) -> %s" % (
            durum, ad, sure,
            " | ".join(olaylar) if olaylar else "hic olay yok"))

    kostu = sum(1 for s in sonuclar if s["arac_kostu"])
    toplam = len(sonuclar)
    print("\n=== OZET ===")
    print("Arac kostu: %d/%d (%%%d)" % (kostu, toplam, round(100 * kostu / toplam)))
    print("Aracsiz kalan:")
    for s in sonuclar:
        if not s["arac_kostu"]:
            print("  - %s: %s | olaylar=%s" % (
                s["soru"], s["metin"], s["olaylar"]))

    with open("_olcum_arac_cagirma_sonuc.json", "w", encoding="utf-8") as f:
        json.dump(sonuclar, f, ensure_ascii=False, indent=2)
    print("\nKayit: _olcum_arac_cagirma_sonuc.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
