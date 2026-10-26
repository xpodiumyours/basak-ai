"""tests/test_bulut_iscisi_tarayici.py — gerçek Chromium ile adım testleri.

Neden bu dosya: bulut işçisinin karar vermediğini ve yalnız onaylı tek
eylemi uyguladığını tarayıcıda ölçer. Aç → oku → yaz → tıkla → doğrula
→ ekran zinciri gerçek sayfada koşar; belge başka koşuya, adıma, eyleme,
kaynağa veya argümana taşınamaz; aynı belge ikinci kez çalışmaz.

Playwright yoksa modül atlanır: ana CI matrisi tarayıcı indirmez,
`.github/workflows/bulut-iscisi.yml` indirir ve bu dosyayı koşar.
"""

import asyncio
import base64
import logging
import os
import sys
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import urlsplit

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

pytest.importorskip("playwright.async_api")

from worker.guvenlik import TokenHatasi, token_uret  # noqa: E402
from worker.tarayici import BulutTarayici, TarayiciHatasi  # noqa: E402

logger = logging.getLogger(__name__)

ANAHTAR = "test-iscisi-anahtari-32-bayt"

_SAYFA = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><title>Başak Test</title></head>
<body>
<h1 id="baslik">Merhaba</h1>
<div id="icerik">ilk metin</div>
<div id="uzun">{uzun}</div>
<div id="girdi" contenteditable="true"></div>
<button id="dugme"
 onclick="document.getElementById('icerik').textContent='Tıklandı';
          document.title='Tıklandı';">Tıkla</button>
