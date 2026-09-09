"""memory/profil.py — Kalici kullanici profili + konusarak ogrenme.

2026-09-09: Casper istedi — "hafizasi kalici olsun, beni konusarak
tanisin". Episodic anilar budanabilir/silinebilir; PROFIL budanmaz,
temizlenmez. meta tablosunda "profil" anahtariyla JSON durur:

    {"ad": "Casper",
     "tercihler": ["sade konusma", "cayi sekerli"],
     "bilgiler": ["muhendis", "Istanbul'da yasiyor"]}

Ogrenme kural tabanlidir (ekstra model cagrisi YOK — kota yenmez):
kullanici cumlesindeki acik kalıplar yakalanir. Supheli eslesme
KAYDEDILMEZ (yanlis ogrenmektense ogrenmemek).

Hassas bilgi ASLA profile alinmaz: sifre, TC, kart, telefon, adres.
Bu kalıplar gorulurse o cumleden hicbir sey ogrenilmez.
"""

import logging
import re

logger = logging.getLogger(__name__)

PROFIL_ANAHTARI = "profil"

# Hassas bilgi kokusu — bu cumleden ogrenme YOK
_HASSAS = re.compile(
    r"(sifre|şifre|parola|tc\b|kimlik\s*no|kart\s*no|kredi\s*kart|"
    r"telefon|gsm|cep\s*no|iban|hesap\s*no|cvv|cvc|pin\s*kod)",
    re.IGNORECASE,
)

_AD = r"[A-ZÇĞİÖŞÜ][a-zçğıöşü]+"

# (alan, desen, grup)
_AD_KALIPLARI = [
    ("ad", re.compile(r"benim ad[ıi]m\s+(%s)" % _AD)),
    ("ad", re.compile(r"\bad[ıi]m\s+(%s)" % _AD)),
    ("ad", re.compile(r"bana\s+(%s)\s+de\b" % _AD)),
]

_HATIRLA = re.compile(
    r"^(hat[ıi]rla|unutma|akl[ıi]nda tut)\s*[:\-]?\s*(.+)$",
    re.IGNORECASE | re.DOTALL,
)

_SEVME = re.compile(
    r"(.{2,60}?)\s+(seviyorum|severim|sevmiyorum|sevmem)\b",
    re.IGNORECASE,
)

_MESLEKLER = (
    "mühendis|muhendis|öğretmen|ogretmen|öğrenci|ogrenci|doktor|avukat|"
    "yazılımcı|yazilimci|tasarımcı|tasarimci|memur|emekli|esnaf|işçi|isci|"
    "mimar|hemşire|hemsire|muhasebeci|eczacı|eczaci|pilot|şoför|sofor|"
    "aşçı|asci|garson|polis|asker|çiftçi|ciftci|ev hanımı|ev hanimi|"
    "yönetici|yonetici|müdür|mudur|patron|serbest|freelance"
)
_MESLEK = re.compile(
    r"\bben\s+(?:bir\s+)?((?:%s))(?:y[ıiuü]m|[ıiuü]m)?\b"
    % _MESLEKLER, re.IGNORECASE,
)
_CALISMA = re.compile(
    r"\bben\s+(.+?)\s+olarak\s+çalışıyorum\b", re.IGNORECASE,
)

_SEHIR = re.compile(
    r"\bben\s+(.+?)(?:'da|'de|'ta|'te|da|de|ta|te)\s+"
    r"(yaşıyorum|yasiyorum|oturuyorum)\b", re.IGNORECASE,
)

_UNUT = re.compile(r"^unut\s*[:\-]?\s*(.+)$", re.IGNORECASE | re.DOTALL)
_HEPSINI_UNUT = re.compile(
    r"hakkımdaki her şeyi unut|hakkimdaki her seyi unut|"
    r"beni tamamen unut|profilimi sil", re.IGNORECASE,
)


def bos_profil():
    return {"ad": "", "tercihler": [], "bilgiler": []}


def profil_al(motor):
    """Motor yoksa bos profil; varsa meta'dan okur."""
    if not motor:
        return bos_profil()
    try:
        p = motor.meta_al(PROFIL_ANAHTARI, None)
    except Exception:
        return bos_profil()
    if not isinstance(p, dict):
        return bos_profil()
    return {
        "ad": str(p.get("ad", "")),
        "tercihler": [str(x) for x in (p.get("tercihler") or [])],
        "bilgiler": [str(x) for x in (p.get("bilgiler") or [])],
    }


def profil_koy(motor, profil):
    try:
        motor.meta_koy(PROFIL_ANAHTARI, profil)
        return True
    except Exception as e:
        logger.warning("Profil yazilamadi: %s", e)
        return False


