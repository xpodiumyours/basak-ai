"""basak_web.py — Basak'in web yuzu: KOPRU + EKRAN (tek beyin kurali).

AGENTS.md §9 + knowledge/web-kopru-plani.md:
- Beyin yalniz cekirdekte: bu dosya yalniz HTTP koprusu + statik ekran
  servisidir. Ayrı ajan dongusu, saglayici zinciri, arac calistirici
  YOKTUR; tek baglanacak nokta chat.flow.mesaj_isle'dir (telegram_bot.py
  ile ayni yol, ucuncu yuz).
- Olay akisi: cekirdek BasakUI.* dizelerini yayar; kopru bunlari
  istek-bazli HTTP polling ile tasir (parca/bitir/error/toolStatus/thinking).
- Guvenlik: varsayilan 127.0.0.1; dis erisim yalniz ayarlarla
  ("web_dis_erisim": true) ve zorunlu token ile. Ayarlar.json servis
  EDILMEZ; yol beyaz listesi disinda dosya servis edilmez.
- Kosum: python basak_web.py  (port: ayarlar.json "web_port", 8787)
"""

import json
import logging
import os
import subprocess
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

logging.basicConfig(level=logging.INFO,
                    format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("basak_web")

BASE = Path(__file__).resolve().parent
WEB = BASE / "web"
MATRIS = BASE / "data" / "kabul-matrisi.json"
AYARLAR = BASE / "ayarlar.json"

# Yol beyaz listesi: disari acilan TEK dosyalar. Uzanti -> MIME.
_STATIK = {
    "/": ("index.html", "text/html; charset=utf-8"),
    "/index.html": ("index.html", "text/html; charset=utf-8"),
    "/giris.html": ("giris.html", "text/html; charset=utf-8"),
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/common.js": ("common.js", "application/javascript; charset=utf-8"),
    "/chat.css": ("chat.css", "text/css; charset=utf-8"),
    "/lab.html": ("lab.html", "text/html; charset=utf-8"),
    "/durum.html": ("durum.html", "text/html; charset=utf-8"),
    "/durum.js": ("durum.js", "application/javascript; charset=utf-8"),
    "/durum-kabul.json": ("durum-kabul.json", "application/json; charset=utf-8"),
}

# POST govdesi tavanlari. Sohbet govdesi gecmisi ve ekleri tasir; 16 KiB
# gercek kullanimda doluyordu. Giris govdesi kucuk kalir.
_SOHBET_GOVDE_SINIRI = 262144
_GIRIS_GOVDE_SINIRI = 4096

# Kimlik istisnaları: giris/сagri disinda /api/* kimlik ister.
# Saglik (/api/durum) acik kalir — kopru durumu olcer.
_KIMLIK_ISTISNA = ("/api/durum",)

# ── Olay kaydi (HTTP polling) ────────────────────────────────────────
# Quick Tunnel SSE desteklemez. Olaylar istek kimligine gore bellekte
# tutulur; tarayici kisa HTTP GET'lerle yalniz kendi olaylarini alir.
# Boylece olay kacirma/capraz kullanici sizintisi da engellenir.
_KILIT = threading.Lock()
_OLAYLAR = {}       # {istek: [olay, ...]}
_OLAY_ZAMANI = {}   # {istek: son_degisim_monotonic}
_OLAY_TTL = 600.0


def _eski_olaylari_temizle():
    simdi = time.monotonic()
    eski = [
        no for no, zaman in _OLAY_ZAMANI.items()
        if simdi - zaman > _OLAY_TTL
    ]
    for no in eski:
        _OLAY_ZAMANI.pop(no, None)
        _OLAYLAR.pop(no, None)


def _yayin(olay):
    no = olay.get("istek") if isinstance(olay, dict) else None
    if no is None:
        return
    with _KILIT:
        _eski_olaylari_temizle()
        _OLAYLAR.setdefault(no, []).append(olay)
        _OLAY_ZAMANI[no] = time.monotonic()


# ── Cekirdek olay ayiklayici (telegram_bot.Kaydedici ile ayni kalip) ─
class _OlayAyiklayici:
    """js_callback yerine gecer: BasakUI.* dizelerini SSE olayina mapler."""

    def __init__(self, istek):
        self.istek = istek
        self.bitti = False

    def olay(self, tur, **veri):
        """Cekirdegin zengin olayini (source, runState...) SSE'ye yollar.

        `hasattr(js_callback, "olay")` korumali cagri — bu metod yokken
        `source` uretilmiyor, web'deki Kaynaklar bolumu hep bos kaliyordu.
        """
        yay = {"istek": self.istek, "tur": str(tur)}
        yay.update(veri)
        _yayin(yay)

    def __call__(self, kod):
        try:
            if not kod.startswith("BasakUI."):
                return
            ad, icerik = kod[8:].split("(", 1)
            parca = json.loads("[%s]" % icerik.rsplit(")", 1)[0])
            if ad in ("parca", "error", "toolStatus"):
                _yayin({"istek": self.istek, "tur": ad, "metin": parca[0]})
            elif ad == "thinking":
                _yayin({"istek": self.istek, "tur": "thinking"})
            elif ad == "bitir":
                self.bitti = True
                _yayin({"istek": self.istek, "tur": "bitir",
                        "cevap": parca[0],
                        "kaynak": parca[1] if len(parca) > 1 else ""})
        except Exception:
            # Cekirdegin urettigi kod satiri cozulemedi: bu tur icin atlanir,
            # akis bir sonraki satirda devam eder. Iz birakilir.
            logger.debug("UI kodu cozulemedi: %r", kod[:120], exc_info=True)


class _EklentiAyiklayici:
    """Eklenti paneli icin olay ayiklayici: son cevabi toplar.

    Ayni cekirdek yolu (mesaj_isle) calisir; fark yalniz tasiyicidir —
    HTTP olay kuyrugu yerine tek cevap sozlugu.
    """

    def __init__(self):
        self.cevap = ""
        self.kaynak = ""
        self.hata = ""
        self.bitti = False

    def olay(self, tur, **veri):
        """Durum olaylari simdilik yalniz iz birakir (akis sonra eklenecek)."""
        logger.debug("eklenti olayi: %s %s", tur, sorted(veri))

    def __call__(self, kod):
        try:
            if not str(kod).startswith("BasakUI."):
                return
            ad, icerik = kod[8:].split("(", 1)
            parca = json.loads("[%s]" % icerik.rsplit(")", 1)[0])
            if ad == "bitir":
                self.bitti = True
                self.cevap = str(parca[0] or "")
                self.kaynak = str(parca[1] or "") if len(parca) > 1 else ""
            elif ad == "error":
                self.hata = str(parca[0] or "")
        except Exception:
            logger.debug("eklenti UI kodu cozulemedi: %r", str(kod)[:120])


def _eklenti_sohbet(metin, kullanici=None):
    """Eklenti panelinden gelen mesaj — TEK cekirdek girisi.

    Kendi beyin/arac zinciri YOKTUR: chat.flow.mesaj_isle cagrilir.
    Boylece panel, web ekrani ve Telegram ayni Basak'i konusturur.
    """
    metin = str(metin or "").strip()
    if not metin:
        raise ValueError("mesaj bos")
    if BEYIN is None or TOOLS is None:
        raise RuntimeError("cekirdek hazir degil")

    from chat.flow import mesaj_isle
    from chat.kimlik import kullanici_kur
    from chat.prompts import kisilik_blogu

    if kullanici:
        kullanici_kur(kullanici)
    else:
        kullanici_kur("misafir")     # kimlik yok: kisisel koke dusme
    ayikla = _EklentiAyiklayici()
    mesaj_isle(metin, BEYIN, kisilik_blogu(kullanici, misafir=not kullanici),
               ayikla, TOOLS)
    if ayikla.hata and not ayikla.cevap:
        raise RuntimeError(ayikla.hata)
    return {"cevap": ayikla.cevap, "kaynak": ayikla.kaynak}


def _sunucu_ayarlari():
    """(port, adres) — ortam degiskeni > ayarlar.json > yerel varsayilan.

    Barindirilan onizleme icin `BASAK_WEB_PORT=3001 BASAK_WEB_DIS=1`
    yeter; ayarlar.json'a dokunmak gerekmez. Ortam bos ise davranis
    eskisi gibi: 8787 + yalniz bu makine.
    """
    port = int(os.environ.get("BASAK_WEB_PORT") or _ayar("web_port", 8787))
    dis = (bool(_ayar("web_dis_erisim", False))
           or os.environ.get("BASAK_WEB_DIS", "").strip().lower()
           in ("1", "true", "evet", "yes"))
    return port, "0.0.0.0" if dis else "127.0.0.1"


def _ayar(anahtar, varsayilan=None):
    try:
        with open(AYARLAR, "r", encoding="utf-8-sig") as f:
            return json.load(f).get(anahtar, varsayilan)
    except (OSError, ValueError):
        return varsayilan


# ── Kisi kimligi (web) ──────────────────────────────────────────────

def _cookie_al(handler, ad):
    ham = handler.headers.get("Cookie", "") or ""
    for parcasi in ham.split(";"):
        parcasi = parcasi.strip()
        if parcasi.startswith(ad + "="):
            return parcasi.split("=", 1)[1]
    return ""


def _yerel_sunucu(handler):
    """Sunucu yalnız bu makineye mi bağlı (masaüstü açılışı)?

    0.0.0.0'a bağlı sunucu önizleme/sunucudur; orada kişisel kimlik
    VARSAYILMAZ (2026-10-21, canlıda görülen sızıntı: önizleme, giriş
    olmayan herkesi "casper" sayıp "Casper'ın kişisel asistanıyım"
    diyordu).
    """
    try:
        adres = str(handler.server.server_address[0])
    except (AttributeError, IndexError, TypeError):
        return False
    return adres in ("127.0.0.1", "::1", "localhost")


def _aktif_kimlik(handler):
    """İsteğin kişi kimliği; None = kimliksiz (misafir) ziyaretçi.

    Önce imzalı cookie. Yoksa tek-kişi (casper) modu YALNIZ yerel
    sunucuda geçerli; dışarı açık sunucuda kimlik uydurulmaz.
    """
    import kullanici as kullanici_modulu
    from chat.kimlik import VARSAYILAN_KULLANICI

    token = _cookie_al(handler, kullanici_modulu.cookie_adi())
    kid = kullanici_modulu.oturum_coz(token)
    if kid:
        return kid
    if not kullanici_modulu.giris_zorunlu_mu() and _yerel_sunucu(handler):
        return VARSAYILAN_KULLANICI
    return None


def mesaj_isle_cagir(metin, beyin, kisilik, ayiklayici, toollar,
                     misafir=False):
    """TEK cekirdek girisi — testlerde enjekte edilebilir nokta.
    Buradan baska hicbir sey cagrilmaz (tek beyin kurali)."""
    from chat.flow import mesaj_isle
    mesaj_isle(metin, beyin, kisilik, ayiklayici, toollar,
               misafir=misafir)


def _sohbet_islet(istek, metin, misafir=False, kid=None):
    """Cekirdek cagrisi — kendi thread'inde. TEK beyin: mesaj_isle.

    kid: web girisindeki kisi — yeni thread'in contextvar'i default
    'casper'a sifirlanir; burada tekrar kurulur (kişi izolasyonu).
    """
    from chat.kimlik import kullanici_kur
    if kid:
        kullanici_kur(kid)
    elif misafir:
        # Kimliksiz ziyaretci: hafiza/knowledge kökü kişisel köke
        # (casper) DÜŞMEZ; nötr bir kök kullanilir.
        kullanici_kur("misafir")
    from chat.prompts import kisilik_blogu
    ayikla = _OlayAyiklayici(istek)
    try:
        mesaj_isle_cagir(metin, BEYIN, kisilik_blogu(kid, misafir=misafir),
                         ayikla, TOOLS, misafir=misafir)
    except Exception as e:
        logger.warning("Sohbet hatasi: %s", e)
        if not ayikla.bitti:
            _yayin({"istek": istek, "tur": "bitir",
                    "cevap": "Bir sorun oldu: %s" % e, "kaynak": ""})


# ── HTTP katmani ─────────────────────────────────────────────────────

class _Kopru(BaseHTTPRequestHandler):
    server_version = "BasakKopru/1"

    def log_message(self, bicim, *args):   # guurlukleri kirletme
        logger.debug(bicim, *args)

    def _gonder(self, kod, veri, tur="application/json; charset=utf-8"):
        govde = veri if isinstance(veri, bytes) else json.dumps(
            veri, ensure_ascii=False).encode("utf-8")
        self.send_response(kod)
        self.send_header("Content-Type", tur)
        self.send_header("Content-Length", str(len(govde)))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        try:
            self.wfile.write(govde)
        except (BrokenPipeError, ConnectionAbortedError):
            # Istemci sekmeyi kapatti / baglanti koptu. Sunucu tarafinda
            # yapilacak bir sey yok; gürültü olmasin diye iz seviyesinde.
            logger.debug("istemci baglantisi koptu (govde yazilamadi)")

    def _token_ok(self):
        # Gecerli IMZALI oturum cerezi varsa token tekrar sorulmaz:
        # ad+sifre girisinden sonraki istekler bu yoldan gecer.
        # _aktif_kimlik BURADA KULLANILMAZ — o, kullanici tablosu bosken
        # tek-kullanici moduna duser ve disa acik kapiyi tokensuz gecirir
        # (olculdu 2026-09-23: test_dis_erisim_token_zorunlu kirmizi).
        import kullanici as kullanici_modulu
        cerez = _cookie_al(self, kullanici_modulu.cookie_adi())
        if cerez and kullanici_modulu.oturum_coz(cerez):
            return True
        if not _ayar("web_dis_erisim", False):
            return True   # localhost: token gerekmez
        import hmac
        beklenen = _ayar("web_token", "")
        istek_token = self.headers.get("X-Basak-Token", "")
        if not istek_token:
            # GET polling sorgusunda da token query yedegi kabul edilir.
            from urllib.parse import parse_qs, urlparse
            qs = parse_qs(urlparse(self.path).query)
            istek_token = (qs.get("token") or [""])[0]
        if not istek_token or not beklenen:
            return False
        # Sabit sureli karsilastirma: token karsilastirmasi zamanlama
        # kanaliyla tahmin edilemez.
        return hmac.compare_digest(
            istek_token.encode("utf-8"),
            str(beklenen).encode("utf-8"),
        )

    def _json(self, kod, veri):
        self._gonder(kod, veri)

    def _kimlik_zorunlu(self, yol):
        """True = engellendi (401 yazildi); False = devam et."""
        if not yol.startswith("/api/"):
            return False
        if yol in _KIMLIK_ISTISNA:
            return False
        kid = _aktif_kimlik(self)
        if kid is None:
            import kullanici as kullanici_modulu
            if (kullanici_modulu.giris_zorunlu_mu()
                    or kullanici_modulu.uretim_mi()):
                self._gonder(401, {"error": "giris gerekli"})
                return True
            # Kimlik yok ama giriş zorunlu değil: ziyaretçi NÖTR misafir
            # olarak devam eder (kişisel kimlik uydurulmaz).
            return False
        from chat.kimlik import kullanici_kur
        kullanici_kur(kid)
        return False

    def _istek_govdesi(self, sinir):
        """POST govdesini okur: `Content-Length` ya da parcali (chunked).

        Neden: onizleme/vekil katmani govdeyi chunked iletiyor; yalniz
        Content-Length'e bakan eski kod her mesaji "govde boyu" diye
        reddediyordu (olculdu: curl normal 200, chunked 400).
        """
        kodlama = (self.headers.get("Transfer-Encoding") or "").lower()
        if "chunked" in kodlama:
            return self._parcali_govde(sinir)
        try:
            uzunluk = int(self.headers.get("Content-Length") or 0)
        except (TypeError, ValueError):
            raise ValueError("govde boyu")
        if uzunluk < 0 or uzunluk > sinir:
            raise ValueError("govde boyu")
        return self.rfile.read(uzunluk) if uzunluk else b""

    def _parcali_govde(self, sinir):
        """Chunked govdeyi cozer; tavan asilirsa okumayi keser."""
        parcalar, toplam = [], 0
        while True:
            satir = self.rfile.readline(1024)
            if not satir:
                raise ValueError("govde boyu")
            try:
                boy = int(satir.strip().split(b";")[0], 16)
            except ValueError:
                raise ValueError("govde boyu")
            if boy == 0:
                while True:                 # trailer satirlarini at
                    iz = self.rfile.readline(1024)
                    if iz in (b"\r\n", b"\n", b""):
                        break
                break
            toplam += boy
            if toplam > sinir:
                raise ValueError("govde boyu")
            parcalar.append(self.rfile.read(boy))
            self.rfile.read(2)              # parca sonu CRLF
        return b"".join(parcalar)

    def _giris_yap(self):
        """POST /api/giris — ad + sifre -> HttpOnly cookie."""
        import kullanici as kullanici_modulu

        try:
            govde = self._istek_govdesi(_GIRIS_GOVDE_SINIRI)
        except ValueError:
            self._gonder(400, {"error": "govde boyu"})
            return
        if not govde:
            self._gonder(400, {"error": "govde boyu"})
            return
        try:
            veri = json.loads(govde.decode("utf-8"))
            ad = str(veri.get("ad", "")).strip()
            sifre = str(veri.get("sifre", ""))
        except (ValueError, UnicodeDecodeError):
            self._gonder(400, {"error": "gecersiz json"})
            return
        kid = kullanici_modulu.giris_kontrol(ad, sifre)
        if kid is None:
            self._gonder(401, {"error": "ad veya sifre hatali"})
            return
        token = kullanici_modulu.oturum_tokeni_uret(kid)
        govde = self._govde_olustur({"ok": True, "kullanici": kid})
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(govde)))
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Set-Cookie",
            "%s=%s; Path=/; HttpOnly; SameSite=Lax; Max-Age=%d"
            % (kullanici_modulu.cookie_adi(), token, 7 * 24 * 3600))
        self.end_headers()
        try:
            self.wfile.write(govde)
        except (BrokenPipeError, ConnectionAbortedError):
            logger.debug("istemci baglantisi koptu (giris cevabinda)")

    def _cikis_yap(self):
        import kullanici as kullanici_modulu
        govde = self._govde_olustur({"ok": True})
        self.send_response(200)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(govde)))
        self.send_header("Cache-Control", "no-store")
        self.send_header(
            "Set-Cookie",
            "%s=; Path=/; HttpOnly; SameSite=Lax; Max-Age=0"
            % kullanici_modulu.cookie_adi())
        self.end_headers()
        try:
            self.wfile.write(govde)
        except (BrokenPipeError, ConnectionAbortedError):
            logger.debug("istemci baglantisi koptu (cikis cevabinda)")

    def _govde_olustur(self, veri):
        return json.dumps(veri, ensure_ascii=False).encode("utf-8")

    def do_GET(self):
        yol = self.path.split("?", 1)[0]
        if yol.startswith("/api/") and not self._token_ok():
            # Dis erisimde tum api noktalari token ister (matris dahil —
            # olcum verisi disariya acilmaz). localhost'ta serbest.
            self._gonder(401, {"error": "token gecersiz"})
            return
        if yol.startswith("/api/") and self._kimlik_zorunlu(yol):
            return
        if yol == "/api/olaylar":
            self._olaylari_ver()
        elif yol == "/api/sohbetler":
            from chat import oturum
            self._gonder(200, {"ok": True, "liste": oturum.liste()})
        elif yol.startswith("/api/sohbet/"):
            from chat import oturum
            from chat.kimlik import aktif_kullanici
            sid = yol.rsplit("/", 1)[-1]
            # Sahiplik: kisi kendi dizininde okur; sahip alan da
            # denetlenir (eski tek-dizin bug'ina karsi ikinci kapi).
            msgs = oturum.ac(sid)
            kid = aktif_kullanici()
            if msgs is None or not oturum.sahip_mi(sid, kid):
                # 403: bu sohbet sana ait degil (404 ile karistirmamak
                # icin sahiplik reddi burada; kisi kokusunda yok = sahipsiz).
                self._gonder(403, {"error": "bu sohbet sana ait degil"})
            else:
                self._gonder(200, {"ok": True, "mesajlar": msgs})
        elif yol == "/api/durum":
            self._gonder(200, _runtime_durumu())
        elif yol == "/api/matris":
            if not MATRIS.exists():
                self._gonder(200, {"duzey2": {}, "not": "matris henüz yok"})
                return
            self._gonder(200, MATRIS.read_bytes(),
                         "application/json; charset=utf-8")
        elif yol in _STATIK:
            dosya, mime = _STATIK[yol]
            icerik = (WEB / dosya).read_bytes()
            self._gonder(200, icerik, mime)
        else:
            self._gonder(404, {"error": "yok"})

    def _olaylari_ver(self):
        """Bir istegin yeni olaylarini JSON olarak dondurur.

        Query:
          istek=<int>  zorunlu
          son=<int>    istemcinin gordugu olay sayisi (varsayilan 0)
        """
        from urllib.parse import parse_qs, urlparse

        qs = parse_qs(urlparse(self.path).query)
        try:
            istek = int((qs.get("istek") or [""])[0])
            son = max(0, int((qs.get("son") or ["0"])[0]))
        except (TypeError, ValueError):
            self._gonder(400, {"error": "gecersiz istek/son"})
            return

        with _KILIT:
            _eski_olaylari_temizle()
            tumu = list(_OLAYLAR.get(istek, []))
        yeniler = tumu[son:]
        bitti = any(o.get("tur") in ("bitir", "error") for o in tumu)
        self._gonder(200, {
            "istek": istek,
            "olaylar": yeniler,
            "son": len(tumu),
            "bitti": bitti,
        })

    def do_POST(self):
        yol = self.path.split("?", 1)[0]
        if yol == "/api/giris":
            self._giris_yap()
            return
        if yol == "/api/cikis":
            self._cikis_yap()
            return
        if yol == "/api/yeni":
            if not self._token_ok():
                self._gonder(401, {"error": "token gecersiz"})
                return
            if self._kimlik_zorunlu(yol):
                return
            from chat import oturum
            from chat import context as ctx
            try:
                eski = [m for m in ctx.yukle(ctx.gecmis_yolu(), [])
                        if m.get("role") != "system"]
            except Exception:
                eski = []
            sid = oturum.yeni(eski)
            try:
                ctx.kaydet(ctx.gecmis_yolu(), [])
            except OSError:
                logger.warning("gecmis dosyasi temizlenemedi: %s",
                               exc_info=True)
            self._gonder(200, {"ok": True, "oturum": sid})
            return
        if yol != "/api/sohbet":
            self._gonder(404, {"error": "yok"})
            return
        if not self._token_ok():
            self._gonder(401, {"error": "token gecersiz"})
            return
        try:
            govde = self._istek_govdesi(_SOHBET_GOVDE_SINIRI)
        except ValueError:
            self._gonder(400, {"error": "govde boyu"})
            return
        if not govde:
            self._gonder(400, {"error": "govde boyu"})
            return
        try:
            veri = json.loads(govde.decode("utf-8"))
            metin = str(veri.get("metin", "")).strip()
            # Misafir bayragi URL'den gelir (?misafir=1), metne bakilmaz.
            misafir = bool(veri.get("misafir", False))
        except (ValueError, UnicodeDecodeError):
            self._gonder(400, {"error": "gecersiz json"})
            return
        # Misafir hariç: giris zorunlu (kisi kimligi alinir).
        kid = None
        if not misafir:
            if self._kimlik_zorunlu(yol):
                return
            kid = _aktif_kimlik(self)
            if kid is None:
                # Kimlik yok (dışarı açık sunucu, girişsiz ziyaretçi):
                # kişisel kimlik uydurulmaz, nötr misafir olarak devam.
                misafir = True
        if not metin or len(metin) > 4000:
            self._gonder(400, {"error": "mesaj bos veya cok uzun"})
            return

        global _SAYAC
        with _KILIT:
            _eski_olaylari_temizle()
            _SAYAC += 1
            istek = _SAYAC
            _OLAYLAR[istek] = []
            _OLAY_ZAMANI[istek] = time.monotonic()
        threading.Thread(target=_sohbet_islet,
                         args=(istek, metin, misafir, kid),
                         daemon=True).start()
        self._gonder(200, {"ok": True, "istek": istek})

    def do_HEAD(self):
        self.send_response(200)
        self.end_headers()

    # Guvenlik: yalniz bilinen metodlar.
    def do_PUT(self):
        self._gonder(405, {"error": "yasak"})

    do_DELETE = do_PUT
    do_PATCH = do_PUT


