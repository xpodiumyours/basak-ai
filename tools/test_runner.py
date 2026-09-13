"""Beyaz listedeki projelerin sabit test komutlarini calistirir."""

import os
import subprocess

from tools.olcum import PROJELER

_WIN = os.name == "nt"
KOMUTLAR = {
    "basak": ["python", "-m", "pytest", "tests", "-q"],
    "vixrex": ["flutter.bat" if _WIN else "flutter", "test", "--reporter", "expanded"],
    "numeramatch": ["npm.cmd" if _WIN else "npm", "run", "test:ci"],
    "xses": ["npm.cmd" if _WIN else "npm", "test"],
}


def testleri_kos(proje):
    """Modelden komut almadan, sabit argv ile proje testlerini kosar."""
    ad = (proje or "").strip().lower()
    kok = PROJELER.get(ad)
    komut = KOMUTLAR.get(ad)
    if kok is None:
        return {"error": "Bilinmeyen proje: %s" % ad}
    if komut is None:
        return {"error": "Bu projede test komutu tanimli degil."}

    try:
        r = subprocess.run(
            list(komut), cwd=kok, capture_output=True, text=True,
            timeout=300, shell=False, encoding="utf-8", errors="replace")
    except subprocess.TimeoutExpired:
        return {"error": "Testler 300 saniye icinde tamamlanmadi."}
    except Exception as e:
        return {"error": "Test komutu calismadi: %s" % str(e)[:160]}

    cikti = ((r.stdout or "") + ("\n" + r.stderr if r.stderr else "")).strip()
    if len(cikti) > 2000:
        cikti = "...(son 2000 karakter)\n" + cikti[-2000:]
    durum = "BASARILI" if r.returncode == 0 else "BASARISIZ"
    return {"result": "%s | cikis_kodu=%d\n%s" %
                      (durum, r.returncode, cikti or "(cikti yok)")}
