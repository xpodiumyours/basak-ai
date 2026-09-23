"""kullanici.py — Web kullanıcı tablosu + şifre hash'i + oturum jetonu.

Kurallar:
- Şifre düz metin SAKLANMAZ: hashlib.pbkdf2_hmac (stdlib) + tuz.
- Tablo: data/kullanicilar.json (Vercel'de BASAK_STATE_DIR altında).
- Oturum: imzalı HttpOnly cookie (Vercel'de de çalışır; bellek tutmaz).
- Tablo boş/yoksa tek-kullanıcı modu: herkes `casper` (eski davranış);
  ilk kullanıcı eklenince giriş zorunlu olur.
"""

import base64
import hashlib
import hmac
import json
import os
import secrets
import time

from chat.kimlik import slugla, state_kok

KULLANICI_DOSYA = None  # None = state_kok()/kullanicilar.json (test patch edebilir)

_PBKDF2_TUR = "pbkdf2-sha256"
_PBKDF2_TUR_SAYISI = 200000
_OTURUM_OMUR = 7 * 24 * 3600  # 7 gün
_OTURUM_COOKIE = "basak_oturum"


def kullanici_dosyasi():
    if KULLANICI_DOSYA is not None:
        return KULLANICI_DOSYA
    return os.path.join(state_kok(), "kullanicilar.json")


def _yukle():
    try:
        with open(kullanici_dosyasi(), "r", encoding="utf-8-sig") as f:
            veri = json.load(f)
        return veri if isinstance(veri, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def _kaydet(veri):
    yol = kullanici_dosyasi()
    os.makedirs(os.path.dirname(yol), exist_ok=True)
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
    os.replace(gecici, yol)


def hash_le(sifre, tuz=None):
    """pbkdf2_sha256 hash üretir: `pbkdf2-sha256$<tur>$<tuz>$<hex>`."""
    tuz = tuz or secrets.token_hex(16)
    dk = hashlib.pbkdf2_hmac(
        "sha256", str(sifre).encode("utf-8"),
        bytes.fromhex(tuz), _PBKDF2_TUR_SAYISI)
    return "%s$%d$%s$%s" % (_PBKDF2_TUR, _PBKDF2_TUR_SAYISI, tuz, dk.hex())


def dogrula(sifre, kayit):
    """Kayıtlı hash'e karşı şifreyi doğrular (düz metin karşılaştırma yok)."""
    if not isinstance(kayit, str):
        return False
    try:
        tur, tur_sayisi, tuz, beklenen = kayit.split("$", 3)
        if tur != _PBKDF2_TUR:
            return False
        dk = hashlib.pbkdf2_hmac(
            "sha256", str(sifre).encode("utf-8"),
            bytes.fromhex(tuz), int(tur_sayisi))
        return hmac.compare_digest(dk.hex(), beklenen)
    except (ValueError, TypeError):
        return False


def kullanici_listesi():
    """{slug: kayit} — slug'lar normalize edilir."""
    return {slugla(ad): kayit for ad, kayit in _yukle().items()}


def giris_zorunlu_mu():
    """Kayıtlı kullanıcı varsa web girişi zorunlu; yoksa tek-kullanıcı modu."""
    return bool(kullanici_listesi())


def giris_kontrol(ad, sifre):
    """Başarılıysa slug döndürür, değilse None."""
    slug = slugla(ad)
    kayit = kullanici_listesi().get(slug)
    if not kayit:
        return None
    hash_ = kayit.get("hash") if isinstance(kayit, dict) else kayit
    if dogrula(sifre, hash_):
        return slug
    return None


def kullanici_ekle(ad, sifre, varsa_guncelle=False):
    """Kullanıcı ekler/günceller. Dönüş: slug ya da hata mesajı."""
    slug = slugla(ad)
    if not str(sifre or ""):
        return "sifre bos olamaz"
    if not varsa_guncelle and slug in kullanici_listesi():
        return "kullanici zaten var: %s" % slug
    veri = _yukle()
    veri[slug] = {"hash": hash_le(sifre), "ad": str(ad or "").strip()}
    _kaydet(veri)
    return slug


# ── Oturum jetonu (imzalı cookie — bellek tutmaz, Vercel'de çalışır) ──

def _anahtar():
    anahtar = (os.environ.get("BASAK_OTURUM_ANAHTARI")
               or os.environ.get("BASAK_WEB_TOKEN") or "").strip()
    if anahtar:
        return anahtar.encode("utf-8")
    # Yerel: dosyada bir kez üretilir (gitignore'da), Vercel'de env şart.
    yol = os.path.join(state_kok(), "oturum.anahtar")
    try:
        with open(yol, "rb") as f:
            mevcut = f.read().strip()
        if mevcut:
            return mevcut
    except OSError:
        pass
    yeni = secrets.token_hex(32).encode("ascii")
    try:
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        with open(yol, "wb") as f:
            f.write(yeni)
    except OSError:
        pass
    return yeni


def oturum_tokeni_uret(kid, omur_sn=_OTURUM_OMUR):
    bitis = int(time.time()) + int(omur_sn)
    ham = "%s.%d" % (slugla(kid), bitis)
    imza = hmac.new(_anahtar(), ham.encode("utf-8"),
                    hashlib.sha256).hexdigest()
    govde = base64.urlsafe_b64encode(
        ham.encode("utf-8")).decode("ascii").rstrip("=")
    return "%s.%s" % (govde, imza)


def oturum_coz(token):
    """Geçerliyse slug döndürür; süresi dolmuş/bozuksa None."""
    if not token or "." not in str(token):
        return None
    govde, imza = str(token).rsplit(".", 1)
    try:
        padding = "=" * (-len(govde) % 4)
        ham = base64.urlsafe_b64decode(govde + padding).decode("utf-8")
    except (ValueError, UnicodeDecodeError):
        return None
    beklenen = hmac.new(_anahtar(), ham.encode("utf-8"),
                        hashlib.sha256).hexdigest()
    # imza cerezden gelir: ASCII disi harf (or. Turkce s) compare_digest'i
    # TypeError ile patlatir ve istek 500 doner. Imza her zaman onaltilik
    # ASCII'dir; oyle degilse gecersizdir -- cokme yerine None.
    if not imza.isascii() or not hmac.compare_digest(beklenen, imza):
        return None
    try:
        kid, bitis = ham.rsplit(".", 1)
        if int(bitis) < time.time():
            return None
    except (ValueError, TypeError):
        return None
    return slugla(kid)


def cookie_adi():
    return _OTURUM_COOKIE
