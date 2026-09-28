"""tools/freetools_yerel.py — tarayici yokken yerel standart algoritma (Faz 2).

Neden var: freetools.org sayfalari tarayicida (JS) calisir; Vercel'de
playwright YOKTUR (60 sn / 500 MB). Bu modul freetools.org'un JS'ini
KOPYALAMAZ (lisansi acik degil) — yalnizca Python standart kutuphanesindeki
evrensel algoritmalari (hashlib, base64, urllib.parse, ondalik aritmetik)
kullanir. Boylece web'de arac sonucu bos kalmaz.

Kurallar:
- Yalnizca EMIN oldugumuz, evrensel/dogrulanmis araclar burada vardir
  (Faz 1'de canli karsilastirilan SHA-256, Base64, yuzde dahil).
- Diger araclar None doner: kopru hatasi aynen modele gider, uydurma yok.
- Her sonuc "kaynak": "yerel-hesaplama" etiketiyle doner; model aracin
  freetools.org adresini de verir (derin baglanti yeni sekmede acilir).
- Adres denetimi (beyaz liste) kopru tarafindan ONCE yapilir; buraya
  *.freetools.org disinda bir adres asla gelmez.
"""

import base64
import binascii
import hashlib
import re
from decimal import Decimal, InvalidOperation
from urllib.parse import quote, unquote

KAYNAK_ETIKETI = "yerel-hesaplama (standart algoritma)"


# ── yardimcilar ──────────────────────────────────────────────────────

def _girdi(form, i=0):
    if not isinstance(form, (list, tuple)):
        form = [form]
    ham = [str(f) for f in form if f is not None]
    return ham[i] if len(ham) > i else ""


def _yon(form):
    """Ikinci alan yon belirtiyorsa ('decode'/'coz') True."""
    s = _girdi(form, 1).strip().lower()
    return s in ("decode", "dec", "coz", "çöz", "çözme", "çözülmüş",
                 "down") or s.startswith("çöz")


def _ondalik(d):
    if d == d.to_integral():
        return str(int(d))
    return format(d.normalize(), "f")


# ── araclar ──────────────────────────────────────────────────────────

def _sha(form):
    """sha-hash-generator — canli testte SHA-256 birebir dogrulandi."""
    metin = _girdi(form, 0)
    istek = _girdi(form, 1).strip().lower().replace("-", "").replace("_", "")
    adaylar = ("md5", "sha1", "sha224", "sha256", "sha384", "sha512")
    secim = next((a for a in adaylar if istek == a), "sha256")
    return hashlib.new(secim, metin.encode("utf-8")).hexdigest()


def _b64_coz(metin):
    try:
        bayt = base64.b64decode(metin.strip(), validate=False)
    except (binascii.Error, ValueError, TypeError):
        return None
    try:
        return bayt.decode("utf-8")
    except UnicodeDecodeError:
        return None


def _base64(form):
    """base64-encode-decode — canli testte kodlama birebir dogrulandi."""
    metin = _girdi(form, 0)
    if _yon(form):
        cozulmus = _b64_coz(metin)
        if cozulmus is None:
            return None
        return cozulmus
    return base64.b64encode(metin.encode("utf-8")).decode("ascii")


def _base64_cozucu(form):
    cozulmus = _b64_coz(_girdi(form, 0))
    if cozulmus is None:
        return None
    return cozulmus


def _url(form):
    metin = _girdi(form, 0)
    if _yon(form):
        return unquote(metin)
    return quote(metin, safe="")


def _yuzde(form):
    """percentage-calculator — canli testte (15, 200) -> 30 dogrulandi."""
    try:
        a = Decimal(_girdi(form, 0).replace(",", "."))
        b = Decimal(_girdi(form, 1).replace(",", "."))
    except (InvalidOperation, ValueError):
        return None
    return _ondalik(a * b / Decimal(100))


def _harf_sayaci(form):
    metin = _girdi(form, 0)
    return "\n".join((
        "Karakter (boşluklu): %d" % len(metin),
        "Karakter (boşluksuz): %d" % len(metin.replace(" ", "")),
        "Kelime: %d" % len(metin.split()),
        "Harf: %d" % sum(1 for c in metin if c.isalpha()),
        "Rakam: %d" % sum(1 for c in metin if c.isdigit()),
        "Satır: %d" % (len(metin.splitlines()) if metin else 0),
    ))


def _ters(form):
    return _girdi(form, 0)[::-1]


def _bin_hex(form):
    """binary-hex-converter — yalnizca deger doner, bicim serbest."""
    ham = _girdi(form, 0).strip().lower()
    if ham.startswith("0x"):
        ham = ham[2:]
    if not ham:
        return None
    if re.fullmatch(r"[01]+", ham):
        return "0x" + format(int(ham, 2), "x")
    if re.fullmatch(r"[0-9a-f]+", ham):
        ikili = format(int(ham, 16), "b")
        return " ".join(ikili[i:i + 4] for i in range(0, len(ikili), 4))
    return None


def _hex_ondalik(form):
    """hexadecimal-to-decimal-converter — giris hex (sayfanin yonu)."""
    ham = _girdi(form, 0).strip().lower()
    if ham.startswith("0x"):
        ham = ham[2:]
    if not ham or not re.fullmatch(r"[0-9a-f]+", ham):
        return None
    return str(int(ham, 16))


# slug -> hesaplayici
ARACLAR = {
    "sha-hash-generator": _sha,
    "base64-encode-decode": _base64,
    "base64-decoder": _base64_cozucu,
    "url-encode-decode": _url,
    "percentage-calculator": _yuzde,
    "letter-counter": _harf_sayaci,
    "reverse-text": _ters,
    "binary-hex-converter": _bin_hex,
    "hexadecimal-to-decimal-converter": _hex_ondalik,
}


def slug(adres):
    """Adresin arac slug'i (son yol parcasi)."""
    yol = str(adres or "").strip().rstrip("/")
    return yol.rsplit("/", 1)[-1].lower() if yol else ""


def hesapla(adres, form=None):
    """Adresteki araci yerelde (standart algoritmayla) calistirir.

    Doneger:
      {"sonuc": str, "kaynak": KAYNAK_ETIKETI, "adres": adres}  — basarili
      None                                             — bu arac bizde yok
      {"error": str}                                   — girdi gecersiz
    """
    fonksiyon = ARACLAR.get(slug(adres))
    if fonksiyon is None:
        return None
    if not isinstance(form, (list, tuple)):
        form = [form] if form else []
    try:
        sonuc = fonksiyon([str(f) for f in form][:8])
    except Exception:
        return {"error": "Yerel hesap başarısız: girdi okunamadı"}
    if sonuc is None:
        return {"error": ("Yerel hesap yapılamadı: girdi bu aracın "
                          "beklediği biçimde değil")}
    if not str(sonuc).strip():
        return {"error": "Yerel hesap boş sonuç verdi"}
    return {"sonuc": str(sonuc), "kaynak": KAYNAK_ETIKETI, "adres": adres}
