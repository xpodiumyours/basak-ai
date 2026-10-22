# -*- coding: utf-8 -*-
"""_devam_kanit.py — Yol B-1 gercek davranis kaniti (2026-10-22).

Beklenmedik akis kesilmesinde web surumu calisma satirini siliyor ve is
kayboluyordu. Bu gercek tarayici provasi GERCEK web/index.html + app.js +
common.js'i surer (sunucu kurulmaz; Playwright route intercept ile /api
cagrilari sahte sunucudan cevaplanir) ve uc senaryoyu olcer:

  A — kopma + imzali devam kaydi: satir SILINMEZ, "Devam et" sunulur;
      tiklayinca yeni istekte `yonlendirme_baglami` gercek tokenle gider;
      ayni ekranda Yol A-1 sayaclari gercek olaylarla dolar.
  B — kopma + kayit yok: bugunun davranisi aynen kalir (satir silinir,
      acik hata balonu; "Devam et" YOK).
  C — bozuk ekran: konsol hatasi yok, yatay tasma yok.

Olculen her iddia konsola sayi olarak yazilir; ekran goruntuleri
`_devam_kanit/` klasorune dusar. Calistirma:
`python scripts/olcum/_devam_kanit.py`
"""

import json
import pathlib
import sys
from urllib.parse import unquote, urlparse

from playwright.sync_api import sync_playwright

KOK = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

WEB = KOK / "web"
CIKTI = KOK / "_devam_kanit"
CIKTI.mkdir(exist_ok=True)

TOKEN = "kanit-govde.kanit-imza"

KONSOL = []
BASARISIZ = []
ISTEK_GOVDELERI = []
DURUM = {"senaryo": "A", "akis": 0}

# Senaryo A akisi: gercek olay bicimleri (chat/tools.py + app.py), SONUNDA
# bitir YOK — istemci bunu "baglanti koptu" olarak gormeli.
AKIS_A = (
    '{"tur":"toolStatus","istek":"r1","metin":"Görevler listeleniyor"}\n'
    '{"tur":"toolDone","istek":"r1","id":"c1","arac":"list_tasks",'
    '"baslik":"Görevler listeleniyor","detay":"","ok":true,'
    '"handoff_token":"%s"}\n'
    '{"tur":"source","istek":"r1","url":"https://example.com/ara",'
    '"baslik":"Örnek sayfa"}\n' % TOKEN
)

# Senaryo B: ayni kopma ama imzali kayit HIC gelmedi.
AKIS_B = (
    '{"tur":"toolStatus","istek":"r1","metin":"Görevler listeleniyor"}\n'
)

BITIR = '{"tur":"bitir","istek":"r2","cevap":"Devam tamamlandı.","kaynak":""}\n'


def _rota(route):
    istek = route.request
    parca = urlparse(istek.url)
    yol = unquote(parca.path)

    if yol == "/api/sohbet":
        govde = istek.post_data or ""
        ISTEK_GOVDELERI.append(govde)
        DURUM["akis"] += 1
        if DURUM["akis"] == 1:
            akis = AKIS_A if DURUM["senaryo"] == "A" else AKIS_B
        else:
            akis = BITIR
        route.fulfill(
            status=200,
            content_type="application/x-ndjson; charset=utf-8",
            body=akis)
        return

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
        # Tarayici her sayfada ister; uygulama hatasi degildir.
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


def _sayaclar(sayfa):
    return sayfa.evaluate("""() => {
      const k = document.querySelector('.work-card');
      return {
        kart: !!k,
        baslik: k?.querySelector('.work-title')?.textContent || '',
        ozet: k?.querySelector('.work-summary')?.textContent || '',
        ozetGorunur: k ? !k.querySelector('.work-summary')?.hidden : false,
        sayac: k?.querySelector('.work-counts')?.textContent || '',
        devam: !!document.querySelector('.work-continue'),
        devamMetni: document.querySelector('.work-continue')?.textContent || '',
        hataBalonu: [...document.querySelectorAll('.icerik')]
          .map(e => e.textContent || '')
          .some(t => t.includes('Bir sorun oluştu')),
        govdeYukseklik: document.body.scrollHeight,
        tasma: document.documentElement.scrollWidth >
               document.documentElement.clientWidth,
      };
    }""")


SONUCLAR = []


def _olc(ad, deger):
    SONUCLAR.append((ad, deger))
    print("OLCUM %s = %s" % (ad, json.dumps(deger, ensure_ascii=False)))