_SAYAC = 0
BEYIN = None
# KISILIK artık kisilik_blogu ile istek bazında üretilir (yabancıya
# Casper adı sızmaz). main() sadece beyin/toolları kurar.
TOOLS = None


def _git_commit():
    """Calisan web koprusunun gercek kod surumunu gosterir."""
    try:
        return subprocess.check_output(
            ["git", "rev-parse", "--short", "HEAD"],
            cwd=str(BASE), timeout=2, text=True,
            stderr=subprocess.DEVNULL,
        ).strip()
    except Exception:
        return "dogrulanamadi"


def _runtime_durumu():
    """Sir/anahtar acmadan calisan Basak'in durumunu verir."""
    saglayicilar = []
    if BEYIN is not None:
        try:
            saglayicilar = [
                ad for ad, _ in BEYIN._bulut_zinciri(tools=True)
            ]
        except Exception:
            saglayicilar = []

    modeller = []
    beklenen_saglayicilar = []
    eksik_saglayicilar = []
    try:
        from brain import registry
        from brain.stats import model_stats_al
        istat = model_stats_al()
        beklenen_saglayicilar = list(registry.VARSAYILAN_SIRA)
        eksik_saglayicilar = [
            ad for ad in beklenen_saglayicilar if ad not in saglayicilar
        ]
        istemciler = dict(BEYIN._bulut_zinciri(tools=True)) if BEYIN else {}
        for ad in saglayicilar:
            kart = registry.kart(ad)
            istemci = istemciler.get(ad)
            modeller.append({
                "ad": ad,
                "model": getattr(istemci, "model", None) or "dogrulanamadi",
                "gucleri": list(kart.get("gucleri") or []),
                "limit": {
                    "saatlik_istek": kart.get("saatlik_istek"),
                    "gunluk_istek": kart.get("gunluk_istek"),
                    "aylik_istek": kart.get("aylik_istek"),
                    "gunluk_token": kart.get("gunluk_token"),
                    "gunluk_neuron": kart.get("gunluk_neuron"),
                },
                "kullanim": {
                    "saat": istat.istek_sayisi(ad, "saat"),
                    "gun": istat.istek_sayisi(ad, "gun"),
                    "ay": istat.istek_sayisi(ad, "ay"),
                    "bugun_token": sum(istat.token_bugun(ad)),
                },
            })
    except Exception as e:
        logger.debug("Model durum ayrintisi okunamadi: %s", e)

    return {
        "ok": BEYIN is not None and TOOLS is not None,
        "commit": _git_commit(),
        "saglayicilar": saglayicilar,
        "beklenen_saglayicilar": beklenen_saglayicilar,
        "eksik_saglayicilar": eksik_saglayicilar,
        "modeller": modeller,
        "arac_sayisi": len(TOOLS or []),
        "tasima": "http-polling",
    }


