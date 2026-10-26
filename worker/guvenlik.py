"""Bulut işçisi için onay belgesi ve adres güvenliği.

Kural: bu modül KARAR VERMEZ. Hangi eylemin yapılacağını Başak'ın beyni
ve kullanıcı onayı belirler. Burada yalnız şunlar vardır:

- Eylem + kaynak + argüman özetine bağlı HMAC imzası.
- Kısa ömür ve tek kullanım.
- SSRF koruması: iç/özel adreslere ve standart dışı portlara çıkış yok.

Belge biçimi: base64url(payload) + "." + base64url(hmac_sha256).
"""

import base64
import hashlib
import hmac
import ipaddress
import json
import secrets
import socket
import threading
import time
from urllib.parse import urlsplit

# RFC 6598 paylaşımlı adres uzayı; Python'un is_private'ı bunu her
# sürümde kapsamıyor.
_CGNAT = ipaddress.ip_network("100.64.0.0/10")

_SEMA = "p2-bulut-adim-v1"


class TokenHatasi(ValueError):
    """Onay belgesi geçersiz, süresi dolmuş ya da eyleme uymuyor."""


class GuvenlikHatasi(ValueError):
    """Adres güvenlik denetiminden geçmedi."""


def _b64e(ham):
    return base64.urlsafe_b64encode(ham).rstrip(b"=").decode("ascii")


def _b64d(metin):
    dolgu = "=" * (-len(metin) % 4)
    try:
        return base64.urlsafe_b64decode(metin + dolgu)
    except (ValueError, TypeError) as hata:
        raise TokenHatasi("belge çözülemedi") from hata


def _simdi(deger=None):
    return int(time.time() if deger is None else deger)


def kaynak(url):
    """URL'nin şema + host + port kimliği.

    Varsayılan portlar açıkça yazılır; `https://a.test` ile
    `https://a.test:443` aynı kaynaktır.
    """
    try:
        k = urlsplit(str(url or "").strip())
        port = k.port
    except ValueError as hata:
        raise TokenHatasi("geçersiz URL") from hata
    if k.scheme not in ("http", "https") or not k.hostname:
        raise TokenHatasi("geçersiz URL")
    if k.username or k.password:
        raise TokenHatasi("URL kimlik bilgisi taşıyamaz")
    if port is None:
        port = 443 if k.scheme == "https" else 80
    return "%s://%s:%d" % (k.scheme, k.hostname.lower(), port)


def eylem_ozeti(tur, argumanlar=None):
    """Eylem türü + argümanların kanonik SHA-256 özeti."""
    govde = json.dumps(
        {"tur": str(tur or ""), "arg": argumanlar or {}},
        sort_keys=True, separators=(",", ":"), ensure_ascii=False,
    )
    return hashlib.sha256(govde.encode("utf-8")).hexdigest()


def token_uret(anahtar, *, kosu_id, adim_id, tur, url, argumanlar=None,
               ttl=120, nonce=None, simdi=None):
    """Başak tarafında, kullanıcı onayından sonra üretilir.

    İşçi bu belgeyi üretemez; yalnız doğrular. `ttl` en fazla 300 sn.
    """
    if not anahtar:
        raise TokenHatasi("işçi anahtarı yok")
    kosu_id = str(kosu_id or "").strip()
    adim_id = str(adim_id or "").strip()
    if not kosu_id or not adim_id:
        raise TokenHatasi("koşu ve adım kimliği zorunlu")
    if len(kosu_id) > 96 or len(adim_id) > 96:
        raise TokenHatasi("kimlik çok uzun")
    if ttl is None:
        ttl = 120
    # 0 açıkça "en kısa süre" demektir; `ttl or 120` onu 120'ye çevirirdi.
    ttl = max(1, min(int(ttl), 300))
    payload = {
        "v": 1,
        "sema": _SEMA,
        "rid": kosu_id,
        "sid": adim_id,
        "tur": str(tur or ""),
        "org": kaynak(url),
        "h": eylem_ozeti(tur, argumanlar),
        "exp": _simdi(simdi) + ttl,
        "nonce": str(nonce or secrets.token_hex(16)),
    }
    govde = _b64e(json.dumps(
        payload, sort_keys=True, separators=(",", ":"),
        ensure_ascii=False,
    ).encode("utf-8"))
    imza = _b64e(hmac.new(
        anahtar.encode("utf-8"), govde.encode("ascii"), hashlib.sha256,
    ).digest())
    return govde + "." + imza, payload


