# -*- coding: utf-8 -*-
"""Arac isareti — "Basak araca bakti mi?" ekranda gorunur mu.

Olculen davranis, dosyada bir kelimenin bulunmasi DEGIL:

1. Sunucu tarafi: her cevapta, `bitir` olayindan ONCE, dogru `tool_count`
   tasiyan bir `runState` olayi yayiliyor mu (arac kosan tur, arac
   kosmayan tur, onbellekten donen tur).
2. Ekran tarafi: web/app.js icindeki GERCEK `aracIsaretiYaz` kodu
   Node'da calistirilir ve olusan sayfa agaci olculur — isaretin metni
   dogru mu, ve isaret cevap METNININ DISINDA ayri bir ogede mi.

AGENTS.md §0 geregi hicbir test kullanici cumlesine bakan kod beklemez;
isaret yalniz sunucunun saydigi arac sayisindan cikar.
"""

import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

KOK = Path(__file__).resolve().parents[1]
APP_JS = KOK / "web" / "app.js"


# ─────────────────────────────────────────────────────────────────
# Sunucu tarafi: runState sinyali gercekten her yolda geliyor mu
# ─────────────────────────────────────────────────────────────────

class _Kopru:
    """app.py'deki _JsKopru'nun test ikizi: hem olay() hem __call__."""

    def __init__(self):
        self.olaylar = []

    def olay(self, tur, **veri):
        kayit = {"tur": str(tur)}
        veri.pop("_handoff", None)
        kayit.update(veri)
        self.olaylar.append(kayit)
        return kayit

    def __call__(self, kod):
        if not isinstance(kod, str) or not kod.startswith("BasakUI."):
            return
        ad, icerik = kod[8:].split("(", 1)
        try:
            parca = json.loads("[%s]" % icerik.rsplit(")", 1)[0])
        except Exception:
            parca = []
        kayit = {"tur": ad}
        if ad == "bitir":
            kayit["cevap"] = parca[0] if parca else ""
        elif ad == "error":
            kayit["metin"] = parca[0] if parca else ""
        self.olaylar.append(kayit)

    def bitirmeden_onceki_run_state(self):
        """`bitir`e kadar gorulen SON runState — ekranin okudugu sinyal."""
        son = None
        for o in self.olaylar:
            if o["tur"] == "runState":
                son = o
            if o["tur"] == "bitir":
                return son
        return None

    def turler(self):
        return [o["tur"] for o in self.olaylar]


class _AracsizBrain:
    """Duz sohbet: hicbir tool_call uretmez."""

    ajan_musait = True

    def bulut_musait(self):
        return True

    def cevapla(self, messages, model=None, **kw):
        return {"content": "duz cevap"}, "groq"


class _AracliBrain:
    """Once gercek bir tool_call, sonra final metin."""

    ajan_musait = True

    def __init__(self):
        self.tur = 0

    def bulut_musait(self):
        return True

    def cevapla(self, messages, model=None, **kw):
        self.tur += 1
        if self.tur == 1:
            return {"content": "", "tool_calls": [{
                "id": "c1",
                "function": {
                    "name": "yetenek_ac",
                    "arguments": json.dumps({"alanlar": ["hesap"]}),
                },
            }]}, "groq"
        if self.tur == 2:
            return {"content": "", "tool_calls": [{
                "id": "c2",
                "function": {
                    "name": "hesapla",
                    "arguments": json.dumps({"ifade": "2+2"}),
                },
            }]}, "groq"
        return {"content": "araca bakarak cevap"}, "groq"


@pytest.fixture
def izole(monkeypatch, tmp_path):
    from chat import context as cc
    from chat import onbellek
    monkeypatch.setattr(cc, "HISTORY_FILE", str(tmp_path / "g.json"))
    monkeypatch.setattr(cc, "SETTINGS_FILE", str(tmp_path / "a.json"))
    monkeypatch.setattr(cc, "_hafiza", False)
    onbellek.temizle()
    yield tmp_path
    onbellek.temizle()


def _kos(brain, metin="merhaba", **kw):
    """app.py'nin yaptigi cagrinin aynisi: gercek arac katalogu ile."""
    import chat as c
    from tools import TOOLS
    kopru = _Kopru()
    kw.setdefault("tools", TOOLS)
    c.mesaj_isle(metin, brain, "SYS", kopru, **kw)
    return kopru


def test_arac_kosmayan_cevapta_sinyal_sifir(izole):
    """Arac kosmadan verilen cevap: tool_count 0 ve bitir'den once gelir."""
    kopru = _kos(_AracsizBrain())
    assert "bitir" in kopru.turler()
    durum = kopru.bitirmeden_onceki_run_state()
    assert durum is not None, "bitir'den once hic runState yayilmadi"
    assert durum["tool_count"] == 0


