"""tools/github.py — GitHub durumu (Is 5, salt-okunur).

Guvenlik kodda sabittir, model degistiremez:
- Depo ADI modelden gelmez: yalniz proje anahtari (basak/vixrex/
  numeramatch/xses), depo eslemesi asagidaki sabit tablodadir.
- Komutlar sabit argv, shell=False, timeout=20. Yalniz uc okuma:
  pr list / pr view / run list. merge/create/close/delete YOK.
- Kosucu enjekte edilebilir (runner) — testler agsiz kosar.
"""

import json
import logging
import subprocess

logger = logging.getLogger(__name__)

# Depo eslemesi kodda sabit (git remote'tan olculdu) — model veremez.
DEPOLAR = {
    "basak": "xpodiumyours/basak-ai",
    "vixrex": "xpodiumyours/vixrex",
    "numeramatch": "xpodiumyours/NumeraMatch",
    "xses": "xpodiumyours/xses",
}

_DURUMLAR = frozenset(("open", "closed", "merged", "all"))

_GH_TIMEOUT = 20


def _hata_beyaz_liste(proje):
    adlar = ", ".join(sorted(DEPOLAR))
    return {"error": "Bilinmeyen proje: '%s'. Beyaz liste: %s"
                     % ((proje or ""), adlar)}


def _kos(argv, runner=None):
    """gh'yi sabit argv ile kostur, JSON ciktiyi coz."""
    run = runner or subprocess.run
    try:
        r = run(["gh"] + list(argv), capture_output=True, text=True,
                timeout=_GH_TIMEOUT, shell=False,
                encoding="utf-8", errors="replace")
    except FileNotFoundError:
        return {"error": "gh kurulu degil."}
    except Exception as e:
        return {"error": "gh calismadi: %s" % e}
    if r.returncode != 0:
        _hata = (r.stderr or "").strip()
        if len(_hata) > 300:
            _hata = _hata[:300] + "...(kisaltildi)"
        return {"error": "gh hatasi: %s" % _hata}
    try:
        return {"result": json.loads(r.stdout or "[]")}
    except ValueError:
        _ham = (r.stdout or "").strip()
        if len(_ham) > 2000:
            _ham = _ham[:2000] + "\n...(kisaltildi)"
        return {"result": _ham}


def pr_liste(proje, durum="open", runner=None):
    """Acik/kapali PR listesi (salt-okunur)."""
    depo = DEPOLAR.get((proje or "").strip().lower())
    if depo is None:
        return _hata_beyaz_liste(proje)
    durum = (durum or "open").strip().lower()
    if durum not in _DURUMLAR:
        return {"error": "Gecersiz durum: '%s'." % durum}
    return _kos(["pr", "list", "--repo", depo, "--state", durum,
                 "--json", "number,title,state,headRefName"],
                runner=runner)


def pr_goruntule(proje, no, runner=None):
    """Tek PR detayi (salt-okunur)."""
    depo = DEPOLAR.get((proje or "").strip().lower())
    if depo is None:
        return _hata_beyaz_liste(proje)
    try:
        numara = int(no)
    except (TypeError, ValueError):
        return {"error": "PR numarasi sayi olmali."}
    return _kos(["pr", "view", str(numara), "--repo", depo,
                 "--json", "number,title,state,mergedAt,"
                 "statusCheckRollup"], runner=runner)


def calisma_liste(proje, runner=None):
    """Son 5 CI kosusu (salt-okunur)."""
    depo = DEPOLAR.get((proje or "").strip().lower())
    if depo is None:
        return _hata_beyaz_liste(proje)
    return _kos(["run", "list", "--repo", depo, "--limit", "5",
                 "--json", "name,status,conclusion,headBranch"],
                runner=runner)


def github_durum(islem, proje, no=None, durum="open", runner=None):
    """Tek giris: islem secilir, gerisi sabit yoldan kosar."""
    islem = (islem or "").strip().lower()
    if islem in ("pr_liste", "pr_list"):
        return pr_liste(proje, durum, runner=runner)
    if islem in ("pr_goruntule", "pr_gor", "pr_view"):
        return pr_goruntule(proje, no, runner=runner)
    if islem in ("calisma_liste", "run_list", "kosular"):
        return calisma_liste(proje, runner=runner)
    return {"error": ("Bilinmeyen islem: '%s'. Gecerli: pr_liste, "
                      "pr_goruntule, calisma_liste." % (islem or ""))}
