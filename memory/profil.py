"""memory/profil.py — Kayıtlı kullanıcı profilinin salt-okunur bağlamı.

Bu modül kullanıcı cümlesini yorumlamaz, regex/kelimeyle profil üretmez ve
sohbet sırasında otomatik profil silmez. Yalnız daha önce açıkça kaydedilmiş
profil verisini okuma/yazma yardımcılarını sağlar.
"""
import logging

logger = logging.getLogger(__name__)

PROFIL_ANAHTARI = "profil"

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
    return ("Casper hakkinda kayitli profil:\n"
            + "\n".join("- " + p for p in parcalar))