def token_dogrula(anahtar, token, *, tur, url, argumanlar=None, simdi=None,
                  kosu_id=None, adim_id=None):
    """İmza, süre, kimlik, eylem, kaynak ve argüman özetini doğrular.

    `kosu_id` / `adim_id` verilirse belge bunlara da bağlanır: başka bir
    koşuda veya adımda geçerli olmaz. İşçi ikisini de her zaman verir.
    """
    if not anahtar:
        raise TokenHatasi("işçi anahtarı yok")
    parcalar = str(token or "").split(".")
    if len(parcalar) != 2:
        raise TokenHatasi("belge biçimi geçersiz")
    govde, imza = parcalar
    beklenen = _b64e(hmac.new(
        anahtar.encode("utf-8"), govde.encode("ascii"), hashlib.sha256,
    ).digest())
    if not hmac.compare_digest(imza, beklenen):
        raise TokenHatasi("imza geçersiz")
    try:
        payload = json.loads(_b64d(govde).decode("utf-8"))
    except (ValueError, UnicodeDecodeError) as hata:
        raise TokenHatasi("belge çözülemedi") from hata
    if not isinstance(payload, dict) or payload.get("v") != 1:
        raise TokenHatasi("belge sürümü desteklenmiyor")
    if payload.get("sema") != _SEMA:
        raise TokenHatasi("belge şeması desteklenmiyor")
    try:
        bitis = int(payload.get("exp") or 0)
    except (TypeError, ValueError) as hata:
        raise TokenHatasi("belge süresi geçersiz") from hata
    if _simdi(simdi) >= bitis:
        raise TokenHatasi("belgenin süresi doldu")
    if not str(payload.get("rid") or "") or not str(payload.get("sid") or ""):
        raise TokenHatasi("belge koşu/adım kimliği taşımıyor")
    if kosu_id is not None and str(payload.get("rid")) != str(kosu_id):
        raise TokenHatasi("belge başka koşu için")
    if adim_id is not None and str(payload.get("sid")) != str(adim_id):
        raise TokenHatasi("belge başka adım için")
    if str(payload.get("tur") or "") != str(tur or ""):
        raise TokenHatasi("belge başka eylem için")
    if str(payload.get("org") or "") != kaynak(url):
        raise TokenHatasi("belge başka kaynak için")
    if str(payload.get("h") or "") != eylem_ozeti(tur, argumanlar):
        raise TokenHatasi("belge başka argümanlar için")
    return payload


class TekKullanim:
    """Nonce defteri; aynı onay belgesi ikinci kez çalışmaz.

    Süreç içi MVP'dir. Postgres'e taşındığında aynı `kullan` sözleşmesi
    korunacak; atomiklik veritabanı satırıyla sağlanacak.
    """

    def __init__(self):
        self._kilit = threading.Lock()
        self._nonce = {}

    def kullan(self, nonce, exp, simdi=None):
        nonce = str(nonce or "").strip()
        if not nonce:
            return False
        an = _simdi(simdi)
        with self._kilit:
            for anahtar, bitis in list(self._nonce.items()):
                if int(bitis) <= an:
                    self._nonce.pop(anahtar, None)
            if nonce in self._nonce:
                return False
            self._nonce[nonce] = int(exp or an + 300)
            return True


def guvenli_url(url):
    """SSRF denetimi; engel varsa insan okunur neden, yoksa None döner.

    Hostname çözülür ve TÜM adresler denetlenir. DNS yeniden çözümleme
    (rebinding) için tam koruma değildir; bu yüzden tarayıcı ayrıca
    yönlendirme sonrası adresi tekrar denetler.
    """
    try:
        k = urlsplit(str(url or "").strip())
        port = k.port
    except ValueError:
        return "geçersiz URL"
    if k.scheme not in ("http", "https"):
        return "yalnız http/https"
    if k.username or k.password:
        return "URL kimlik bilgisi taşıyamaz"
    if port is not None and port not in (80, 443):
        return "yalnız 80/443 portları"
    if not k.hostname:
        return "sunucu adı yok"
    try:
        bilgiler = socket.getaddrinfo(k.hostname, None)
    except (socket.gaierror, OSError):
        return "adres çözülemedi"
    for bilgi in bilgiler:
        ham = str(bilgi[4][0]).split("%", 1)[0]
        try:
            ip = ipaddress.ip_address(ham)
        except ValueError:
            continue
        if (ip.is_private or ip.is_loopback or ip.is_link_local
                or ip.is_reserved or ip.is_multicast or ip.is_unspecified
                or ip in _CGNAT):
            return "iç/özel adres (%s)" % ip
    return None
