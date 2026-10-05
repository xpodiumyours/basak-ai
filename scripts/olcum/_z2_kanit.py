"""_z2_kanit.py — Z2 kabul probu (2026-10-01, D4b = B).

Gerçek `web/index.html` + `web/app.js` + `web/chat.css` **gerçek sunucu
çıktısıyla** sürülür. Sunucu kurulmaz: Playwright route intercept ile
dosyalar diskten servis edilir.

Kapsam doğrusu (dürüst sınır): model anahtarı olmadan canlı sohbet
koşmadığı için SSE taşıyıcısı taklit edilir. Kartın verisi
`chat/tools.py:_harita_olayi` tarafından üretilmiş GERÇEK çıktıdır
(Z1 canlı Photon çağrısı); kartın DOM'u ve CSS'i tamamen gerçek
proje kodudur. Ekran görüntüleri kök dizindeki `_z2_kanit/` klasörüne
yazılır.

Çalıştırma: `python3 scripts/olcum/_z2_kanit.py`
"""

import json
import pathlib
import sys
from urllib.parse import unquote, urlparse

from playwright.sync_api import sync_playwright

# Depo kokunu __file__ uzerinden bul; calisma dizinine bagimli degildir.
KOK = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

WEB = KOK / "web"
CIKTI = KOK / "_z2_kanit"
CIKTI.mkdir(exist_ok=True)


def olaylari_uret():
    """Gerçek araç çıktısından gerçek `harita` olaylarını üretir.

    Z1 canlı Photon çağrısıdır (ağ açık). Z0 saf URL üretimidir.
    Olay listesi tarayıcıya SSE ile gelen çerçevenin birebiridir.
    """
    from tools import calistir
    from chat import tools as ct

    olaylar = [
        {"tur": "thinking", "istek": 1},
        {"tur": "toolStatus", "istek": 1,
         "metin": "Konum koordinatı çözülüyor: Kadıköy Moda Sahili"},
    ]
    for sonuc in (calistir("konum_coz", {"adres": "Kadıköy Moda Sahili"}),
                  calistir("harita_goster",
                           {"konum": "Tuzla, İstanbul", "mod": "yol"})):
        veri = sonuc.get("result")
        ad = ("konum_coz" if '"enlem"' in str(veri) else "harita_goster")
        o = ct._harita_olayi(ad, sonuc)
        if o:
            olaylar.append(dict(o, tur="harita", istek=1))
    cevap = ("Kadıköy Moda Sahili bulundu. Koordinatları ve harita "
             "bağlantısını aşağıda bıraktım.")
    olaylar.append({"tur": "parca", "istek": 1, "metin": cevap})
    olaylar.append({"tur": "bitir", "istek": 1, "cevap": cevap})
    return olaylar


OLAYLAR = olaylari_uret()

KONSOL = []
BASARISIZ = []


def rota(route):
    istek = route.request
    parca = urlparse(istek.url)
    yol = unquote(parca.path)          # sorgu dizesi (?v=20) dosya adinda degil
    if yol in ("", "/"):
        yol = "/index.html"
    hedef = WEB / yol.lstrip("/")
    if hedef.is_file():
        govde = hedef.read_bytes()
        tur = ("text/html" if hedef.suffix == ".html"
               else "text/css" if hedef.suffix == ".css"
               else "application/javascript")
        route.fulfill(status=200, content_type=tur + "; charset=utf-8",
                      body=govde)
        return
    if yol.startswith("/api/"):
        route.fulfill(status=200, content_type="application/json",
                      body='{"ok":true}')
        return
    BASARISIZ.append(istek.url)
    route.fulfill(status=404, body="")


with sync_playwright() as p:
    tarayici = p.chromium.launch(args=["--no-sandbox"])
    sayfa = tarayici.new_page(viewport={"width": 1100, "height": 900})
    sayfa.on("console", lambda m: KONSOL.append("%s: %s" % (m.type, m.text)))
    sayfa.on("requestfailed", lambda r: BASARISIZ.append(r.url))
    sayfa.route("**/*", rota)

    sayfa.goto("http://basak.local/", wait_until="networkidle")

    # Gerçek olay akışını gerçek işleyiciye ver.
    sayfa.evaluate(
        "(olaylar) => olaylar.forEach((o) => olayiIsle(o))", OLAYLAR)
    sayfa.wait_for_timeout(600)

    kart = sayfa.evaluate("""() => {
      const k = document.querySelector('.map-card');
      if (!k) return null;
      const r = k.getBoundingClientRect();
      const a = k.querySelector('.map-card-open');
      return {
        ad: k.querySelector('.map-card-title')?.textContent || null,
        koordinat: k.querySelector('.map-card-coords')?.textContent || null,
        atf: k.querySelector('.map-card-attribution')?.textContent || null,
        dugme: a?.textContent || null,
        href: a?.getAttribute('href') || null,
        rel: a?.getAttribute('rel') || null,
        hedef: a?.getAttribute('target') || null,
        genislik: Math.round(r.width), yukseklik: Math.round(r.height),
        gorunur: r.width > 0 && r.height > 0,
        kartSayisi: document.querySelectorAll('.map-card').length,
        atifliKart: document.querySelectorAll('.map-card-attribution').length,
        bolumGizli: document.querySelector('.map-cards')?.hidden,
        govdeUzunluk: document.body.scrollHeight,
        tasma: document.documentElement.scrollWidth >
                 document.documentElement.clientWidth,
      };
    }""")
    print("KART:", json.dumps(kart, ensure_ascii=False, indent=2))

    sayfa.screenshot(path=str(CIKTI / "z2_masaustu.png"), full_page=True)
    sayfa.set_viewport_size({"width": 390, "height": 780})
    sayfa.wait_for_timeout(300)
    mobil = sayfa.evaluate("""() => {
      const a = document.querySelector('.map-card-open');
      const r = a.getBoundingClientRect();
      return { dugmeYuksekligi: Math.round(r.height),
               tasma: document.documentElement.scrollWidth >
                      document.documentElement.clientWidth };
    }""")
    print("MOBIL:", json.dumps(mobil, ensure_ascii=False))
    sayfa.screenshot(path=str(CIKTI / "z2_mobil.png"), full_page=True)

    harici = sayfa.evaluate(
        "() => performance.getEntriesByType('resource')"
        ".map(e => e.name).filter(n => !n.startsWith("
        "'http://basak.local/'))")
    print("HARICI ISTEK:", harici)
    print("KONSOL HATASI:", [k for k in KONSOL if k.startswith("error")])
    print("BASARISIZ ISTEK:", BASARISIZ)
    tarayici.close()

print("GORSELLER:", sorted(x.name for x in CIKTI.glob("*.png")))