def test_arac_kosan_cevapta_sinyal_arac_sayisini_tasir(izole, monkeypatch):
    """Gercek arac kosan turda tool_count, kosan arac sayisini soyler."""
    import tools as t
    monkeypatch.setattr(t, "calistir", lambda ad, args: "4")

    kopru = _kos(_AracliBrain(), metin="iki arti iki kac eder")
    assert "bitir" in kopru.turler()
    durum = kopru.bitirmeden_onceki_run_state()
    assert durum is not None, "bitir'den once hic runState yayilmadi"
    # yetenek_ac bir yetenek acimidir, arac degil: sayiya girmez.
    assert durum["tool_count"] == 1


def test_onbellekten_donen_cevapta_da_sinyal_var(izole):
    """Onbellekten donen cevap araca bakmamistir: tool_count 0, sinyal var."""
    from chat import onbellek

    brain = _AracsizBrain()
    ilk = _kos(brain, metin="ayni soru", tool_policy="none")
    assert "bitir" in ilk.turler()

    ikinci = _kos(brain, metin="ayni soru", tool_policy="none")
    assert "bitir" in ikinci.turler()
    durum = ikinci.bitirmeden_onceki_run_state()
    assert durum is not None, "onbellek yolunda runState yayilmadi"
    assert durum["tool_count"] == 0
    assert onbellek.al("ayni soru", []) is not None


class _AkanAracsizBrain(_AracsizBrain):
    """Cevap KELIME KELIME akar (gercek stream yolu), arac kosmaz."""

    def cevapla_yayin(self, mesajlar, model=None, tercih=None, tools=None):
        for parca in ("duz ", "akan ", "cevap"):
            yield "groq", parca

    def cevapla(self, *a, **kw):
        raise AssertionError("akan yolda tek-seferlik cagri olmamali")


class _AkanAracliBrain(_AracsizBrain):
    """Gercek akis yolu: alan ac -> araci cagir -> final metni akit."""

    def __init__(self):
        self.tur = 0

    def _istek(self, ad, args, cagri_id):
        from brain.yayin import AracIstegi
        raise AracIstegi(
            tool_calls=[{
                "id": cagri_id,
                "function": {"name": ad, "arguments": json.dumps(args)},
            }],
            kaynak="groq",
        )

    def cevapla_yayin(self, mesajlar, model=None, tercih=None, tools=None):
        self.tur += 1
        if self.tur == 1:
            self._istek("yetenek_ac", {"alanlar": ["hesap"]}, "c1")
        if self.tur == 2:
            self._istek("hesapla", {"ifade": "2+2"}, "c2")
        for parca in ("araca ", "bakarak ", "cevap"):
            yield "groq", parca

    def cevapla(self, *a, **kw):
        raise AssertionError("akan yolda tek-seferlik cagri olmamali")


def test_akan_cevapta_da_isaret_sinyali_gelir(izole):
    """Akan (parca parca) duz cevapta da bitir'den once sinyal var."""
    kopru = _kos(_AkanAracsizBrain())
    turler = kopru.turler()
    assert "parca" in turler, "bu test akan yolu olcmeli"
    assert "bitir" in turler
    durum = kopru.bitirmeden_onceki_run_state()
    assert durum is not None
    assert durum["tool_count"] == 0


def test_akan_cevapta_arac_kosarsa_sayi_gelir(izole, monkeypatch):
    """Akis icinde arac cagrilirsa sinyal arac sayisini tasir."""
    import tools as t
    monkeypatch.setattr(t, "calistir", lambda ad, args: "4")

    kopru = _kos(_AkanAracliBrain(), metin="iki arti iki")
    turler = kopru.turler()
    assert "parca" in turler, "bu test akan yolu olcmeli"
    assert "bitir" in turler
    durum = kopru.bitirmeden_onceki_run_state()
    assert durum is not None
    assert durum["tool_count"] >= 1


def test_run_state_her_zaman_bitirden_once_gelir(izole):
    """Ekran isareti bitir aninda yazar; sinyal daha once gelmis olmali."""
    kopru = _kos(_AracsizBrain())
    turler = kopru.turler()
    assert turler.index("runState") < turler.index("bitir")


# ─────────────────────────────────────────────────────────────────
# Ekran tarafi: GERCEK aracIsaretiYaz kodu Node'da calistirilir
# ─────────────────────────────────────────────────────────────────