def _ekle(profil, alan, deger):
    deger = re.sub(r"\s+", " ", (deger or "")).strip(" .!,:;\"'")
    if not deger or len(deger) > 80:
        return None
    hedef = profil["tercihler"] if alan == "tercih" else profil["bilgiler"]
    if alan == "ad":
        if profil["ad"] == deger:
            return None
        profil["ad"] = deger
        return ("ad", deger)
    if deger in hedef:
        return None
    hedef.append(deger)
    if len(hedef) > 30:
        del hedef[0]
    return (alan, deger)


def cikar(cumle):
    """Cumleden ogrenilecekleri cikarir: [(alan, deger)].

    Alanlar: ad / tercih / bilgi. Hassas kokulu cumle -> [].
    """
    t = (cumle or "").strip()
    if not t or _HASSAS.search(t):
        return []
    bulgular = []

    for alan, desen in _AD_KALIPLARI:
        m = desen.search(t)
        if m:
            bulgular.append((alan, m.group(1)))
            break

    m = _HATIRLA.match(t)
    if m:
        icerik = m.group(2).strip()
        if icerik and not _HASSAS.search(icerik):
            bulgular.append(("bilgi", icerik))

    m = _SEVME.search(t)
    if m:
        nesne = re.sub(r"^ben\s+", "", m.group(1).strip(),
                       flags=re.IGNORECASE)
        fiil = m.group(2).lower()
        if nesne and len(nesne) <= 40 and not _HASSAS.search(nesne):
            if fiil in ("sevmiyorum", "sevmem"):
                bulgular.append(("tercih", nesne + " sevmiyor"))
            else:
                bulgular.append(("tercih", nesne + " seviyor"))

    m = _MESLEK.search(t)
    if m:
        bulgular.append(("bilgi", m.group(1).strip().lower()))

    m = _CALISMA.search(t)
    if m and len(m.group(1).strip()) <= 40:
        bulgular.append(("bilgi", m.group(1).strip() + " olarak çalışıyor"))

    m = _SEHIR.search(t)
    if m and len(m.group(1).strip()) <= 30:
        bulgular.append(("bilgi", m.group(1).strip() + " yaşıyor"))

    return bulgular


def ogren(motor, cumle, speaker=""):
    """Cumleden ogren, profile + episodic(onem=3) yaz.

    Donus: yeni ogrenilen [(alan, deger)] listesi.
    """
    if not motor or not (cumle or "").strip():
        return []
    profil = profil_al(motor)
    yeniler = []
    for alan, deger in cikar(cumle):
        kayit = _ekle(profil, alan, deger)
        if kayit:
            yeniler.append(kayit)
    if yeniler:
        profil_koy(motor, profil)
        try:
            motor.ekle(
                "Öğrenildi (%s): %s" % (
                    speaker or "Casper",
                    "; ".join("%s=%s" % (a, d) for a, d in yeniler)),
                kind="episodic", kaynak="profil-ogrenme", onem=3)
        except Exception as e:
            logger.warning("Ogrenme anisi yazilamadi: %s", e)
    return yeniler


def unut(motor, cumle):
    """'unut: X' -> profilde X gecen kayitlari siler. Donus: silinen sayisi.

    'hakkimdaki her seyi unut' -> profil sifirlanir (episodic'e dokunulmaz;
    onun dugmesi UI'daki temizlemedir).
    """
    if not motor:
        return 0
    t = (cumle or "").strip()
    if _HEPSINI_UNUT.search(t):
        profil_koy(motor, bos_profil())
        return -1
    m = _UNUT.match(t)
    if not m:
        return 0
    hedef = m.group(1).strip().lower()
    if not hedef:
        return 0
    profil = profil_al(motor)
    sayi = 0
    for liste in ("tercihler", "bilgiler"):
        once = len(profil[liste])
        profil[liste] = [x for x in profil[liste]
                         if hedef not in x.lower()]
        sayi += once - len(profil[liste])
    if profil["ad"] and hedef in profil["ad"].lower():
        profil["ad"] = ""
        sayi += 1
    if sayi:
        profil_koy(motor, profil)
    return sayi


def blok(motor):
    """System prompt'a eklenecek 'bilinenler' blogu (bossa '')."""
    profil = profil_al(motor)
    parcalar = []
    if profil["ad"]:
        parcalar.append("Adi: %s" % profil["ad"])
    if profil["tercihler"]:
        parcalar.append("Tercihleri: %s" % "; ".join(profil["tercihler"]))
    if profil["bilgiler"]:
        parcalar.append("Bilinenler: %s" % "; ".join(profil["bilgiler"]))
    if not parcalar:
        return ""
    return ("Casper hakkinda KALICI bilinenler (bunlari tekrar sorma):\n"
            + "\n".join("- " + p for p in parcalar))
