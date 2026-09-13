"""tools/testkos.py — Test kosturma (Is 8, kod CALISTIRAN tek arac).

Guvenlik kodda sabittir, model degistiremez:
- Komut modelden GELMEZ: asagidaki sabit tablodan alinir.
- shell=False; Windows'ta npm icin sabit COMSPEC uzerinden `cmd /c`.
- timeout=300; cikti son 2000 karakter.
- Calisma dizini proje koku; baska dizinde kosmaz.
- vixrex YOK (Casper yasagi): bu projede tanimli degil doner.
"""

import logging
import os
import subprocess
import sys

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

_COMSPEC = os.environ.get("COMSPEC", r"C:\Windows\System32\cmd.exe")

# Komut tablosu — depolardan olculdu (2026-09-13):
# basak: pytest (dogrulandi) · numeramatch: "test": "jest" ·
# xses: "test": "vitest run". vixrex KASITLI yok (islem yasagi).
TEST_KOMUTLARI = {
    "basak": {
        "kok": BASE,
        "argv": [sys.executable, "-m", "pytest", "tests", "-q"],
    },
    "numeramatch": {
        "kok": r"C:\Users\Casper\source\NumeraMatch",
        "argv": [_COMSPEC, "/c", "npm", "test"],
    },
    "xses": {
        "kok": r"C:\Projects\xses",
        "argv": [_COMSPEC, "/c", "npm", "test"],
    },
}

_TEST_TIMEOUT = 300
_CIKTI_TAVAN = 2000


def testleri_kos(proje, runner=None):
    """Sabit tablodaki test komutunu proje kokunde kosturur."""
    ad = (proje or "").strip().lower()
    kayit = TEST_KOMUTLARI.get(ad)
    if kayit is None:
        return {"error": ("Bu projede test komutu tanimli degil: '%s'. "
                          "Tanimli: %s." % ((proje or ""),
                                            ", ".join(sorted(TEST_KOMUTLARI))))}
    run = runner or subprocess.run
    try:
        r = run(list(kayit["argv"]), cwd=kayit["kok"],
                capture_output=True, text=True,
                timeout=_TEST_TIMEOUT, shell=False,
                encoding="utf-8", errors="replace")
    except Exception as e:
        return {"error": "Test kosulamadi: %s" % e}
    cikti = ((r.stdout or "") + ("\n" + r.stderr if r.stderr else "")).strip()
    if len(cikti) > _CIKTI_TAVAN:
        cikti = "...(bas kisaltildi)\n" + cikti[-_CIKTI_TAVAN:]
    durum = "gecti" if r.returncode == 0 else \
        "KALDI (kod %d)" % r.returncode
    return {"result": "proje: %s | sonuc: %s\n%s" % (ad, durum, cikti)}
