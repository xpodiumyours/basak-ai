"""İşçi sağlık ucu — yalnız 127.0.0.1'e bağlanır.

Neden: Oracle VM'de 80/443 açılmıyor ve işçi internete kapalı olmalı.
Sağlık kontrolü aynı makineden (Docker healthcheck) okunur; dışarıya
servis açmaz. `veri_uret` her istekte taze kalp/kuyruk özeti döndürür.
"""

import json
import logging
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

logger = logging.getLogger(__name__)

_YOLLAR = ("/saglik", "/health")


def saglik_yaniti(veri_uret):
    """Sağlık gövdesini üretir; üretici patlarsa açık hata döner."""
    try:
        veri = veri_uret()
        if not isinstance(veri, dict):
            raise TypeError("sağlık verisi sözlük değil")
        return veri
    except Exception as hata:
        logger.warning("sağlık verisi üretilemedi", exc_info=True)
        return {"ok": False, "hata": str(hata)[:300]}


def sunucu_baslat(port, veri_uret, adres="127.0.0.1"):
    """Arka planda HTTP sunucusu başlatır; `httpd.shutdown()` ile durur."""

    class _Isleyici(BaseHTTPRequestHandler):
        server_version = "BasakIsci/1"

        def do_GET(self):  # noqa: N802 — BaseHTTPRequestHandler sözleşmesi
            if urlsplit(self.path).path not in _YOLLAR:
                self.send_error(404, "yol yok")
                return
            veri = saglik_yaniti(veri_uret)
            govde = json.dumps(
                veri, ensure_ascii=False, default=str,
            ).encode("utf-8")
            self.send_response(200 if veri.get("ok") else 503)
            self.send_header(
                "Content-Type", "application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(govde)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            self.wfile.write(govde)

        def log_message(self, bicim, *args):
            logger.debug("sağlık: " + bicim, *args)

    httpd = ThreadingHTTPServer((adres, int(port)), _Isleyici)
    httpd.daemon_threads = True
    ip, gercek_port = httpd.server_address[:2]
    is_parcacigi = threading.Thread(
        target=httpd.serve_forever, name="basak-isci-saglik", daemon=True)
    is_parcacigi.start()
    logger.info("sağlık ucu: http://%s:%s/saglik", ip, gercek_port)
    return httpd
