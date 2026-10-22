# -*- coding: utf-8 -*-
"""_eklenti_kart_kanit.py — eklenti kartinin mobil gizleme kurali kaniti (2026-10-22).

Sikayet: telefonla acilinca ilk ekrani "Başak'ı tarayıcında yanına al"
karti karsiliyordu — telefonda eklenti KURULAMAZ (chrome://extensions
yok, arac cubugu simgesi yok), yani uygulanamaz kurulum adimi gosteriyordu.

Kural: kart yalniz kurulum mumkun olan (masaustu) tarayicida gorunur;
telefon/tablette HIC gorunmez. Masaustu davranisi aynen kalir.

Bu prova GERCEK web/index.html + eklenti-kart.js + app.js'i surer
(sunucu kurulmaz; Playwright route intercept ile dosyalar ve /api
cevaplari sahte sunucudan gelir) ve iki ortami olcer:

  MOBIL   (Pixel 7 benzeri): kart gizli, durum metni bos (hic yazilmadi),
            hero gorunur, yatay tasma yok, konsol hatasi yok.
  MASAUSTU: kart gorunur, "kurulu görünmüyor" + uc adim gorunur.

Olculen her iddia konsola sayi olarak yazilir; herhangi biri yanlissa
betik 1 cikis koduyla biter. Ekran goruntuleri `_eklenti_kart_kanit/`
altina dusar. Calistirma: `python scripts/olcum/_eklenti_kart_kanit.py`
"""

import json
import pathlib
import sys
from urllib.parse import unquote, urlparse

from playwright.sync_api import sync_playwright

KOK = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

WEB = KOK / "web"
CIKTI = KOK / "_eklenti_kart_kanit"
CIKTI.mkdir(exist_ok=True)

MOBIL_UA = ("Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/120.0.0.0 Mobile Safari/537.36")
MASAUSTU_UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
               "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")

KONSOL = []
BASARISIZ = []


def _rota(route):
    istek = route.request
    parca = urlparse(istek.url)
    yol = unquote(parca.path)

    if yol.startswith("/api/"):
        if yol == "/api/kimlik":
            govde = {"ok": True, "kullanici": "kanit", "basak_id": "kanit"}
        elif yol == "/api/sohbetler":
            govde = {"ok": True, "sohbetler": []}
        else:
            govde = {"ok": True}
        route.fulfill(status=200, content_type="application/json",
                      body=json.dumps(govde, ensure_ascii=False))
        return

    if yol == "/favicon.ico":
        route.fulfill(status=204, body="")
        return

    if yol in ("", "/"):
        yol = "/index.html"
    hedef = WEB / yol.lstrip("/")
    if hedef.is_file():
        icerik = ("text/html" if hedef.suffix == ".html"
                  else "text/css" if hedef.suffix == ".css"
                  else "application/javascript")
        route.fulfill(status=200,
                      content_type=icerik + "; charset=utf-8",
                      body=hedef.read_bytes())
        return
    if istek.url.startswith("http"):
        BASARISIZ.append(istek.url)
    route.fulfill(status=404, body="")


def _ekran(sayfa):
    return sayfa.evaluate("""() => {
      const kart = document.getElementById('eklentiKarti');
      return {
        kartVar: !!kart,
        kartGorunur: kart ? !kart.hidden : false,
        durum: (document.getElementById('eklentiDurum')||{}).textContent || '',
        adimlarGorunur: kart
          ? !kart.querySelector('#eklentiAdimlar').hidden : false,
        hero: (document.querySelector('h1')||{}).textContent || '',
        tasma: document.documentElement.scrollWidth >
               document.documentElement.clientWidth,
      };
    }""")


SONUCLAR = []


def _olc(ad, deger):
    SONUCLAR.append((ad, deger))
    print("OLCUM %s = %s" % (ad, json.dumps(deger, ensure_ascii=False)))


def _kayit(pencere, ad):
    yol = CIKTI / (ad + ".png")
    pencere.screenshot(path=str(yol), full_page=True)
    print("GORUNTU %s" % yol)


with sync_playwright() as p:
    tarayici = p.chromium.launch(args=["--no-sandbox"])

    # ── MOBIL: kart HIC gorunmemeli ──
    mobil = tarayici.new_context(
        viewport={"width": 390, "height": 844},
        user_agent=MOBIL_UA,
        is_mobile=True,
        has_touch=True,
        device_scale_factor=3,
        locale="tr-TR",
    )
    sayfa = mobil.new_page()
    sayfa.on("console", lambda m: KONSOL.append(
        (m.type, m.text, (m.location or {}).get("url", ""))))
    sayfa.on("requestfailed",
             lambda r: BASARISIZ.append(r.url)
             if r.url.startswith("http") else None)
    sayfa.route("**/*", _rota)
    sayfa.goto("http://basak.local/", wait_until="networkidle")
    sayfa.wait_for_timeout(1200)  # sinyal denemesi (1500 ms tavan) bitsin

    m = _ekran(sayfa)
    _olc("mobil_kart_yok", m["kartVar"] and not m["kartGorunur"])
    _olc("mobil_kart_hic_yazi_yazmadi", m["durum"] == "")
    # Baslik tipografik kesme isaretiyle yazar (U+2019): "Başak’a sor."
    _olc("mobil_hero_gorunur", "Başak\u2019a sor" in m["hero"])
    _olc("mobil_yatay_tasma_yok", not m["tasma"])
    _kayit(sayfa, "mobil_ekran")

    hata_konsol = [k for k in KONSOL if k[0] == "error"]
    _olc("mobil_konsol_hatasi_yok", not hata_konsol)
    _olc("mobil_basarisiz_istek_yok", not BASARISIZ)
    mobil.close()

    # ── MASAUSTU: kart eski davranisiyla gorunur kalmali ──
    masaustu = tarayici.new_context(
        viewport={"width": 1280, "height": 900},
        user_agent=MASAUSTU_UA,
        locale="tr-TR",
    )
    sayfa = masaustu.new_page()
    sayfa.route("**/*", _rota)
    sayfa.goto("http://basak.local/", wait_until="networkidle")
    sayfa.wait_for_timeout(1200)

    d = _ekran(sayfa)
    _olc("masaustu_kart_gorunur", d["kartVar"] and d["kartGorunur"])
    _olc("masaustu_kurulum_tarifi_var",
         "kurulu görünmüyor" in d["durum"] and d["adimlarGorunur"])
    _olc("masaustu_yatay_tasma_yok", not d["tasma"])
    _kayit(sayfa, "masaustu_ekran")
    masaustu.close()

    tarayici.close()

yanlis = [ad for ad, deger in SONUCLAR if deger is not True]
print("\nSONUC: %d/%d tutarli" % (len(SONUCLAR) - len(yanlis), len(SONUCLAR)))
if yanlis:
    print("TUTARSIZ: " + ", ".join(yanlis))
    sys.exit(1)
