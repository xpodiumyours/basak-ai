"""scripts/indexnow.py — IndexNow bildirimi (hesap/uyelik GEREKMEZ).

Kullanim:
    python scripts/indexnow.py                 # varsayilan kok ile bildir
    python scripts/indexnow.py <kok>           # ornegin https://site.example
    python scripts/indexnow.py --liste         # yalniz yollari yazdirir

Anahtar dosyasi sitede YAYINDA olmali: /<anahtar>.txt (icerik = anahtar).
IndexNow; Bing, Yandex ve Seznam gibi arama motorlarina tek istekle bildirir.
"""

import json
import re
import sys
import urllib.request
from pathlib import Path

KOK_VARSAYILAN = "https://basak-vercel.vercel.app"
KOK = Path(__file__).resolve().parent.parent
if str(KOK) not in sys.path:
    sys.path.insert(0, str(KOK))


def anahtar_bul(web=KOK / "web"):
    """Anahtar dosyasi: adi 32 hex karakter ve icerigi adiyla ayni."""
    for yol in sorted(web.glob("*.txt")):
        if re.fullmatch(r"[0-9a-f]{32}", yol.stem):
            if yol.read_text(encoding="utf-8").strip() == yol.stem:
                return yol.stem
    return ""


def yollari_topla():
    """Tum bilinen site yollari (sayfalar + araclar + rehberler)."""
    from rehberler import REHBERLER
    from tools.freetools_katalog import ARACLAR
    yollar = ["/", "/araclar", "/rehber", "/bilgilendirme.html",
              "/gizlilik.html", "/cerez.html", "/sartlar.html",
              "/sorumluluk.html", "/destek.html", "/reklam-ver.html"]
    yollar += ["/araclar/%s/%s" % (k, s) for k, s in ARACLAR]
    yollar += ["/rehber/%s" % r["slug"] for r in REHBERLER]
    return yollar


def gonder(kok=KOK_VARSAYILAN):
    anahtar = anahtar_bul()
    if not anahtar:
        print("ANAHTAR-YOK: web/ altinda <32-hex>.txt "
              "anahtar dosyasi bulunamadi.")
        return 1
    temiz = kok.rstrip("/")
    adresler = [temiz + y for y in yollari_topla()]
    govde = json.dumps({
        "host": temiz.replace("https://", "").replace("http://", ""),
        "key": anahtar,
        "keyLocation": "%s/%s.txt" % (temiz, anahtar),
        "urlList": adresler,
    }).encode("utf-8")
    istek = urllib.request.Request(
        "https://api.indexnow.org/indexnow", data=govde,
        headers={"Content-Type": "application/json; charset=utf-8"})
    try:
        with urllib.request.urlopen(istek, timeout=20) as yanit:
            print("IndexNow: %s (%d adres)" % (yanit.status, len(adresler)))
            return 0
    except Exception as hata:
        print("IndexNow HATA: %s" % hata)
        return 1


if __name__ == "__main__":
    if "--liste" in sys.argv:
        for yol in yollari_topla():
            print(yol)
        raise SystemExit(0)
    kok = next((a for a in sys.argv[1:] if a.startswith("http")),
               KOK_VARSAYILAN)
    raise SystemExit(gonder(kok))
