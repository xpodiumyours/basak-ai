"""_eval_probe.py - Eval soru bankasinin GERCEK zincirde kosulmasi (FAZ 0.1).

tests/eval/sorular.json'daki her soru izole gecmisle bir kez sorulur;
sonuclar tests/eval/sonuc.json'a yazilir, metrikler tests/eval/puanla ile
hesaplanir. Bu sayilar FAZ 1'in "gerileme yok" citasidir (ANA-PLAN.md).

Kullanim: python _eval_probe.py  [soru_id...]
"""

import json
import os
import re
import sys
import tempfile
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
try:
    sys.stdout.reconfigure(encoding="utf-8")
except Exception:
    pass

from tests.eval import puanla

BEKLEME_SN = 6


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
    istenen = set(sys.argv[1:])
    sorular = [s for s in puanla.yukle()
               if not istenen or s["id"] in istenen]

    import chat
    import tools

    try:
        from basak_app import KISILIK
    except Exception:
        KISILIK = ""

    from brain import Brain
    from tools import TOOLS
    import olcu

    print("== EVAL PROVasi: %d soru ==" % len(sorular))

    chat._load_knowledge()
    chat.init_cache()

    calisan_araclar = []
    gercek_calistir = tools.calistir

    def sayan_calistir(ad, args, *a, **kw):
        calisan_araclar.append(ad)
        return gercek_calistir(ad, args, *a, **kw)

    tools.calistir = sayan_calistir

    brain = Brain()
    kayitlar = []

    for i, s in enumerate(sorular, 1):
        chat.HISTORY_FILE = os.path.join(
            tempfile.gettempdir(), "_eval_gecmis_%s.json" % s["id"])
        if os.path.exists(chat.HISTORY_FILE):
            os.remove(chat.HISTORY_FILE)

        calisan_araclar.clear()
        top = Toplayici()
        t0 = time.time()
        try:
            chat.mesaj_isle(s["soru"], brain, KISILIK, top, TOOLS)
        except Exception as e:
            top.hata = "istisna: %s" % e
        sure = time.time() - t0

        cevap = top.cevap or ""
        norm_cevap = cevap.lower()

        if top.hata or not cevap:
            durum = "HATA"
        elif calisan_araclar:
            durum = "ARAC_CALISTI"
        elif ("[b]" in norm_cevap or olcu.YEDEK_CUMLE in cevap.strip()
              or "olcemedi" in norm_cevap):
            durum = "DURUST_RED"
        elif s["kategori"] in ("kod", "sohbet"):
            durum = "SERBEST"
        else:
            durum = "OLCUMSUZ"

        kayit = {
            "id": s["id"],
            "kategori": s["kategori"],
            "durum": durum,
            "araclar": list(calisan_araclar),
            "kaynak_beyin": top.kaynak,
            "sure_sn": round(sure, 1),
            "cevap": cevap[:400],
            "hata": top.hata,
        }
        kayitlar.append(kayit)
        print("[%d/%d] %s %-13s | %.1fs | araclar=%s | %s" % (
            i, len(sorular), s["id"], durum, kayit["sure_sn"],
            kayit["araclar"],
            (cevap[:70].replace("\n", " ") if cevap
             else str(top.hata)[:70])))

        if i < len(sorular):
            time.sleep(BEKLEME_SN)

    metrikler = puanla.puanla(kayitlar, sorular)
    print("\n=============== EVAL OZETI ===============")
    print("\n".join(puanla.rapor(metrikler)))

    yol = os.path.join(os.path.dirname(os.path.abspath(__file__)),
                       "tests", "eval", "sonuc.json")
    with open(yol, "w", encoding="utf-8") as f:
        json.dump({"tarih_zaman": time.strftime("%Y-%m-%d %H:%M:%S"),
                   "metrikler": metrikler, "kayitlar": kayitlar},
                  f, ensure_ascii=False, indent=2)
    print("\nKanit dosyasi: tests/eval/sonuc.json")


if __name__ == "__main__":
    main()
