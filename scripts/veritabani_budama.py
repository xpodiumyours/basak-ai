"""Eski kosularin agir kayitlarini siler (veritabani kotasi dolu kalmasin).

Kullanim (proje kokunden):
    python scripts/veritabani_budama.py [gun]

Varsayilan 14 gun. Silinen: o kosunun olaylari, yapaylari ve arac sonuc
govdeleri. Kalan: kosu satiri ve "hangi arac, basarili mi" denetim kaydi.
"""
import json
import os
import sys

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if KOK not in sys.path:
    sys.path.insert(0, KOK)

from chat.platform_runtime import RuntimeStore  # noqa: E402


def main(argv):
    gun = int(argv[1]) if len(argv) > 1 else 14
    try:
        sayi = RuntimeStore().budama(gun)
    except Exception as exc:  # depo yoksa sessiz kalmak yerine soyle
        print("Budama yapilamadi: " + str(exc)[:200])
        return 1
    print(json.dumps({"gun": gun, **sayi}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