def _isaret_kodu():
    """web/app.js icindeki gercek aracIsaretiYaz govdesini al."""
    kaynak = APP_JS.read_text(encoding="utf-8")
    bas = kaynak.index("function aracIsaretiYaz(")
    son = kaynak.index("\n}\n", bas) + 3
    return kaynak[bas:son]


_DOM_SHIM = """
// Kucuk sayfa agaci taklidi: appendChild var olan dugumu TASIR.
class Dugum {
  constructor(ad) { this.ad = ad; this.className = ""; this._metin = "";
                    this.cocuklar = []; this.ust = null; }
  get textContent() {
    if (this.cocuklar.length === 0) return this._metin;
    return this.cocuklar.map((c) => c.textContent).join("");
  }
  set textContent(v) { this._metin = String(v); this.cocuklar = []; }
  appendChild(c) {
    if (c.ust) c.ust.cocuklar = c.ust.cocuklar.filter((x) => x !== c);
    c.ust = this; this.cocuklar.push(c); return c;
  }
  querySelector(sec) {
    const sinif = sec.replace(".", "");
    for (const c of this.cocuklar) {
      if (c.className === sinif) return c;
      const alt = c.querySelector(sec);
      if (alt) return alt;
    }
    return null;
  }
}
const document = { createElement: (ad) => new Dugum(ad) };
"""


def _node():
    yol = shutil.which("node")
    if not yol:
        pytest.skip("node kurulu degil")
    return yol


def _ekranda_ciz(tool_count):
    """Gercek aracIsaretiYaz'i calistirip olusan agaci geri getir."""
    betik = _DOM_SHIM + _isaret_kodu() + """
const balon = new Dugum("div");
const icerik = new Dugum("div");
icerik.className = "icerik";
icerik.textContent = "Basak'in cevap metni.";
balon.appendChild(icerik);

aracIsaretiYaz(balon, { toolCount: TOOL_COUNT });

const isaret = balon.querySelector(".arac-isareti");
console.log(JSON.stringify({
  isaretMetni: isaret ? isaret.textContent : null,
  cevapMetni: icerik.textContent,
  // isaret cevap metninin ICINDE mi, yoksa DISINDA ayri bir oge mi?
  isaretinUstu: isaret ? (isaret.ust === balon ? "balon" : "icerik") : null,
  balonunSonCocugu: balon.cocuklar[balon.cocuklar.length - 1].className,
}));
""".replace("TOOL_COUNT", str(tool_count))
    ciktil = subprocess.run(
        [_node(), "-e", betik], capture_output=True, text=True,
        encoding="utf-8", timeout=60,
    )
    assert ciktil.returncode == 0, ciktil.stderr
    return json.loads(ciktil.stdout.strip())


def test_arac_kosan_cevapta_isaret_gorunur():
    """2 arac kostuysa ekranda Casper'in onayladigi satir cikar."""
    sonuc = _ekranda_ciz(2)
    assert sonuc["isaretMetni"] == "● 2 araç kullanıldı"


def test_arac_kosmayan_cevapta_bakilmadan_yazar():
    """Hic arac kosmadiysa 'bakilmadan cevaplandi' yazar."""
    sonuc = _ekranda_ciz(0)
    assert sonuc["isaretMetni"] == "○ bakılmadan cevaplandı"


def test_isaret_cevap_metninin_disinda_durur():
    """AGENTS.md §0: cevabin METNINE hicbir sey yapistirilmaz."""
    for sayi in (0, 2):
        sonuc = _ekranda_ciz(sayi)
        assert sonuc["cevapMetni"] == "Basak'in cevap metni.", (
            "isaret cevap metnine karismis"
        )
        assert sonuc["isaretinUstu"] == "balon", (
            "isaret cevap metninin icine konmus"
        )
        assert sonuc["balonunSonCocugu"] == "arac-isareti", (
            "isaret cevabin altinda degil"
        )


def test_isaret_kaynak_sayisi_gostermez():
    """evidence_count okunmamis baglantilari da sayiyor; gosterilmez."""
    for sayi in (0, 1, 2, 5):
        metin = _ekranda_ciz(sayi)["isaretMetni"]
        assert "kaynak" not in metin.lower()


# ─────────────────────────────────────────────────────────────────
# Baglanti (glue): GERCEK olayiIsle, runState'i alip bitir'de yaziyor mu
# Node'da kosar; tarayici kurulu olmasa da bu kapi olculur.
# ─────────────────────────────────────────────────────────────────

def _kod_dilimi(bas_imza):
    kaynak = APP_JS.read_text(encoding="utf-8")
    bas = kaynak.index(bas_imza)
    return kaynak[bas:kaynak.index("\n}\n", bas) + 3]


