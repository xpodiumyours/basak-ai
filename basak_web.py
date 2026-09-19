"""basak_web.py — Basak'in web yuzu: KOPRU + EKRAN (tek beyin kurali).

AGENTS.md §9 + knowledge/web-kopru-plani.md:
- Beyin yalniz cekirdekte: bu dosya yalniz HTTP koprusu + statik ekran
  servisidir. Ayrı ajan dongusu, saglayici zinciri, arac calistirici
  YOKTUR; tek baglanacak nokta chat.flow.mesaj_isle'dir (telegram_bot.py
  ile ayni yol, ucuncu yuz).
- Olay akisi: cekirdek BasakUI.* dizelerini yayar; kopru bunu SSE'ye
  dogrudan mapler (parca/bitir/error/toolStatus/thinking).
- Guvenlik: varsayilan 127.0.0.1; dis erisim yalniz ayarlarla
  ("web_dis_erisim": true) ve zorunlu token ile. Ayarlar.json servis
  EDILMEZ; yol beyaz listesi disinda dosya servis edilmez.
- Kosum: python basak_web.py  (port: ayarlar.json "web_port", 8787)
"""

import json
import logging
import os
import threading
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
    "/app.js": ("app.js", "application/javascript; charset=utf-8"),
    "/styles.css": ("styles.css", "text/css; charset=utf-8"),
    "/common.js": ("common.js", "application/javascript; charset=utf-8"),
    "/lab.html": ("lab.html", "text/html; charset=utf-8"),
    "/lab.js": ("lab.js", "application/javascript; charset=utf-8"),
}

# ── Olay yayini (SSE) ────────────────────────────────────────────────
_KILIT = threading.Lock()
_ABONELER = []   # her abone: queue.Queue; yayin tum abonelere gider


def _yayin(olay):
    with _KILIT:
        aboneler = list(_ABONELER)
    for q in aboneler:
        try:
            q.put_nowait(olay)
        except Exception:
            pass


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


def mesaj_isle_cagir(metin, beyin, kisilik, ayiklayici, toollar):
    """TEK cekirdek girisi — testlerde enjekte edilebilir nokta.
    Buradan baska hicbir sey cagrilmaz (tek beyin kurali)."""
    from chat.flow import mesaj_isle
    mesaj_isle(metin, beyin, kisilik, ayiklayici, toollar)


def _sohbet_islet(istek, metin):
    """Cekirdek cagrisi — kendi thread'inde. TEK beyin: mesaj_isle."""
    ayikla = _OlayAyiklayici(istek)
    try:
        mesaj_isle_cagir(metin, BEYIN, KISILIK, ayikla, TOOLS)
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
            # EventSource baslik ekleyemez; SSE icin ?token= kabul edilir.
            from urllib.parse import parse_qs, urlparse
            qs = parse_qs(urlparse(self.path).query)
            istek_token = (qs.get("token") or [""])[0]
        return bool(istek_token) and istek_token == beklenen

    def do_GET(self):
        yol = self.path.split("?", 1)[0]
        if yol.startswith("/api/") and not self._token_ok():
            # Dis erisimde tum api noktalari token ister (matris dahil —
            # olcum verisi disariya acilmaz). localhost'ta serbest.
            self._gonder(401, {"error": "token gecersiz"})
            return
        if yol == "/api/olaylar":
            self._sse()
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

    def _sse(self):
        if not self._token_ok():
            self._gonder(401, {"error": "token gecersiz"})
            return
        import queue
        q = queue.Queue()
        with _KILIT:
            _ABONELER.append(q)
        self.send_response(200)
        self.send_header("Content-Type", "text/event-stream; charset=utf-8")
        self.send_header("Cache-Control", "no-cache")
        self.end_headers()
        try:
            self.wfile.write(b": baglanti\n\n")
            self.wfile.flush()
            while True:
                try:
                    olay = q.get(timeout=15)
                    satir = "data: %s\n\n" % json.dumps(
                        olay, ensure_ascii=False)
                    self.wfile.write(satir.encode("utf-8"))
                    self.wfile.flush()
                except queue.Empty:
                    self.wfile.write(b": canli\n\n")   # keep-alive
                    self.wfile.flush()
        except (BrokenPipeError, ConnectionAbortedError, OSError):
            pass
        finally:
            with _KILIT:
                if q in _ABONELER:
                    _ABONELER.remove(q)

    def do_POST(self):
        if self.path.split("?", 1)[0] != "/api/sohbet":
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
        except (ValueError, UnicodeDecodeError):
            self._gonder(400, {"error": "gecersiz json"})
            return
        if not metin or len(metin) > 4000:
            self._gonder(400, {"error": "mesaj bos veya cok uzun"})
            return

        global _SAYAC
        with _KILIT:
            _SAYAC += 1
            istek = _SAYAC
        threading.Thread(target=_sohbet_islet, args=(istek, metin),
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
KISILIK = ""
TOOLS = None


def main():
    global BEYIN, KISILIK, TOOLS
    from basak_app import KISILIK, init_cache
    from brain import Brain
    from tools import TOOLS as _TOOLS
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
