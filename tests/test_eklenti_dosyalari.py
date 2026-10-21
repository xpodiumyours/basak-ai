"""tests/test_eklenti_dosyalari.py — eklenti dosya sozlesmesi.

Tarayici calistirmadan denetlenebilen seyler burada kilitlenir:

1. `manifest.json` gecerli JSON ve MV3; isaret ettigi her dosya var.
2. Uzaktan kod yok (MV3 + magaza kurali): panelde satir ici script yok,
   betikler yalniz yerel dosyadan yuklenir.
3. Izinler beklenen kume; sessizce genisletilemez.
4. Icerik betigi cekirdegin bekledigi alanlari uretir (rol/ad/deger/
   gorunur/kapali) — aksi halde gozlem sessizce bos gorunur.
5. Eklentinin kendi icinde ajan dongusu/model cagrisi yok (tek beyin).
"""

import json
import os
import re

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
EKLENTI = os.path.join(KOK, "eklenti")


def _oku(ad):
    with open(os.path.join(EKLENTI, ad), encoding="utf-8") as f:
        return f.read()


def test_manifest_gecerli_ve_mv3():
    manifest = json.loads(_oku("manifest.json"))
    assert manifest["manifest_version"] == 3
    assert manifest["name"].strip()
    assert manifest["version"].count(".") >= 1


def test_manifest_isaret_ettigi_dosyalar_var():
    manifest = json.loads(_oku("manifest.json"))
    yollar = [manifest["background"]["service_worker"],
              manifest["side_panel"]["default_path"]]
    for betik in manifest["content_scripts"]:
        yollar.extend(betik["js"])
    for yol in yollar:
        assert os.path.exists(os.path.join(EKLENTI, yol)), yol


def test_izinler_beklenen_kume():
    manifest = json.loads(_oku("manifest.json"))
    assert set(manifest["permissions"]) == {
        "storage", "tabs", "scripting", "sidePanel"}
    # wss:// sart: eklenti artik BULUT kanalina baglanir (2026-10-21).
    # ws://127.0.0.1 yalniz yerel gelistirme icin listede kalir.
    assert set(manifest["host_permissions"]) == {
        "http://*/*", "https://*/*",
        "ws://127.0.0.1/*", "http://127.0.0.1/*",
        "wss://basak-vercel.vercel.app/*",
        "https://basak-vercel.vercel.app/*"}


def test_panelde_satir_ici_script_yok():
    html = _oku("panel.html")
    for etiket in re.findall(r"<script[^>]*>", html, re.IGNORECASE):
        assert "src=" in etiket, etiket
    assert not re.search(r"\son[a-z]+\s*=", html, re.IGNORECASE), \
        "satir ici olay ozniteligi (CSP ihlali)"


def test_uzaktan_kod_yok():
    for ad in ("icerik.js", "arka.js", "panel.js"):
        kaynak = _oku(ad)
        assert not re.search(r"\beval\s*\(", kaynak), ad
        assert not re.search(r"new\s+Function\s*\(", kaynak), ad
        assert not re.search(r"import\s*\(\s*['\"]http", kaynak), ad


def test_icerik_betigi_cekirdegin_alanlarini_uretir():
    kaynak = _oku("icerik.js")
    for alan in ("rol", "ad", "deger", "gorunur", "kapali"):
        assert alan + ":" in kaynak or "'" + alan + "'" in kaynak, alan
    assert "password" in kaynak, "sifre alani ayrimi kaybolmus"
    assert "__basakGozlem" in kaynak


def test_baglanti_canli_tutulur():
    """MV3 servis calisani bosta olur: acik kanal ping ile ayakta kalir.

    Ping olmazsa kanal ~30 saniyede duser ve Basak "tarayici bagli degil"
    der — kullanici bunu hata sanir. Sunucu islemsiz mesaji yutar.
    """
    kaynak = _oku("arka.js")
    assert "setInterval" in kaynak
    assert "ping" in kaynak
    assert "clearInterval" in kaynak


def test_icerik_betigi_tiklama_ve_yazma_tasir():
    """Eklenti EL'dir: iki eylem de icerik betiginde karsilanir.

    `sira` alani olmadan cekirdegin ref'i ogeye baglanamaz; `tikla`/`yaz`
    olmadan sayfa_bakis yalniz goz olur, eli olmaz.
    """
    kaynak = _oku("icerik.js")
    assert "sira:" in kaynak, "gozlem kalici oge kimligi tasimiyor"
    assert 'mesaj.tip === "tikla"' in kaynak
    assert 'mesaj.tip === "yaz"' in kaynak
    assert "__basakTikla" in kaynak and "__basakYaz" in kaynak


def test_arka_betigi_eylemleri_yonlendirir():
    kaynak = _oku("arka.js")
    assert 'mesaj.islem === "sayfa_tikla"' in kaynak
    assert 'mesaj.islem === "sayfa_yaz"' in kaynak


def test_yeniden_baglanma_sinirsizdir():
    """Vercel baglantiyi 300 sn'de kapatir; tek denemeden sonra vazgecmek
    eklentiyi kalici olarak olu birakirdi."""
    kaynak = _oku("arka.js")
    assert "if (deneme > 0) return;" not in kaynak, \
        "ilk basarisiz denemeden sonra yeniden baglanma duruyor"
    assert "yenidenZaman" in kaynak


def test_panel_gecmisi_her_mesajla_gonderir():
    """Bulutta kalici disk yok: konusma gecmisi istemciden tasinir."""
    kaynak = _oku("panel.js")
    assert "GECMIS" in kaynak
    assert "gecmis:" in kaynak


def test_eklentide_ajan_dongusu_yok():
    """Tek beyin kurali: eklenti model cagirmaz, saglayici bilmez."""
    for ad in ("icerik.js", "arka.js", "panel.js"):
        kaynak = _oku(ad).lower()
        for yasak in ("openai", "groq", "gemini", "openrouter", "api key",
                      "api_key", "authorization"):
            assert yasak not in kaynak, (ad, yasak)
