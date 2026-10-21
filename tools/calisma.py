"""tools/calisma.py — Yapılan işin okunabilir özeti (salt-okunur).

Bu bir MODEL ARACI DEGILDIR: `tools/definitions.py` listesinde yoktur ve
modele sunulmaz. Web ekrani (/durum) "saatlerdir suren calismanin sonucu ne?"
sorusunu CEKIRDEKTEN okuyarak yanitlar. Ikinci bir beyin, ikinci bir
zincir yoktur (AGENTS.md §9).

Nerede ne var:
- `knowledge/`                     → Basak'in calisma notlari (depoda kayitli)
- `knowledge/yayin-kayitlari.md`   → canliya cikan islerin kaydi (tarihli)
- `<state>/matris/`                → fikir tablolari (kisiye ozel, kanitli satirlar)
- `<state>/gorevler.json`          → gorevler (kisiye ozel)

Kural: hicbir sey yazilmaz. Dosya yoksa "yok" doner; uydurma kayit uretilmez.
Bozulmus/okunamayan dosya sessizce yutulmaz — hata metni `hata` alaninda
gorunur.
"""

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

# None = proje kokundeki knowledge/ (testler monkeypatch edebilir).
BILGI_KOK = None

_YAYIN_DOSYASI = "yayin-kayitlari.md"
_ENTRI_DESENI = re.compile(r"^\s*-\s+(\d{4}-\d{2}-\d{2})\s*:\s*(.*)$")


def bilgi_kok():
    """Calisma notlarinin klasoru."""
    if BILGI_KOK:
        return BILGI_KOK
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return os.path.join(kok, "knowledge")


def _ilk_baslik(metin):
    """Markdown basligi; yoksa ilk dolu satir."""
    for satir in metin.splitlines():
        s = satir.strip()
        if s.startswith("#"):
            return s.lstrip("#").strip()
    for satir in metin.splitlines():
        s = satir.strip()
        if s and not s.startswith("---"):
            return s[:120]
    return ""


def _ilk_cumle(metin):
    """Basligi atlayip ilk anlamli satiri ozet olarak doner."""
    for satir in metin.splitlines():
        s = satir.strip()
        if not s or s.startswith("#") or s.startswith("---"):
            continue
        return s[:220]
    return ""


def notlar(limit=40):
    """Calisma notlari: ad + baslik + tek satirlik ozet."""
    kok = bilgi_kok()
    try:
        adlar = sorted(os.listdir(kok))
    except OSError as e:
        return {"hata": "Notlar okunamadi: %s" % e, "liste": []}
    liste = []
    for ad in adlar:
        if not ad.lower().endswith((".md", ".txt")):
            continue
        yol = os.path.join(kok, ad)
        try:
            with open(yol, "r", encoding="utf-8-sig") as f:
                metin = f.read(20000)
            boyut = os.path.getsize(yol)
        except OSError as e:
            logger.debug("not okunamadi: %s (%s)", ad, e)
            continue
        liste.append({
            "ad": ad,
            "baslik": _ilk_baslik(metin) or os.path.splitext(ad)[0],
            "ozet": _ilk_cumle(metin),
            "boyut": boyut,
        })
    liste.sort(key=lambda n: n["ad"])
    return {"liste": liste[:limit], "toplam": len(liste), "hata": None}


def yayin_kayitlari(limit=6):
    """Canliya cikan islerin kaydi: en yeni kayitlar once."""
    yol = os.path.join(bilgi_kok(), _YAYIN_DOSYASI)
    try:
        with open(yol, "r", encoding="utf-8-sig") as f:
            satirlar = f.read().splitlines()
    except OSError as e:
        return {"hata": "Yayin kaydi okunamadi: %s" % e, "liste": []}

    kayitlar = []
    for satir in satirlar:
        eslesme = _ENTRI_DESENI.match(satir)
        if not eslesme:
            continue
        kayitlar.append({"tarih": eslesme.group(1),
                         "metin": eslesme.group(2).strip()})
    # Kayit dosyasi en yeniden eskiye yazilir; yine de tarihe gore sirala.
    kayitlar.sort(key=lambda k: k["tarih"], reverse=True)
    return {"liste": kayitlar[:limit], "toplam": len(kayitlar), "hata": None}


def _tablolar(limit=6):
    """Fikir tablolari: baslik, skor, son satirlar (kanitlarla)."""
    try:
        from tools import matris
    except Exception as e:                       # pragma: no cover
        return {"hata": "Tablolar okunamadi: %s" % e, "liste": []}
    try:
        return matris.calisma_ozeti(limit=limit)
    except Exception as e:                       # pragma: no cover
        return {"hata": "Tablolar okunamadi: %s" % e, "liste": []}


def _gorevler():
    """Gorevler: sayim + acik olanlar (kisiye ozel)."""
    try:
        from tools import tasks
        from tools import gorevler_dosyasi
    except Exception as e:                       # pragma: no cover
        return {"hata": "Gorevler okunamadi: %s" % e}
    try:
        return tasks.gorev_ozeti(gorevler_dosyasi())
    except Exception as e:                       # pragma: no cover
        return {"hata": "Gorevler okunamadi: %s" % e}


def ozet(limit=6):
    """Yapilan isin tam ozeti: notlar + yayin kaydi + tablolar + gorevler."""
    veri = {
        "notlar": notlar(),
        "yayin": yayin_kayitlari(limit=limit),
        "tablolar": _tablolar(limit=limit),
        "gorevler": _gorevler(),
    }
    veri["okundu"] = True
    return veri