with sync_playwright() as p:
    tarayici = p.chromium.launch(args=["--no-sandbox"])
    sayfa = tarayici.new_page(viewport={"width": 1100, "height": 900})
    sayfa.on("console", lambda m: KONSOL.append(
        (m.type, m.text, (m.location or {}).get("url", ""))))
    sayfa.on("requestfailed",
             lambda r: BASARISIZ.append(r.url)
             if r.url.startswith("http") else None)
    sayfa.route("**/*", _rota)

    # ── Senaryo A: kopma + imzali kayit ──
    DURUM.update(senaryo="A", akis=0)
    sayfa.goto("http://basak.local/", wait_until="networkidle")
    sayfa.fill("#message", "görevlerimi listele")
    sayfa.click("#send")
    sayfa.wait_for_selector(".work-continue", timeout=8000)
    sayfa.wait_for_timeout(300)

    a = _sayaclar(sayfa)
    _olc("A_kart_ayakta", a["kart"])
    _olc("A_baslik_baglanti_koptu", "Bağlantı koptu" in a["baslik"])
    _olc("A_devam_dugmesi", a["devam"] and a["devamMetni"] == "Devam et")
    _olc("A_ozet_durust", a["ozetGorunur"] and
         "Bağlantı beklenmedik kapandı" in a["ozet"])
    _olc("A_sayaclar", a["sayac"])
    sayfa.screenshot(path=str(CIKTI / "a_kopma_devam.png"), full_page=True)

    sayfa.click(".work-continue")
    sayfa.wait_for_timeout(1200)

    devam_istegi = None
    for govde in ISTEK_GOVDELERI:
        try:
            v = json.loads(govde)
        except ValueError:
            continue
        if isinstance(v, dict) and v.get("yonlendirme_baglami"):
            devam_istegi = v
    _olc("A_devam_istegi_var", devam_istegi is not None)
    if devam_istegi:
        bag = devam_istegi["yonlendirme_baglami"]
        _olc("A_devam_semasi", bag.get("schema"))
        _olc("A_devam_token_eslesme", bag.get("token") == TOKEN)

    sayfa.wait_for_timeout(600)
    cevaplar = sayfa.evaluate(
        "() => [...document.querySelectorAll('.message-row.assistant"
        " .icerik')].map(e => e.textContent || '')")
    _olc("A_devam_cevabi",
         any("Devam tamamlandı." in (c or "") for c in cevaplar))
    sayfa.screenshot(path=str(CIKTI / "a_devam_sonrasi.png"), full_page=True)

    # ── Senaryo B: kopma + kayit yok → eski davranis ──
    DURUM.update(senaryo="B", akis=0)
    ISTEK_GOVDELERI.clear()
    sayfa.goto("http://basak.local/", wait_until="networkidle")
    sayfa.fill("#message", "görevlerimi listele")
    sayfa.click("#send")
    sayfa.wait_for_timeout(1500)

    b = _sayaclar(sayfa)
    _olc("B_devam_dugmesi_yok", not b["devam"])
    _olc("B_kart_silindi", not b["kart"])
    _olc("B_acik_hata", b["hataBalonu"])
    sayfa.screenshot(path=str(CIKTI / "b_kopma_hata.png"), full_page=True)

    # ── Senaryo C: bozuk ekran kontrolu ──
    # Yalniz uygulama kaynakli konsol hatalari sayilir; tarayicinin kendi
    # uzanti/istem kaynaklari ortam gurultusudur.
    _olc("C_konsol_hatasi",
         [(t, m) for t, m, u in KONSOL
          if t == "error" and u.startswith("http")])
    _olc("C_basarisiz_istek", BASARISIZ)
    _olc("A_tasma", a["tasma"])
    _olc("B_tasma", b["tasma"])

    # Mobil olcum (A senaryosunun kartiyla)
    DURUM.update(senaryo="A", akis=0)
    sayfa.goto("http://basak.local/", wait_until="networkidle")
    sayfa.fill("#message", "görevlerimi listele")
    sayfa.click("#send")
    sayfa.wait_for_selector(".work-continue", timeout=8000)
    sayfa.set_viewport_size({"width": 390, "height": 780})
    sayfa.wait_for_timeout(300)
    m = _sayaclar(sayfa)
    _olc("M_tasma", m["tasma"])
    # Bozuk ekran kilidi: süre/sayaç sayıları ve düğme metinleri mobilde
    # kelime/sayı ortasından KIRILMAZ (tek satır yükseklik ≤ 44 px).
    kirilma = sayfa.evaluate("""() => {
      const zaman = document.querySelector('.work-time');
      const sayac = document.querySelector('.work-counts');
      const dugmeler = [...document.querySelectorAll('.work-action')];
      return {
        zaman: Math.round(zaman.getBoundingClientRect().height),
        sayac: Math.round(sayac.getBoundingClientRect().height),
        dugmeler: dugmeler.map(d =>
          Math.round(d.getBoundingClientRect().height)),
      };
    }""")
    _olc("M_sure_tek_satir", kirilma["zaman"] <= 44)
    _olc("M_sayac_tek_satir", kirilma["sayac"] <= 44)
    _olc("M_dugmeler_tek_satir",
         all(h <= 44 for h in kirilma["dugmeler"]) and
         len(kirilma["dugmeler"]) > 0)
    sayfa.screenshot(path=str(CIKTI / "m_kopma_devam.png"), full_page=True)

    tarayici.close()

print("GORSELLER:", sorted(x.name for x in CIKTI.glob("*.png")))
beklenen = {
    "A_kart_ayakta": True,
    "A_baslik_baglanti_koptu": True,
    "A_devam_dugmesi": True,
    "A_ozet_durust": True,
    "A_sayaclar": "1 komut çalıştırıldı · 1 sayfa gezildi",
    "A_devam_istegi_var": True,
    "A_devam_semasi": "p2-handoff-v1",
    "A_devam_token_eslesme": True,
    "A_devam_cevabi": True,
    "B_devam_dugmesi_yok": True,
    "B_kart_silindi": True,
    "B_acik_hata": True,
    "C_konsol_hatasi": [],
    "C_basarisiz_istek": [],
    "A_tasma": False,
    "B_tasma": False,
    "M_tasma": False,
    "M_sure_tek_satir": True,
    "M_sayac_tek_satir": True,
    "M_dugmeler_tek_satir": True,
}
hatalar = [(k, v, beklenen.get(k)) for k, v in SONUCLAR
           if beklenen.get(k, v) != v]
print("SONUC:", "HEPSI TUTARLI" if not hatalar else "TUTARSIZ %s" % hatalar)
sys.exit(1 if hatalar else 0)