def _glue_sonucu(tool_count):
    """runState + bitir olaylarini GERCEK olayiIsle'ye verip sonucu olc."""
    betik = _DOM_SHIM + """
// olayiIsle'nin bu iki dalinin disinda kalan yardimcilar taklit edilir;
// olculen sey runState -> bitir baglantisinin kendisi.
const balonlar = new Map();
const runDurumlari = new Map();
const cagrildi = [];
function bubble() { const b = new Dugum("div"); b.className = "bubble";
                    const i = new Dugum("div"); i.className = "icerik";
                    b.appendChild(i); return b; }
function calismaKaydi() { return {yonlendir:{}, canli:{}}; }
function durumSatiri() {}
function planiGuncelle() {}
function kaynakEkle() {}
function araciTamamla() {}
function calismaMolaVer() {}
function calismaYanitaGecti() { cagrildi.push("yanitaGecti"); }
function akiciMetinEkle() {}
function akiciMetniDurdur() {}
function durumuKapat() {}
function sohbetAlta() {}
function calismaBitir() { cagrildi.push("calismaBitir"); }
function akiciMetniFinaleTamamla(b, metin) {
  b.querySelector(".icerik").textContent = metin;
  return Promise.resolve();
}
""" + _isaret_kodu() + _kod_dilimi("function olayiIsle(") + """
(async () => {
  const balon = bubble();
  balonlar.set("r1", balon);
  olayiIsle({istek:"r1", tur:"runState", tool_count:TOOL_COUNT,
             evidence_count:7, status:"completed"});
  await olayiIsle({istek:"r1", tur:"bitir", cevap:"Basak cevabi"});
  const isaret = balon.querySelector(".arac-isareti");
  const icerik = balon.querySelector(".icerik");
  console.log(JSON.stringify({
    isaretMetni: isaret ? isaret.textContent : null,
    cevapMetni: icerik.textContent,
    isaretinUstu: isaret ? (isaret.ust === balon ? "balon" : "icerik") : null,
    sira: cagrildi,
  }));
})();
""".replace("TOOL_COUNT", str(tool_count))
    ciktil = subprocess.run(
        [_node(), "-e", betik], capture_output=True, text=True,
        encoding="utf-8", timeout=60,
    )
    assert ciktil.returncode == 0, ciktil.stderr
    return json.loads(ciktil.stdout.strip())


def test_glue_arac_kosan_cevapta_isareti_yazar():
    """runState(tool_count=2) + bitir -> ekranda "2 arac kullanildi"."""
    sonuc = _glue_sonucu(2)
    assert sonuc["isaretMetni"] == "● 2 araç kullanıldı"
    assert sonuc["cevapMetni"] == "Basak cevabi"
    assert sonuc["isaretinUstu"] == "balon"
    assert "calismaBitir" in sonuc["sira"]


def test_glue_arac_kosmayan_cevapta_bakilmadan_yazar():
    """runState(tool_count=0) + bitir -> "bakilmadan cevaplandi"."""
    sonuc = _glue_sonucu(0)
    assert sonuc["isaretMetni"] == "○ bakılmadan cevaplandı"
    assert sonuc["cevapMetni"] == "Basak cevabi"
    assert sonuc["isaretinUstu"] == "balon"


def test_glue_kaynak_sayisi_asla_yazilmaz():
    """evidence_count 7 gonderilse bile ekranda kaynak sayisi cikmaz."""
    for sayi in (0, 2):
        assert "kaynak" not in _glue_sonucu(sayi)["isaretMetni"].lower()


# ─────────────────────────────────────────────────────────────────
# Olcum: evidence_count NEYI sayiyor (kaynak sayisinin gizlenme sebebi)
# ─────────────────────────────────────────────────────────────────

def test_evidence_okunmamis_baglantilari_da_sayar():
    """Tek sayfa okumasi, sayfadaki baglantilari da 'kaynak' sayiyor.

    Bu testin isi durumu SABITLEMEK: `_kaynaklari_cikar` duzelene kadar
    ekranda kaynak sayisi gosterilemez. Duzelirse bu test kirilir ve
    karar yeniden verilir.
    """
    from chat import tools as ct

    govde = ("Ana metin. Bak: https://a.example.com/1 "
             "ve https://b.example.com/2")
    bulunan = ct._kaynaklari_cikar(
        "sayfa_oku", {"url": "https://okunan.example.com/asil"}, govde)

    assert len(bulunan) > 1, (
        "tek sayfa okumasi tek kaynak uretiyorsa karar yeniden verilebilir"
    )
    assert any("okunan.example.com" not in u for u in bulunan), (
        "okunmamis baglanti kaynak sayilmiyorsa karar yeniden verilebilir"
    )


