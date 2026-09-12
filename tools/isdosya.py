"""tools/isdosya.py — Is dosyasi (gorev hafizasi).

Uzun islerde "bastan anlatma" devrini kapatir: acik komutla acilan her ise
data/isler/<id>.md dosyasi (HEDEF/PLAN/BULGULAR/SONRAKI/KARARLAR). Aktif is
her turda butceli okunur; bulgular kodla, plan modelle (denetimli) yazilir.

Kurallar:
- Acilis YALNIZ acik komutla (ac_komutu_mu) — otomatik sezme YOK.
- HEDEF acilista kilitlenir, sonra degismez (hedef kaymasi yok).
- Tum yazimlar atomiktir (tmp+rename) — yari dosya kalmaz.
- Okuma butcesi IS_BUTCESI (1500 harf); oncelik SONRAKI > HEDEF > PLAN >
  BULGULAR-kuyrugu. Is yoksa/kapalysa "" doner (sifir bayt).
"""

import logging
import os
import re
import time
import uuid

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KOK = os.path.join(BASE, "data", "isler")
AKTIF_DOSYA = os.path.join(BASE, "data", "aktif_is")

IS_BUTCESI = 1500
BOLUM_SIRASI = ("HEDEF", "PLAN", "BULGULAR", "SONRAKI", "KARARLAR")
YAZILABILIR = ("PLAN", "BULGU", "BULGULAR", "SONRAKI", "KARAR", "KARARLAR")
PLAN_ADET = 10
PLAN_UZUNLUK = 200
BULGU_ADET = 10
BULGU_UZUNLUK = 300
SONRAKI_UZUNLUK = 500
KARAR_ADET = 10
BASLIK_UZUNLUK = 120

# Acik komut kalıpları (kural tabanli, model cagrisi YOK)
AC_KOMUTLARI = (
    "takip et",
    "bunu izle",
    "bunu takip et",
    "iş aç",
    "is ac",
    "işi aç",
    "isi ac",
    "görevi takip et",
    "gorevi takip et",
)


def ac_komutu_mu(text):
    """Metin, is-acma komutu mu?"""
    t = (text or "").lower()
    return any(k in t for k in AC_KOMUTLARI)


KAPAT_KOMUTLARI = (
    "işi kapat",
    "isi kapat",
    "işi bitir",
    "isi bitir",
    "takibi bırak",
    "takibi birak",
)


def kapat_komutu_mu(text):
    """Metin, is-kapatma komutu mu?"""
    t = (text or "").lower()
    return any(k in t for k in KAPAT_KOMUTLARI)


def tur_girisi(text, kok=None):
    """Tur basinda is-dosyasi girisi: (olay_notu|None, blok, uzun_is).

    - kapat komutu + aktif is: kapatir, olay notu doner.
    - ac komutu + aktif YOKSA: acar, olay notu + blok doner.
    - aktif is: blok doner (uzun_is=True).
    - yoksa: (None, "", False) — sifir davranis degisikligi.
    """
    try:
        metin = (text or "").strip()
        if kapat_komutu_mu(metin):
            sid = aktif_id(kok=kok)
            if sid:
                is_kapat(sid, kok=kok)
                return ("İş dosyası kapatıldı.", "", False)
            return (None, "", False)
        if ac_komutu_mu(metin) and not aktif_id(kok=kok):
            r = is_ac_dosya(metin[:BASLIK_UZUNLUK], metin[:500], kok=kok)
            if "is_id" in r:
                notu = ("İş dosyası açıldı (%s). Planını is_notu aracıyla "
                        "(bölüm: plan) dosyaya yaz, sonra işe başla."
                        % r["is_id"])
                return (notu, is_oku(r["is_id"], kok=kok), True)
            return (None, "", False)
        sid = aktif_id(kok=kok)
        if sid:
            return (None, is_oku(sid, kok=kok), True)
        return (None, "", False)
    except Exception as e:
        logger.warning("Is girisi atlandi: %s", e)
        return (None, "", False)


def _kok(kok=None):
    d = kok or KOK
    os.makedirs(d, exist_ok=True)
    return d


def _yol(is_id, kok=None):
    guvenli = re.sub(r"[^a-zA-Z0-9-]", "", str(is_id or ""))[:16]
    return os.path.join(_kok(kok), "%s.md" % guvenli)


def _atomik_yaz(yol, metin):
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    tmp = yol + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(metin)
    os.replace(tmp, yol)


