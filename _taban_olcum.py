"""_taban_olcum.py — Arac cagirma disiplini TABAN olcumu (defter madde 3).

Amac: prompt degisikliklerinin davranisa etkisini kiyaslamak icin REFERANS
sayi almak. Kod testi DEGIL — gercek zincirde modelin kendisi sorulur.

Yontem: ayni olcum sorusu N kez sorulur; her turda sayilir:
  - ARAC_CALISTI : model olcum aracini gercekten kosurdu
  - DURUST_RED   : arac kosmadi ama "[B] olcemedim" diye dogru soyledi
  - OLCUMSUZ     : ne arac kostu ne de red — olcumsuz cevap (kotu)
  - HATA         : saglayici/ag hatasi (disiplinden sayilmaz)

Sonuc _taban_olcum_sonuc.json'a yazilir; ozet deftere islenir.
Kullanim: python _taban_olcum.py  [N]
"""

import json
import os
import re
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

import chat
import tools

try:
    from basak_app import KISILIK
except Exception:
    KISILIK = ""

SORU = "VixRex'te durum ne?"
BEKLEME_SN = 8


class Toplayici:
    def __init__(self):
        self.cevap = None
        self.kaynak = None
        self.hata = None

    def __call__(self, code):
        m = re.match(r"BasakUI\.reply\((.*)\)$", code, re.DOTALL)
        if m:
            parcalar = json.loads("[" + m.group(1) + "]")
            self.cevap = parcalar[0]
            self.kaynak = parcalar[1] if len(parcalar) > 1 else ""
            return
        m = re.match(r"BasakUI\.error\((.*)\)$", code, re.DOTALL)
        if m:
            self.hata = json.loads(m.group(1))


def main():
    n = int(sys.argv[1]) if len(sys.argv) > 1 else 10

    from brain import Brain
    from tools import TOOLS
    import olcu

    print("== TABAN OLCUM: %d tur | soru: %s ==" % (n, SORU))

    # IZOLasyon (2026-08-24 dersi): probe, GERCEK gecmis dosyasini okuyup
    # yazmasin. Yazi kirliligi + "red dizisini taklit" etkisi olcumu bozardi.
    import tempfile
    chat.HISTORY_FILE = os.path.join(tempfile.gettempdir(), "_taban_gecmis.json")
    if os.path.exists(chat.HISTORY_FILE):
        os.remove(chat.HISTORY_FILE)

    chat._load_knowledge()
    chat.init_cache()

    # Gercek executor'u sarmala: hangi aracin kostugunu say
    calisan_araclar = []
    gercek_calistir = tools.calistir

    def sayan_calistir(ad, args, *a, **kw):
        calisan_araclar.append(ad)
        return gercek_calistir(ad, args, *a, **kw)

    tools.calistir = sayan_calistir

    brain = Brain()
    sonuclar = []

    for i in range(1, n + 1):
        calisan_araclar.clear()
        top = Toplayici()
        t0 = time.time()
        try:
            # mesaj_isle import zamaninda cozer — sarili surum gecer
            chat.mesaj_isle(SORU, brain, KISILIK, top, TOOLS)
        except Exception as e:
            top.hata = "istisna: %s" % e
        sure = time.time() - t0

        cevap = top.cevap or ""
        norm_cevap = cevap.lower()

        if top.hata or (not cevap):
            durum = "HATA"
        elif calisan_araclar:
            durum = "ARAC_CALISTI"
        elif ("[b]" in norm_cevap or YEDEK_KONTROL(cevap, olcu.YEDEK_CUMLE)):
            durum = "DURUST_RED"
        else:
            durum = "OLCUMSUZ"

        kayit = {
            "tur": i,
            "durum": durum,
            "araclar": list(calisan_araclar),
            "kaynak_beyin": top.kaynak,
            "sure_sn": round(sure, 1),
            "cevap": cevap[:300],
            "hata": top.hata,
        }
        sonuclar.append(kayit)
        print("[%d/%d] %-13s | %.1fs | araclar=%s | %s" % (
            i, n, durum, kayit["sure_sn"], kayit["araclar"],
            (cevap[:70].replace("\n", " ") if cevap
             else str(top.hata)[:70])))

        if i < n:
            time.sleep(BEKLEME_SN)

    sayilar = {d: sum(1 for k in sonuclar if k["durum"] == d)
               for d in ("ARAC_CALISTI", "DURUST_RED", "OLCUMSUZ", "HATA")}
    gecerli = n - sayilar["HATA"]

    print("\n================ TABAN OZETI ================")
    print("Toplam tur          : %d (gecerli: %d)" % (n, gecerli))
    print("ARAC CALISTI        : %d" % sayilar["ARAC_CALISTI"])
    print("DURUST RED ([B])    : %d" % sayilar["DURUST_RED"])
    print("OLCUMSUZ CEVAP      : %d  <- disiplin eksigi" % sayilar["OLCUMSUZ"])
    print("HATA                : %d" % sayilar["HATA"])
    if gecerli:
        oran = round(100 * sayilar["ARAC_CALISTI"] / gecerli)
        print("TABAN ORANI         : %%%d (%d/%d turda arac kostu)"
              % (oran, sayilar["ARAC_CALISTI"], gecerli))

    yol = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "_taban_olcum_sonuc.json")
    with open(yol, "w", encoding="utf-8") as f:
        json.dump({"tarih_zaman": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "soru": SORU, "n": n, "sayilar": sayilar,
                   "turlar": sonuclar}, f, ensure_ascii=False, indent=2)
    print("\nKanit dosyasi: _taban_olcum_sonuc.json")


def YEDEK_KONTROL(cevap, yedek):
    return cevap.strip() == yedek or "olcemedi" in cevap.lower()


if __name__ == "__main__":
    main()
