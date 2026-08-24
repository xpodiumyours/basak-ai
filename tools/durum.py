"""tools/durum.py — DURUM.md üreticisi (denetim 2026-08-24).

Ilke: rakamlari belgelere ELLE gömmek bayatlamaya mahkumdur. Bu modul
gercegi OLÇUP kök dizindeki DURUM.md'yi üretir. Kimse eliyle
güncellemez; güncellemek icin komutu tekrar koşturmak yeter:

    python -m tools.durum

Ölçümler:
- test sayisi      : tests/ altindaki `def test_` tanimlari (statik sayim;
                     pytest'in parametrize ile urettigi vaka sayisi daha
                     yüksek olabilir)
- arac sayisi      : tools.permissions.ETIKETLER tablosu
- saglayici sayisi : brain.registry.SAGLAYICILAR kartlari
- son commit       : git log -1

Belge sagligi testi (tests/test_belge_sagligi.py) bu olcumleri DURUM.md
ile karsilastirir; gercek degisirse test KIRMIZI yanar — belge artik
yanlis soyluyorsa bunu kod degil, TEST soyler.
"""

import os
import re
import subprocess
from datetime import datetime

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DURUM_YOLU = os.path.join(BASE, "DURUM.md")


def test_sayisi(tests_dir=None):
    """tests/ altindaki test fonksiyonu tanimlarini statik sayar."""
    n = 0
    kok = tests_dir or os.path.join(BASE, "tests")
    for dizin, _, dosyalar in os.walk(kok):
        if "__pycache__" in dizin:
            continue
        for d in dosyalar:
            if not (d.startswith("test_") and d.endswith(".py")):
                continue
            with open(os.path.join(dizin, d), "r", encoding="utf-8",
                      errors="replace") as f:
                n += len(re.findall(r"^\s*def test_", f.read(), re.M))
    return n


def arac_sayisi():
    from tools.permissions import ETIKETLER
    return len(ETIKETLER)


def saglayici_ozeti():
    from brain.registry import SAGLAYICILAR
    bulut = [a for a in SAGLAYICILAR if a != "yerel"]
    ucretli = [a for a, k in SAGLAYICILAR.items()
               if not k.get("ucretsiz", True)]
    return len(bulut), len(ucretli)


def son_commit():
    try:
        cikti = subprocess.run(
            ["git", "log", "-1", "--format=%h %ad", "--date=short"],
            cwd=BASE, capture_output=True, text=True, timeout=10,
        ).stdout.strip()
        return cikti or "-"
    except (OSError, subprocess.SubprocessError):
        return "-"


def olc():
    """Zaman damgasi tasimayan olcum sozlugu dondurur (test karsilastirmasi
    icin deterministik)."""
    bulut_adet, ucretli_adet = saglayici_ozeti()
    return {
        "test": test_sayisi(),
        "arac": arac_sayisi(),
        "bulut": bulut_adet,
        "ucretli": ucretli_adet,
        "commit": son_commit(),
    }


def uret(olcum=None, simdi=None):
    o = olcum or olc()
    zaman = simdi or datetime.now().strftime("%Y-%m-%d %H:%M")
    satirlar = [
        "# DURUM — otomatik ölçüm",
        "",
        "> Bu dosya ELLE yazılmaz: `python -m tools.durum` üretir.",
        "> Rakamlar burada GERÇEKTEN ölçülür; başka hiçbir belgede sayı",
        "> taahhüt edilmez. Belgelerle çelişirse DURUM.md doğrudur.",
        "",
        "| Ölçü | Değer | Ölçüm yöntemi |",
        "|---|---|---|",
        "| Test fonksiyonu | %d | `tests/` altındaki `def test_` sayısı |"
        % o["test"],
        "| Araç | %d | `tools/permissions.py` ETIKETLER tablosu |"
        % o["arac"],
        "| Bulut sağlayıcı | %d (%d ücretli) | `brain/registry.py` kartları |"
        % (o["bulut"], o["ucretli"]),
        "| Son commit | %s | `git log -1` |" % o["commit"],
        "",
        "_Son ölçüm: %s_" % zaman,
        "",
    ]
    return "\n".join(satirlar)


def yaz():
    icerik = uret()
    with open(DURUM_YOLU, "w", encoding="utf-8") as f:
        f.write(icerik)
    return icerik


if __name__ == "__main__":
    print(yaz())
