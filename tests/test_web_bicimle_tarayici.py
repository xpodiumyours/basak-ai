"""Web cevap bicimi — GERCEK tarayicida davranis testi.

web/app.js icindeki gercek bicimle() kodu Chromium'da calistirilir ve
olusan sayfa agaci (DOM) olculur: "dosyada su kelime var mi" degil,
"ekranda baslik baslik mi, liste liste mi" sorusu.

Tarayici (playwright + chromium) kurulu degilse test ATLANIR ve atlama
nedeni pytest ciktisinda gorunur.
"""

import glob
import os
from pathlib import Path

import pytest

playwright_api = pytest.importorskip(
    "playwright.sync_api", reason="playwright kurulu degil")

KOK = Path(__file__).resolve().parents[1]
BAS = "function kacis("
SON = "function icerikYaz("


def _bicim_kodu():
    """app.js'ten bicim fonksiyonlarini (kacis..icerikYaz dahil) al."""
    kaynak = (KOK / "web" / "app.js").read_text(encoding="utf-8")
    bas = kaynak.index(BAS)
    son = kaynak.index(SON)
    # icerikYaz'in govdesini de al: ilk "\n}\n" kapanisina kadar.
    son = kaynak.index("\n}\n", son) + 3
    return kaynak[bas:son]


def _chromium_yolu():
    for desen in ("/opt/pw-browsers/chromium-*/chrome-linux/chrome",):
        bulunan = sorted(glob.glob(desen))
        if bulunan:
            return bulunan[-1]
    return None


@pytest.fixture(scope="module")
def sayfa():
    with playwright_api.sync_playwright() as p:
        try:
            yol = _chromium_yolu()
            tarayici = p.chromium.launch(
                **({"executable_path": yol} if yol else {}))
        except Exception as e:  # tarayici ikili dosyasi yoksa
            pytest.skip("chromium acilamadi: %s" % e)
        pg = tarayici.new_page()
        pg.set_content("<div id='b'></div>")
        pg.add_script_tag(content=_bicim_kodu())
        yield pg
        tarayici.close()


def _ciz(sayfa, metin, rol="assistant"):
    sayfa.evaluate(
        """([metin, rol]) => {
            const b = document.getElementById('b');
            b.innerHTML = '';
            b.dataset.rol = rol;
            icerikYaz(b, metin);
        }""",
        [metin, rol],
    )
    return sayfa.locator("#b .icerik")


def test_ekran_goruntusundeki_cevap_duzgun_gorunur(sayfa):
    metin = (
        "### 5. Züccaciye ve Hediyelik Eşya\n"
        "* **Tahtakale (Eminönü):** İstanbul'un en eski ticaret merkezidir.\n"
        "\n---\n\n"
        "### Dijital İzlerini Nasıl Bulabilirsin?\n"
        "1. **Lonca.co:** Merter ve Laleli toptancıları.\n"
        "2. **TurkishExporter:** İhracat kapasiteleri.\n"
    )
    ic = _ciz(sayfa, metin)
    basliklar = ic.locator("h5")
    assert basliklar.count() == 2
    assert basliklar.nth(0).inner_text() == "5. Züccaciye ve Hediyelik Eşya"
    assert ic.locator("ul > li > strong").inner_text() == \
        "Tahtakale (Eminönü):"
    assert ic.locator("hr").count() == 1
    assert ic.locator("ol > li").count() == 2
    gorunen = ic.inner_text()
    for ham in ("###", "**", "---"):
        assert ham not in gorunen, ham
    assert not gorunen.lstrip().startswith("*")


def test_numarali_liste_araya_yazi_girince_numara_korunur(sayfa):
    ic = _ciz(sayfa, "1. bir\n\nAçıklama\n\n2. iki")
    listeler = ic.locator("ol")
    assert listeler.count() == 2
    assert listeler.nth(1).get_attribute("start") == "2"


def test_ic_ice_liste(sayfa):
    ic = _ciz(sayfa, "- ana\n  - alt 1\n  - alt 2\n- ana 2")
    assert ic.locator(":scope > ul > li").count() == 2
    assert ic.locator("ul > li > ul > li").count() == 2


def test_tablo(sayfa):
    ic = _ciz(sayfa, "| Ad | Fiyat |\n|---|---:|\n| Çay | 10 |\n| Kahve | 20 |")
    assert ic.locator("table th").all_inner_texts() == ["Ad", "Fiyat"]
    assert ic.locator("table tbody tr").count() == 2


def test_kod_blogu_icerigi_bicimlenmez(sayfa):
    ic = _ciz(sayfa, "```\n# baslik degil\n* madde degil\n```")
    assert ic.locator("pre code").inner_text() == \
        "# baslik degil\n* madde degil"
    assert ic.locator("h3, h4, h5, ul").count() == 0


def test_yarim_akan_kod_blogu_hata_vermez(sayfa):
    ic = _ciz(sayfa, "Örnek:\n```\nsatir 1")
    assert ic.locator("pre code").inner_text() == "satir 1"


def test_zararli_icerik_calismaz(sayfa):
    ic = _ciz(
        sayfa,
        "<img src=x onerror=\"window.x=1\">\n"
        "[tikla](javascript:alert(1))\n"
        "[iyi](https://example.com/a?b=1&c=2)",
    )
    assert ic.locator("img").count() == 0
    assert sayfa.evaluate("window.x") is None
    linkler = ic.locator("a")
    assert linkler.count() == 1
    assert linkler.get_attribute("href") == "https://example.com/a?b=1&c=2"
    assert linkler.get_attribute("rel") == "noopener noreferrer"


def test_kullanici_mesaji_eskisi_gibi_kalir(sayfa):
    ic = _ciz(sayfa, "### not başlık\n* not madde", rol="user")
    assert ic.locator("h5, ul").count() == 0
    assert ic.inner_text() == "### not başlık\n* not madde"


def test_carpma_isareti_egik_yaziya_donmez(sayfa):
    ic = _ciz(sayfa, "2*3*4 = 24 ve *vurgu* burada")
    assert ic.locator("em").all_inner_texts() == ["vurgu"]
    assert "2*3*4" in ic.inner_text()
