"""Calisma karti ve ust durum — GERCEK tarayicida davranis testi.

web/ klasoru gercek dosyalariyla (index.html + chat.css + app.js +
common.js) Chromium'da acilir; /api/* cevaplari testte taklit edilir.
Olculen sey gorunurluktur (ekranda yer kapliyor mu), dosyadaki metin
degil.

Tarayici (playwright + chromium) kurulu degilse test ATLANIR.
"""

import os
import functools
import glob
import json
import threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import pytest

playwright_api = pytest.importorskip(
    "playwright.sync_api", reason="playwright kurulu degil")

WEB = Path(__file__).resolve().parents[1] / "web"


class _Sessiz(SimpleHTTPRequestHandler):
    def log_message(self, *a):
        pass


@pytest.fixture(scope="module")
def adres():
    sunucu = ThreadingHTTPServer(
        ("127.0.0.1", 0), functools.partial(_Sessiz, directory=str(WEB)))
    t = threading.Thread(target=sunucu.serve_forever, daemon=True)
    t.start()
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
        except Exception as e:
            pytest.skip("chromium acilamadi: %s" % e)
        yield t
        t.close()


def _sayfa(tarayici, adres, durum_ok=True):
    pg = tarayici.new_page()

    def api(route):
        yol = route.request.url.split("?", 1)[0]
        if yol.endswith("/api/kimlik"):
            govde = {"ok": True, "kullanici": "test", "basak_id": "Test"}
        elif yol.endswith("/api/durum"):
            if not durum_ok:
                return route.fulfill(status=503, body="{}",
                                     content_type="application/json")
            govde = {"ok": True, "saglayicilar": ["groq"], "arac_sayisi": 1}
        else:
            govde = {"ok": True, "sohbetler": []}
        route.fulfill(status=200, body=json.dumps(govde),
                      content_type="application/json")

    pg.route("**/api/**", api)
    pg.goto(adres + "/index.html")
    pg.wait_for_function("typeof bubble === 'function'")
    return pg


def _gorunur(pg, secici):
    return pg.evaluate(
        """s => [...document.querySelectorAll(s)]
              .some(e => e.getClientRects().length > 0)""", secici)


def test_calisirken_yonlendir_kutusu_istenmeden_acilmaz(tarayici, adres):
    pg = _sayfa(tarayici, adres)
    pg.evaluate("""() => {
        const b = bubble('assistant', '');
        durumSatiri(b, 'İnternette aranıyor: yapay zeka', 'toolStatus');
        // P2: Yönlendir, sunucudan imzalı devam kaydı gelince açılır.
        balonlar.set('r1', b);
        olayiIsle({istek: 'r1', tur: 'runState', handoff_token: 'imza'});
    }""")
    assert not _gorunur(pg, ".work-redirect-form")
    pg.get_by_role("button", name="Yönlendir").click()
    assert _gorunur(pg, ".work-redirect-form")
    pg.close()


def test_is_bitince_yanit_yaziliyor_satiri_ve_plan_kalmaz(tarayici, adres):
    pg = _sayfa(tarayici, adres)
    pg.evaluate("""() => {
        const b = bubble('assistant', '');
        planiGuncelle(b, [{baslik: 'İnternette aranıyor'},
                          {baslik: 'Derin okunuyor'}]);
        durumSatiri(b, 'İnternette aranıyor: yapay zeka', 'toolStatus');
        durumSatiri(b, 'Derin okunuyor: https://tr.wikipedia.org/wiki/X',
                    'toolStatus');
        calismaYanitaGecti(b);
        icerikYaz(b, 'cevap');
        calismaBitir(b);
    }""")
    assert "adım tamamlandı" in pg.locator(".work-title").inner_text()
    assert not _gorunur(pg, ".work-current")
    assert not _gorunur(pg, ".work-plan")
    assert not _gorunur(pg, ".work-steps")
    # Ayrinti isteyen acar: adimlar ve plan geri gelir.
    pg.get_by_role("button", name="Detaylar").click()
    assert _gorunur(pg, ".work-steps")
    assert _gorunur(pg, ".work-plan")
    pg.close()


def test_ust_durum_saglikliyken_gorunmez(tarayici, adres):
    pg = _sayfa(tarayici, adres, durum_ok=True)
    pg.wait_for_function(
        "document.getElementById('healthDot').classList.contains('ok')")
    # Olcum bos gecmesin: oge sayfada VAR olmali, yalniz gorunmemeli.
    assert pg.locator("#healthStatus").count() == 1
    assert not _gorunur(pg, "#healthStatus")
    pg.close()


def test_ust_durum_baglanti_sorununu_gosterir(tarayici, adres):
    pg = _sayfa(tarayici, adres, durum_ok=False)
    pg.wait_for_function(
        "!document.getElementById('healthStatus').hidden")
    assert _gorunur(pg, "#healthStatus")
    metin = pg.locator("#healthStatus").inner_text()
    assert "Hazır" not in metin
    assert metin.strip()
    pg.close()


def test_mola_karti_uc_secenek_sunar_durdur_kalkar(tarayici, adres):
    pg = _sayfa(tarayici, adres)
    pg.evaluate("""() => {
        const b = bubble('assistant', '');
        durumSatiri(b, 'Şirket bilgisi araştırılıyor: Nari Tekstil',
                    'toolStatus');
        balonlar.set('r2', b);
        olayiIsle({istek: 'r2', tur: 'runState', handoff_token: 'imza'});
        olayiIsle({istek: 'r2', tur: 'checkpoint', adim: 3});
    }""")
    assert "Mola" in pg.locator(".work-title").inner_text()
    assert "nasıl devam edelim" in pg.locator(".work-summary").last.inner_text()
    for ad in ("Devam et", "Bulduklarınla cevap ver", "Yönlendir"):
        assert pg.get_by_role("button", name=ad).is_enabled()
    assert pg.get_by_role("button", name="Durdur").count() == 0
    yol = os.environ.get("BASAK_EKRAN_GORUNTUSU")
    if yol:
        pg.locator(".message-row.assistant").last.screenshot(path=yol)
    pg.close()