def _yeni_id():
    return uuid.uuid4().hex[:8]


def _sablon(baslik, hedef):
    return (
        "# DURUM: acik\n"
        "# BASLIK: %s\n\n"
        "## HEDEF\n%s\n\n"
        "## PLAN\n(yok)\n\n"
        "## BULGULAR\n(yok)\n\n"
        "## SONRAKI\n(yok)\n\n"
        "## KARARLAR\n(yok)\n"
    ) % (baslik, hedef)


def _bolumleri_ayir(metin):
    """Dosyayi {BOLUM: [satirlar]} sozlugune cevirir."""
    out = {b: [] for b in BOLUM_SIRASI}
    aktif = None
    for satir in (metin or "").split("\n"):
        m = re.match(r"##\s+(\S+)", satir.strip())
        if m and m.group(1) in out:
            aktif = m.group(1)
            continue
        if aktif is not None:
            out[aktif].append(satir)
    return out


def _norm_maddeler(satirlar):
    """'- ...' maddelerini ayiklar; '(yok)' yer tutucuyu eler."""
    maddeler = []
    for s in satirlar:
        s = (s or "").strip()
        if not s or s == "(yok)":
            continue
        if s.startswith("- "):
            s = s[2:].strip()
        if s:
            maddeler.append(s)
    return maddeler


def is_ac_dosya(baslik, hedef, kok=None):
    """Yeni is dosyasi acar ve aktif yapar. Donus: is_id."""
    if not (baslik or "").strip():
        return {"error": "İş başlığı boş olamaz"}
    if not (hedef or "").strip():
        return {"error": "İş hedefi boş olamaz"}
    is_id = _yeni_id()
    _atomik_yaz(_yol(is_id, kok),
                _sablon(baslik.strip()[:BASLIK_UZUNLUK],
                        hedef.strip()[:500]))
    aktif_koy(is_id, kok=kok)
    return {"is_id": is_id}


def _bolum_adi(bolum):
    b = (bolum or "").strip().upper()
    if b in ("BULGU", "BULGULAR"):
        return "BULGULAR"
    if b in ("KARAR", "KARARLAR"):
        return "KARARLAR"
    if b in BOLUM_SIRASI:
        return b
    return None


def is_notu_yaz(is_id, bolum, metin, kok=None):
    """Is dosyasina not duser. HEDEF yazilamaz (acilista kilitli)."""
    hedef_bolum = _bolum_adi(bolum)
    if hedef_bolum is None:
        return {"error": "Bölüm şunlardan biri olmalı: plan, bulgu, "
                         "sonraki, karar"}
    if hedef_bolum == "HEDEF":
        return {"error": "HEDEF açılışta kilitlidir, değiştirilemez"}
    icerik = (metin or "").strip()
    if not icerik:
        return {"error": "Not boş olamaz"}
    try:
        with open(_yol(is_id, kok), "r", encoding="utf-8") as f:
            ham = f.read()
    except OSError:
        return {"error": "İş bulunamadı: %s" % is_id}
    if ham.startswith("# DURUM: kapali"):
        return {"error": "İş kapalı: %s" % is_id}
    parcalar = _bolumleri_ayir(ham)
    if hedef_bolum == "PLAN":
        maddeler = _norm_maddeler(parcalar["PLAN"]) + [icerik[:PLAN_UZUNLUK]]
        parcalar["PLAN"] = ["- " + m for m in maddeler[-PLAN_ADET:]]
    elif hedef_bolum == "BULGULAR":
        maddeler = _norm_maddeler(parcalar["BULGULAR"]) + [icerik[:BULGU_UZUNLUK]]
        parcalar["BULGULAR"] = ["- " + m for m in maddeler[-BULGU_ADET:]]
    elif hedef_bolum == "SONRAKI":
        parcalar["SONRAKI"] = [icerik[:SONRAKI_UZUNLUK]]
    else:  # KARARLAR
        maddeler = _norm_maddeler(parcalar["KARARLAR"]) + [icerik[:200]]
        parcalar["KARARLAR"] = ["- " + m for m in maddeler[-KARAR_ADET:]]
    _atomik_yaz(_yol(is_id, kok), _dosyala(parcalar, ham))
    return {"result": "yazıldı"}


