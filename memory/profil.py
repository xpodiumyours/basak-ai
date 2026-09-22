"""memory/profil.py — Kalici kullanici profili (salt-okunur).

2026-09-09: Casper istedi — "hafizasi kalici olsun, beni konusarak
tanisin". Episodic anilar budanabilir/silinebilir; PROFIL budanmaz,
temizlenmez. meta tablosunda "profil" anahtariyla JSON durur:

    {"ad": "Casper",
     "tercihler": ["sade konusma", "cayi sekerli"],
     "bilgiler": ["muhendis", "Istanbul'da yasiyor"]}

2026-09-13 (Casper karari): kullanici cumlelerini regex'le yorumlayip
profil uretmek kelime tabanli chatbot mantigiydi — sokuldu. Model
kendi hatirlar; kod adina karar vermez. Bu dosya yalniz KAYITLI
profili okur/yazar; ogrenme kapisi stub'dur (asagida).

Hassas bilgi ASLA profile alinmaz: sifre, TC, kart, telefon, adres.
"""

import logging
import re

logger = logging.getLogger(__name__)

PROFIL_ANAHTARI = "profil"

# Hassas bilgi kokusu — ogrenme kapisi canlanirsa ilk satir bu kalir.
_HASSAS = re.compile(
    r"(sifre|şifre|parola|tc\b|kimlik\s*no|kart\s*no|kredi\s*kart|"
    r"telefon|gsm|cep\s*no|iban|hesap\s*no|cvv|cvc|pin\s*kod)",
    re.IGNORECASE,
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


def blok(motor):
    """System prompt'a eklenecek 'bilinenler' blogu (bossa '').

    2026-09-23: yalniz casper oturumunda cagrilir (flow._baglam_kur
    kisitlar) — diger web kullanicilarina kisisel bilgi sizmaz.
    Savunma derinligi: aktif kisi casper degilse profil hic okunmaz.
    """
    from chat.kimlik import VARSAYILAN_KULLANICI, aktif_kullanici
    if aktif_kullanici() != VARSAYILAN_KULLANICI:
        return ""
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


# 2026-09-13 (Casper karari): kullanici cumlelerini regex'le yorumlayip
# profil uretmek kelime tabanli chatbot mantigiydi. Model kendi
# hatirlar; kod adina karar vermez.
def ogren(motor, text, speaker=""):
    return []


def unut(motor, text):
    return 0
