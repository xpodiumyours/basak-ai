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
    "/lab.js": ("lab.js", "application/javascript; charset=utf-8"),
}

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
            pass


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


def _aktif_kimlik(handler):
    """Istegin kisi kimligi; None = 401 gerekir.

    once imzali cookie; yoksa kullanici tablosu bosken tek-kullanici
    modu (casper) — eski yerel/test davranisi bozulmaz.
    """
    import kullanici as kullanici_modulu
    from chat.kimlik import VARSAYILAN_KULLANICI

    token = _cookie_al(handler, kullanici_modulu.cookie_adi())
    kid = kullanici_modulu.oturum_coz(token)
    if kid:
        return kid
    if not kullanici_modulu.giris_zorunlu_mu():
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
    if kid:
        from chat.kimlik import kullanici_kur
        kullanici_kur(kid)
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
            pass

    def _token_ok(self):
        if not _ayar("web_dis_erisim", False):
            return True   # localhost: token gerekmez
        beklenen = _ayar("web_token", "")
        istek_token = self.headers.get("X-Basak-Token", "")
        if not istek_token:
            # GET polling sorgusunda da token query yedegi kabul edilir.
            from urllib.parse import parse_qs, urlparse
            qs = parse_qs(urlparse(self.path).query)
            istek_token = (qs.get("token") or [""])[0]
        return bool(istek_token) and istek_token == beklenen

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
            self._gonder(401, {"error": "giris gerekli"})
            return True
        from chat.kimlik import kullanici_kur
        kullanici_kur(kid)
        return False

    def _giris_yap(self):
        """POST /api/giris — ad + sifre -> HttpOnly cookie."""
        import kullanici as kullanici_modulu

        try:
            uzunluk = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            uzunluk = 0
        if uzunluk <= 0 or uzunluk > 4096:
            self._gonder(400, {"error": "govde boyu"})
            return
        try:
            veri = json.loads(self.rfile.read(uzunluk).decode("utf-8"))
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
            pass

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
            pass

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
                pass
            self._gonder(200, {"ok": True, "oturum": sid})
            return
        if yol != "/api/sohbet":
            self._gonder(404, {"error": "yok"})
            return
        if not self._token_ok():
            self._gonder(401, {"error": "token gecersiz"})
            return
        try:
            uzunluk = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            uzunluk = 0
        if uzunluk <= 0 or uzunluk > 16384:
            self._gonder(400, {"error": "govde boyu"})
            return
        try:
            veri = json.loads(self.rfile.read(uzunluk).decode("utf-8"))
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

    port = int(_ayar("web_port", 8787))
    dis = bool(_ayar("web_dis_erisim", False))
    adres = "0.0.0.0" if dis else "127.0.0.1"
    sunucu = ThreadingHTTPServer((adres, port), _Kopru)
    print("Basak web koprusu: http://%s:%d  (%s erisim)"
          % ("127.0.0.1" if not dis else adres, port,
             "DIS + token" if dis else "yalniz bu bilgisayar"))
    print("Kapatmak icin pencereyi kapat.")
    try:
        sunucu.serve_forever()
    except KeyboardInterrupt:
        pass


if __name__ == "__main__":
    main()