</body></html>"""

_CEREZ_OKU = """<!doctype html>
<html lang="tr"><head><meta charset="utf-8"><title>Çerez</title></head>
<body><div id="cerez"></div>
<script>document.getElementById('cerez').textContent =
 document.cookie || 'bos';</script></body></html>"""


class _Isleyici(BaseHTTPRequestHandler):
    def do_GET(self):
        yol = urlsplit(self.path).path
        if yol == "/cerez-yaz":
            self._gonder("<!doctype html><title>Çerez yaz</title><p>yazildi</p>",
                         cerez="kosu=A; Path=/")
        elif yol == "/cerez-oku":
            self._gonder(_CEREZ_OKU)
        elif yol == "/ikinci":
            self._gonder(
                "<!doctype html><title>İkinci</title><p>ikinci sayfa</p>")
        else:
            self._gonder(_SAYFA.format(uzun="a" * 1_200))

    def _gonder(self, html, cerez=None):
        govde = html.encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.send_header("Content-Length", str(len(govde)))
        if cerez:
            self.send_header("Set-Cookie", cerez)
        self.end_headers()
        self.wfile.write(govde)

    def log_message(self, bicim, *argumanlar):
        logger.debug("test sunucusu: " + bicim, *argumanlar)


@pytest.fixture(scope="module")
def site():
    sunucu = ThreadingHTTPServer(("127.0.0.1", 0), _Isleyici)
    sunucu.daemon_threads = True
    isci = threading.Thread(target=sunucu.serve_forever, daemon=True)
    isci.start()
    kok = "http://127.0.0.1:%d" % sunucu.server_address[1]
    try:
        yield kok
    finally:
        sunucu.shutdown()
        sunucu.server_close()
        isci.join(10)


class Kosucu:
    """Async işçiyi kendi döngüsünde koşturur; testler senkron kalır."""

    def __init__(self, tarayici, dongu):
        self.tarayici = tarayici
        self._dongu = dongu

    def kos(self, koro, zaman=90):
        return asyncio.run_coroutine_threadsafe(koro, self._dongu).result(zaman)


@pytest.fixture(scope="module")
def bulut():
    dongu = asyncio.new_event_loop()
    isci = threading.Thread(
        target=dongu.run_forever, name="bulut-iscisi-dongusu", daemon=True)
    isci.start()
    tarayici = BulutTarayici(
        ANAHTAR, guvenlik=False, azami_oturum=16, oturum_suresi=300)
    try:
        asyncio.run_coroutine_threadsafe(tarayici.basla(), dongu).result(90)
        yield Kosucu(tarayici, dongu)
    finally:
        try:
            asyncio.run_coroutine_threadsafe(
                tarayici.kapat(), dongu).result(30)
        finally:
            dongu.call_soon_threadsafe(dongu.stop)
            isci.join(10)


def _belge(kosu, adim, eylem, url):
    token, _ = token_uret(
        ANAHTAR, kosu_id=kosu, adim_id=adim, tur=eylem["tur"],
        url=url, argumanlar=eylem, ttl=120,
    )
    return token


def _adim(bulut, kosu, adim, eylem, url):
    return bulut.kos(bulut.tarayici.adim(
        kosu, eylem, _belge(kosu, adim, eylem, url), adim_id=adim))


def test_ac_oku_ekran_ve_kirpma(bulut, site):
    kosu = "kosu-ac-oku"
    ac = {"tur": "ac", "url": site + "/"}
    sonuc = _adim(bulut, kosu, "a1", ac, site + "/")
    assert sonuc["ok"] is True
    assert sonuc["baslik"] == "Başak Test"
    assert sonuc["durum"] == 200
    assert sonuc["url"] == site + "/"

    oku = {"tur": "oku", "secici": "#icerik"}
    okuma = _adim(bulut, kosu, "a2", oku, sonuc["url"])
    assert okuma["ok"] is True
    assert okuma["metin"] == "ilk metin"
    assert okuma["kirpildi"] is False

    kirp = {"tur": "oku", "secici": "#uzun", "azami_karakter": 200}
    kirpma = _adim(bulut, kosu, "a3", kirp, sonuc["url"])
    assert len(kirpma["metin"]) == 200
    assert kirpma["kirpildi"] is True
    assert kirpma["uzunluk"] == 1_200

    ekran = {"tur": "ekran"}
    goruntu = _adim(bulut, kosu, "a4", ekran, sonuc["url"])
    assert goruntu["ok"] is True
    assert goruntu["boyut"] > 0
    ham = base64.b64decode(goruntu["png_b64"])
    assert ham.startswith(b"\x89PNG\r\n\x1a\n")


def test_tikla_ve_dogrula(bulut, site):
    kosu = "kosu-tikla"
    ac = {"tur": "ac", "url": site + "/"}
    sayfa = _adim(bulut, kosu, "a1", ac, site + "/")

    tikla = {"tur": "tikla", "secici": "#dugme"}
    sonuc = _adim(bulut, kosu, "a2", tikla, sayfa["url"])
    assert sonuc["ok"] is True
    assert sonuc["baslik"] == "Tıklandı"

    dogrula = {"tur": "dogrula", "secici": "#icerik", "beklenen": "Tıklandı"}
    assert _adim(bulut, kosu, "a3", dogrula, sonuc["url"])["ok"] is True

    yanlis = {"tur": "dogrula", "secici": "#icerik",
              "beklenen": "Tıklanmadı"}
    cevap = _adim(bulut, kosu, "a4", yanlis, sonuc["url"])
    assert cevap["ok"] is False
    assert cevap["gercek"] == "Tıklandı"


def test_yaz_ve_icerik_dogrula(bulut, site):
    kosu = "kosu-yaz"
    ac = {"tur": "ac", "url": site + "/"}
    sayfa = _adim(bulut, kosu, "a1", ac, site + "/")

    yaz = {"tur": "yaz", "secici": "#girdi", "metin": "merhaba dünya"}
    sonuc = _adim(bulut, kosu, "a2", yaz, sayfa["url"])
    assert sonuc["ok"] is True
    assert sonuc["uzunluk"] == len("merhaba dünya")

    dogrula = {"tur": "dogrula", "secici": "#girdi",
               "beklenen": "merhaba dünya"}
    cevap = _adim(bulut, kosu, "a3", dogrula, sayfa["url"])
    assert cevap["ok"] is True
    assert cevap["gercek"] == "merhaba dünya"


def test_ayni_belge_ikinci_kez_calismaz(bulut, site):
    kosu = "kosu-tek-kullanim"
    ac = {"tur": "ac", "url": site + "/"}
    sayfa = _adim(bulut, kosu, "a1", ac, site + "/")

    oku = {"tur": "oku", "secici": "#icerik"}
    token = _belge(kosu, "a2", oku, sayfa["url"])
    ilk = bulut.kos(bulut.tarayici.adim(kosu, oku, token, adim_id="a2"))
    assert ilk["ok"] is True

    with pytest.raises(TokenHatasi, match="daha önce kullanıldı"):
        bulut.kos(bulut.tarayici.adim(kosu, oku, token, adim_id="a2"))


def test_belge_kosu_adim_eylem_kaynak_ve_argumana_bagli(bulut, site):
    a = "kosu-bag-a"
    b = "kosu-bag-b"
    ac = {"tur": "ac", "url": site + "/"}
    sayfa_a = _adim(bulut, a, "a1", ac, site + "/")
    _adim(bulut, b, "b1", ac, site + "/")

    oku = {"tur": "oku", "secici": "#icerik"}
    token = _belge(a, "a2", oku, sayfa_a["url"])

    with pytest.raises(TokenHatasi, match="başka koşu"):
        bulut.kos(bulut.tarayici.adim(b, oku, token, adim_id="a2"))

    with pytest.raises(TokenHatasi, match="başka adım"):
        bulut.kos(bulut.tarayici.adim(a, oku, token, adim_id="baska"))

    with pytest.raises(TokenHatasi, match="başka eylem"):
        bulut.kos(bulut.tarayici.adim(
            a, {"tur": "tikla", "secici": "#dugme"}, token, adim_id="a2"))

    with pytest.raises(TokenHatasi, match="başka argüman"):
        bulut.kos(bulut.tarayici.adim(
            a, {"tur": "oku", "secici": "#baslik"}, token, adim_id="a2"))

    with pytest.raises(TokenHatasi, match="başka kaynak"):
        bulut.kos(bulut.tarayici.adim(
            a, oku,
            _belge(a, "a3", oku, "https://baska-ornek.test/"),
            adim_id="a3"))

    # Reddedilen denemeler nonce'u tüketmez; doğru kullanım hâlâ çalışır.
    assert bulut.kos(
        bulut.tarayici.adim(a, oku, token, adim_id="a2"))["ok"] is True


def test_oturum_yoksa_eylem_reddedilir(bulut, site):
    kosu = "kosu-yok"
    oku = {"tur": "oku", "secici": "#icerik"}
    with pytest.raises(TarayiciHatasi, match="açık tarayıcı oturumu yok"):
        bulut.kos(bulut.tarayici.adim(
            kosu, oku, _belge(kosu, "a1", oku, site + "/"), adim_id="a1"))


def test_lokal_adres_ssrf_engeline_takilir(site):
    tarayici = BulutTarayici(ANAHTAR, guvenlik=True)
    ac = {"tur": "ac", "url": site + "/"}
    token = _belge("ssrf", "a1", ac, site + "/")
    with pytest.raises(TarayiciHatasi, match="adres engellendi"):
        asyncio.run(tarayici.adim("ssrf", ac, token, adim_id="a1"))


def test_kosularin_cerezleri_ayri_kalir(bulut, site):
    a = "kosu-cerez-a"
    b = "kosu-cerez-b"
    ac = {"tur": "ac", "url": site + "/cerez-yaz"}
    _adim(bulut, a, "a1", ac, site + "/cerez-yaz")
    ac_b = {"tur": "ac", "url": site + "/cerez-oku"}
    sayfa_b = _adim(bulut, b, "b1", ac_b, site + "/cerez-oku")

    oku = {"tur": "oku", "secici": "#cerez"}
    a_oku = {"tur": "ac", "url": site + "/cerez-oku"}
    sayfa_a = _adim(bulut, a, "a2", a_oku, site + "/cerez-oku")

    cerez_a = _adim(bulut, a, "a3", oku, sayfa_a["url"])
    assert "kosu=A" in cerez_a["metin"]

    cerez_b = _adim(bulut, b, "b2", oku, sayfa_b["url"])
    assert cerez_b["metin"] == "bos"


def test_bilinmeyen_eylem_ve_eksik_secici(bulut, site):
    kosu = "kosu-hatali"
    with pytest.raises(TarayiciHatasi, match="bilinmeyen eylem"):
        bulut.kos(bulut.tarayici.adim(
            kosu, {"tur": "sil"}, "belge", adim_id="a1"))

    with pytest.raises(TarayiciHatasi, match="koşu kimliği geçersiz"):
        bulut.kos(bulut.tarayici.adim(
            "", {"tur": "oku"}, "belge", adim_id="a1"))

    with pytest.raises(TarayiciHatasi, match="adım kimliği geçersiz"):
        bulut.kos(bulut.tarayici.adim(
            kosu, {"tur": "oku"}, "belge", adim_id=""))

    ac = {"tur": "ac", "url": site + "/"}
    sayfa = _adim(bulut, kosu, "a2", ac, site + "/")

    tikla = {"tur": "tikla"}
    with pytest.raises(TarayiciHatasi, match="tıklama seçici ister"):
        _adim(bulut, kosu, "a3", tikla, sayfa["url"])
