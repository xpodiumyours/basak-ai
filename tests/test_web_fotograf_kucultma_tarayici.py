"""Fotoğraf küçültme — GERÇEK tarayıcıda ölçüm (fatura + sohbet ekranı).

Ölçülen sorun (2026-10-13): sunucu gövdesinin tavanı ~4,5 MB (Vercel).
8 MP bir telefon fotoğrafı ham hâlde base64 ile ~8-11 MB olur ve istek
uca HİÇ ulaşmaz (HTTP 413 FUNCTION_PAYLOAD_TOO_LARGE). Sohbet ekranı
(`web/app.js`) fotoğrafı tarayıcıda küçültüyordu; `/fatura` ekranı HAM
gönderiyordu — yani tam o işin üstünde duvar duruyordu.

Bu test iki ekranı da Chromium'da açar, GERÇEK bir 8 MP fotoğraf seçer ve
sunucuya giden gövdenin boyutunu ölçer. "Dosyada şu kelime var mı" değil,
"ağa ne kadar veri çıktı" sorusunun cevabıdır.

Tarayıcı (playwright + chromium) kurulu değilse test ATLANIR ve atlama
nedeni pytest çıktısında görünür.
"""

import base64
import functools
import glob
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from io import BytesIO
from pathlib import Path

import pytest

playwright_api = pytest.importorskip(
    "playwright.sync_api", reason="playwright kurulu degil")

WEB = Path(__file__).resolve().parents[1] / "web"

# Vercel gövde tavanı: 2026-10-13'te 5,05 MB gövde ile ölçüldü → 413.
HAM_TAVAN = int(4.5 * 1024 * 1024)
# Küçültmeden sonra kabul ölçütü. Ölçülen en kötü hâl (gürültülü, yani
# sıkıştırılamayan 8 MP fotoğraf): gövde 0,90 MB — yani tavanın ~5 kat
# altı. 1,5 MB sınırı hem bu payı korur hem de gerçek fatura fotoğrafında
# (kağıt, düşük gürültü) rahatça altında kalır.
KUCUK_TAVAN = int(1.5 * 1024 * 1024)
# Küçültme hedefi (common.js): en büyük kenar 1600 px.
HEDEF_KENAR = 1600


class _Sessiz(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def adres():
    sunucu = ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(_Sessiz, directory=str(WEB)))
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    yield "http://127.0.0.1:%d" % sunucu.server_address[1]
    sunucu.shutdown()


@pytest.fixture(scope="module")
def tarayici():
    with playwright_api.sync_playwright() as p:
        yol = sorted(glob.glob(
            "/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
        try:
            t = p.chromium.launch(
                **({"executable_path": yol[-1]} if yol else {}))
        except Exception as e:  # tarayici ikili dosyasi yoksa
            pytest.skip("chromium acilamadi: %s" % e)
        yield t
        t.close()


def _sekiz_mp_fotograf(yol):
    """3264x2448 (=8,0 MP) gürültü fotoğrafı üretir; byte boyunu döner.

    Gürültü bilinçli: JPEG onu sıkıştıramaz, dosya gerçek telefon
    fotoğrafı boyutuna (tavanı aşacak kadar) çıkar.
    """
    import os as _os

    from PIL import Image

    gen, yuk = 3264, 2448
    ham = _os.urandom(gen * yuk * 3)
    Image.frombytes("RGB", (gen, yuk), ham).save(yol, format="JPEG",
                                                 quality=90)
    return yol.stat().st_size


def _api_taklit(route, kayit):
    yol = route.request.url.split("?", 1)[0]
    if yol.endswith("/api/kimlik"):
        return route.fulfill(
            status=200, content_type="application/json",
            body=json.dumps({"ok": True, "kullanici": "test",
                             "basak_id": "Test"}))
    if yol.endswith("/api/fatura-oku"):
        kayit.append(route.request.post_data or "")
        return route.fulfill(
            status=200, content_type="application/json",
            body=json.dumps({
                "kaynak": "foto", "ustbilgi": {}, "satirlar": [],
                "denetim": [], "eksik": [], "yazi": "",
                "okuma": {"ok": True, "kaynak": "test",
                          "model": "test-model"},
                "fatura_id": "gln_test"}))
    return route.fulfill(status=200, content_type="application/json",
                         body=json.dumps({"ok": True, "sohbetler": [],
                                          "runtime": "vercel"}))


def test_fatura_ekrani_buyuk_fotografi_kucultup_gonderir(
        tarayici, adres, tmp_path):
    foto = tmp_path / "sekiz-mp.jpg"
    ham_boy = _sekiz_mp_fotograf(foto)
    ham_data_url = len(base64.b64encode(foto.read_bytes())) + 23
    assert ham_data_url > HAM_TAVAN, (
        "test anlamli olmali: ham govde tavana carpmali (%d bayt)" % ham_boy)

    pg = tarayici.new_page()
    kayit = []
    pg.route("**/api/**", lambda route: _api_taklit(route, kayit))
    pg.goto(adres + "/fatura.html")
    pg.wait_for_function(
        "document.getElementById('gonder').disabled === false")
    pg.set_input_files("#dosya", str(foto))
    pg.click("#gonder")
    pg.wait_for_function(
        "document.getElementById('durumFoto')"
        ".textContent.includes('okundu')",
        timeout=30000)

    assert kayit, "fatura ucu hic cagrilmadi"
    govde_metni = kayit[-1]
    govde = json.loads(govde_metni)
    assert govde["b64"].startswith("data:image/jpeg;base64,")
    assert len(govde_metni.encode("utf-8")) < KUCUK_TAVAN, (
        "govde hala buyuk: %d bayt" % len(govde_metni.encode("utf-8")))

    from PIL import Image

    gorsel = Image.open(BytesIO(base64.b64decode(govde["b64"].split(",", 1)[1])))
    assert max(gorsel.size) == HEDEF_KENAR, gorsel.size
    assert pg.locator("#durumFoto").inner_text().strip().endswith("okundu")
    pg.close()


def test_sohbet_ekrani_ayni_kucultmeyi_kullanir(tarayici, adres, tmp_path):
    """`web/app.js` küçültmeyi `common.js`ten çağırır; davranış aynı kalır."""
    foto = tmp_path / "sekiz-mp.jpg"
    _sekiz_mp_fotograf(foto)

    pg = tarayici.new_page()
    kayit = []
    pg.route("**/api/**", lambda route: _api_taklit(route, kayit))
    pg.goto(adres + "/index.html")
    pg.wait_for_function("typeof window.basakFotografiKucult === 'function'")
    pg.wait_for_function("typeof gorseliDataUrl === 'function'")
    pg.set_input_files("#image", str(foto))
    veri = pg.evaluate(
        "async () => await gorseliDataUrl("
        "document.getElementById('image').files[0])")
    assert veri.startswith("data:image/jpeg;base64,")
    assert len(veri) < KUCUK_TAVAN, "sohbet yolu kucultmuyor: %d" % len(veri)

    from PIL import Image

    assert max(Image.open(BytesIO(base64.b64decode(veri.split(",", 1)[1]))).size) \
        == HEDEF_KENAR
    pg.close()