def _dosyala(parcalar, ham):
    """Bölüm sözlüğünü dosya metnine çevirir (başlık satırları korunur)."""
    baslik_satirlari = [s for s in (ham or "").split("\n")
                        if s.startswith("# ")]
    while len(baslik_satirlari) < 2:
        baslik_satirlari.append("# ")
    out = baslik_satirlari[:2] + [""]
    for b in BOLUM_SIRASI:
        govde = [s for s in parcalar.get(b, []) if (s or "").strip()]
        out.append("## " + b)
        out += govde if govde else ["(yok)"]
        out.append("")
    return "\n".join(out).rstrip() + "\n"


def is_oku(is_id, butce=IS_BUTCESI, kok=None):
    """Is dosyasini butceli okur: SONRAKI > HEDEF > PLAN > BULGULAR."""
    try:
        with open(_yol(is_id, kok), "r", encoding="utf-8") as f:
            ham = f.read()
    except OSError:
        return ""
    if ham.startswith("# DURUM: kapali"):
        return ""
    parcalar = _bolumleri_ayir(ham)
    bloklar = []
    for b in ("SONRAKI", "HEDEF", "PLAN"):
        govde = "\n".join(s for s in parcalar.get(b, [])
                          if (s or "").strip() and s.strip() != "(yok)")
        if govde:
            bloklar.append("## " + b + "\n" + govde)
    bulgular = _norm_maddeler(parcalar.get("BULGULAR", []))
    if bulgular:
        # Yeniler öncelikli; bütçeye sığanı al
        secilen = []
        for m in reversed(bulgular):
            aday = "- " + m
            taslak = "\n\n".join(bloklar + ["## BULGULAR\n" + "\n".join(
                secilen + [aday])])
            if len(taslak) > butce:
                break
            secilen.append(aday)
        secilen.reverse()
        if secilen:
            bloklar.append("## BULGULAR\n" + "\n".join(secilen))
    metin = "\n\n".join(bloklar)
    if len(metin) > butce:
        metin = metin[:butce].rstrip() + "..."
    return metin


def is_kapat(is_id, kok=None):
    """Isi kapatir (arsiv niyetine durum bayragi); aktifse aktifligi dusurur."""
    try:
        with open(_yol(is_id, kok), "r", encoding="utf-8") as f:
            ham = f.read()
    except OSError:
        return {"error": "İş bulunamadı: %s" % is_id}
    ham = re.sub(r"^# DURUM:.*$", "# DURUM: kapali", ham,
                 count=1, flags=re.MULTILINE)
    _atomik_yaz(_yol(is_id, kok), ham)
    try:
        if aktif_id(kok=kok) == is_id:
            aktif_temizle(kok=kok)
    except OSError:
        pass
    return {"result": "kapatıldı"}


def is_listele(kok=None):
    """Acik islerin kisa ozeti."""
    d = _kok(kok)
    satirlar = []
    try:
        adlar = sorted(os.listdir(d))
    except OSError:
        return {"result": "İş yok"}
    for ad in adlar:
        if not ad.endswith(".md"):
            continue
        try:
            with open(os.path.join(d, ad), "r", encoding="utf-8") as f:
                ham = f.read()
        except OSError:
            continue
        if ham.startswith("# DURUM: kapali"):
            continue
        baslik = ""
        for satir in ham.split("\n"):
            if satir.startswith("# BASLIK:"):
                baslik = satir.split(":", 1)[1].strip()
                break
        satirlar.append("- %s: %s" % (ad[:-3], baslik))
    if not satirlar:
        return {"result": "İş yok"}
    return {"result": "\n".join(satirlar)}


def _aktif_yolu(kok=None):
    return os.path.join(_kok(kok), "aktif")


def aktif_id(kok=None):
    """Aktif is kimligi (yoksa None)."""
    try:
        with open(_aktif_yolu(kok), "r", encoding="utf-8") as f:
            sid = (f.read() or "").strip()
            return sid or None
    except OSError:
        return None


def aktif_koy(is_id, kok=None):
    _atomik_yaz(_aktif_yolu(kok), str(is_id or ""))


def aktif_temizle(kok=None):
    try:
        os.remove(_aktif_yolu(kok))
    except OSError:
        pass


# ── SOHBET ARACI (executor uyumu) ───────────────────────────────────

def is_notu(is_id, bolum, metin, kok=None):
    """Executor'dan cagrilan ince yuz: is_notu_yaz ile ayni."""
    return is_notu_yaz(is_id, bolum, metin, kok=kok)