def test_web_ara_sonuclari_kaynak_sayilmaz():
    """Arama sonuclari kaynak sayilmiyor — olculdu, boyle kalmali."""
    from chat import tools as ct

    assert ct._kaynaklari_cikar(
        "web_search", {"query": "x"}, "https://aday.example.com/1") == []


def test_yetenek_ac_arac_sayisina_girmez():
    """Yetenek acmak arac kullanmak degildir; sayiyi sisirmemeli."""
    from chat.agent_runtime import AgentRunState

    s = AgentRunState(run_id="r1")
    s.capability_opened(["hesap"], "c1")
    assert s.public_snapshot()["tool_count"] == 0
    s.tool_done("hesapla", "c2", True)
    assert s.public_snapshot()["tool_count"] == 1


# ─────────────────────────────────────────────────────────────────
# Uctan uca: GERCEK tarayicida, GERCEK olayiIsle akisiyla
# (playwright + chromium yoksa ATLANIR — atlama nedeni ciktida gorunur)
# ─────────────────────────────────────────────────────────────────

def _tarayici_testi(tool_count):
    """Gercek app.js'i Chromium'da acip runState + bitir olaylarini besler."""
    playwright_api = pytest.importorskip(
        "playwright.sync_api", reason="playwright kurulu degil")

    import functools
    import glob
    import threading
    from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

    class _Sessiz(SimpleHTTPRequestHandler):
        def log_message(self, *a):
            pass

    sunucu = ThreadingHTTPServer(
        ("127.0.0.1", 0),
        functools.partial(_Sessiz, directory=str(KOK / "web")))
    threading.Thread(target=sunucu.serve_forever, daemon=True).start()
    adres = "http://127.0.0.1:%d" % sunucu.server_address[1]

    try:
        with playwright_api.sync_playwright() as p:
            yol = sorted(glob.glob(
                "/opt/pw-browsers/chromium-*/chrome-linux/chrome"))
            try:
                tarayici = p.chromium.launch(
                    **({"executable_path": yol[-1]} if yol else {}))
            except Exception as e:
                pytest.skip("chromium acilamadi: %s" % e)
            pg = tarayici.new_page()
            pg.route("**/api/**", lambda r: r.fulfill(
                status=200, body=json.dumps({"ok": True, "sohbetler": []}),
                content_type="application/json"))
            pg.goto(adres + "/index.html")
            pg.wait_for_function("typeof olayiIsle === 'function'")

            pg.evaluate(
                """async (n) => {
                    const b = bubble('assistant', '');
                    balonlar.set('r1', b);
                    // Sunucunun gercekte yaydigi sira: once runState,
                    // sonra bitir.
                    olayiIsle({istek:'r1', tur:'runState', tool_count:n,
                               evidence_count:7, status:'completed'});
                    await olayiIsle({istek:'r1', tur:'bitir',
                                     cevap:'Basak cevabi'});
                }""", tool_count)
            pg.wait_for_selector(".arac-isareti")

            sonuc = pg.evaluate("""() => {
                const el = document.querySelector('.arac-isareti');
                const balon = el.closest('.bubble');
                const icerik = balon.querySelector('.icerik');
                return {
                  metin: el.textContent,
                  gorunur: el.getClientRects().length > 0,
                  cevapMetni: icerik ? icerik.textContent : '',
                  metninIcinde: !!(icerik && icerik.contains(el)),
                };
            }""")
            pg.close()
            tarayici.close()
            return sonuc
    finally:
        sunucu.shutdown()


def test_tarayicida_arac_kosan_cevapta_isaret_gorunur():
    sonuc = _tarayici_testi(2)
    assert sonuc["gorunur"], "isaret ekranda yer kaplamiyor"
    assert sonuc["metin"].strip() == "● 2 araç kullanıldı"
    # evidence_count 7 gonderildi ama kaynak sayisi GOSTERILMEZ.
    assert "kaynak" not in sonuc["metin"].lower()
    # Cevabin METNI degismedi, isaret metnin disinda.
    assert sonuc["cevapMetni"].strip() == "Basak cevabi"
    assert sonuc["metninIcinde"] is False


def test_tarayicida_arac_kosmayan_cevapta_bakilmadan_yazar():
    sonuc = _tarayici_testi(0)
    assert sonuc["gorunur"]
    assert sonuc["metin"].strip() == (
        "○ bakılmadan cevaplandı")
    assert sonuc["cevapMetni"].strip() == "Basak cevabi"
    assert sonuc["metninIcinde"] is False