def main():
    global BEYIN, TOOLS
    from basak_app import init_cache
    from brain import Brain
    from chat.kimlik import kullanici_kur
    from tools import TOOLS as _TOOLS
    # Yerel web koprusu da yerel kisi = casper (web girisinden once).
    kullanici_kur("casper")
    init_cache()
    BEYIN = Brain()
    TOOLS = _TOOLS

    port, adres = _sunucu_ayarlari()
    dis = adres != "127.0.0.1"
    sunucu = ThreadingHTTPServer((adres, port), _Kopru)
    print("Basak web koprusu: http://%s:%d  (%s erisim)"
          % ("127.0.0.1" if not dis else adres, port,
             "DIS + token" if dis else "yalniz bu bilgisayar"))

    # Tarayici eklentisi koprusu (goz). Yerel WebSocket; eklenti baglanirsa
    # `sayfa_bakis` aracı acik sekmeyi okuyabilir. Kapatmak icin
    # ayarlar.json -> "eklenti_acik": false.
    if _ayar("eklenti_acik", True):
        try:
            from tools import tarayici_ws
            eklenti_koprusu = tarayici_ws.baslat(sohbet_isle=_eklenti_sohbet)
            print("Basak eklenti koprusu: ws://127.0.0.1:%d  (eklenti baglanabilir)"
                  % eklenti_koprusu.port)
        except Exception as hata:            # noqa: BLE001 - sohbet kesilmesin
            logger.warning("eklenti koprusu acilmadi: %s", hata)
    print("Kapatmak icin pencereyi kapat.")
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        # Ctrl-C normal kapanis yolu.
        print("Basak web koprusu kapatildi.")


if __name__ == "__main__":
    main()
