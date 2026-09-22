"""_olcum_arac_cagirma2.py — 2. tur olcum: farkli sorularla %80 dogrulama.

Casper karari (2026-09-22): 1. tur 8/10 (%80) cikti. Ayni oran farkli
sorularda tekrarlanir mi? 1. turdaki sorularin HICBIRI tekrarlanmaz.

Kosum (elle, kota harcar):
    python _olcum_arac_cagirma2.py
"""

import json
import sys
import time

sys.path.insert(0, ".")

SORULAR = [
    ("klasor_bilgi", "basak-ai klasorunde kac tane python dosyasi var"),
    ("dosya_oku", "basak-ai reposundaki requirements.txt icinde ne yaziyor"),
    ("icerik_ara", "basak-ai kodunda AJAN_SOZLESMESI nerede tanimli"),
    ("belge_ara", "basak-ai projesinde chatbot yasagi ne diyor"),
    ("adres_kontrol", "https://basak-vercel.vercel.app/ acik mi kontrol et"),
    ("site_ara", "site:github.com xpodiumyours basak-ai"),
    ("gorsel_ara", "kedi fotografi ara"),
    ("kitap_ara", "yapay zeka kitaplari ara"),
    ("gorev_ekle", "bir test gorevi ekle: olcum turu2"),
    ("saglik", "basak'in saglik raporu ne durumda"),
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
        print("BULUT YOK")
        return 2

    sonuclar = []
    for ad, soru in SORULAR:
        try:
            ctx.kaydet(ctx.gecmis_yolu(), [])
        except OSError:
            pass

        olaylar = []
        t0 = time.time()

        def cb(kod, _olaylar=olaylar):
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
    print("\n=== OZET TUR 2 ===")
    print("Arac kostu: %d/%d (%%%d)" % (
        kostu, toplam, round(100 * kostu / toplam)))
    print("Aracsiz kalan:")
    for s in sonuclar:
        if not s["arac_kostu"]:
            print("  - %s: %s | olaylar=%s" % (
                s["soru"], s["metin"], s["olaylar"]))

    with open("_olcum_arac_cagirma2_sonuc.json", "w", encoding="utf-8") as f:
        json.dump(sonuclar, f, ensure_ascii=False, indent=2)
    print("\nKayit: _olcum_arac_cagirma2_sonuc.json")
    return 0


if __name__ == "__main__":
    sys.exit(main())
