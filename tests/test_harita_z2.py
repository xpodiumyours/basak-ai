"""tests/test_harita_z2.py — Z2: harita yüzeyi (D4b = B onaylı, 2026-10-01).

D4 kararı: yüzey `web/`. D4b = **B** — gömülü harita karosu **YOK**.
`web/` yalnız Z0'ın "Haritada aç" bağlantısını ve Z1'in koordinatını
gösterir; bağlantı kullanıcı tıklamasıyla Google Maps'e gider.

Bedeli ölçülmüştür (docs/HARITA-ZINCIRI-PLANI.md B3): karo yüklemek
ziyaretçinin IP'sini ve baktığı bölgeyi üçüncü tarafa göstermek
demektir; `tests/test_web_gizlilik_beyani.py` üç testle "hiçbir üçüncü
taraf kaynağı yüklemez" sözünü zorlar. B seçildiği için o söz ve
`docs/KVKK-ENVANTER.md` **aynen kalır** — bu dosyada kilitlidir.

Kanıt zinciri (uçtan uca):
  araç sonucu → chat/tools.py `_harita_olayi` → `harita` olayı →
  app.py olay geçişi (+ handoff kümesi) → web/app.js `haritaEkle` →
  web/chat.css kartı.
"""

import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chat import tools as ct
from tools import calistir
from tools.definitions import HARITA_GOSTER, KONUM_COZ

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
JS = (WEB / "app.js").read_text(encoding="utf-8")
CSS = (WEB / "chat.css").read_text(encoding="utf-8")
HTML = (WEB / "index.html").read_text(encoding="utf-8")


def _z0(konum="Kadıköy Moda Sahili"):
    return calistir("harita_goster", {"konum": konum, "mod": "ara"})


def _z1(enlem=40.981169, boylam=29.025471, kaynak="photon"):
    """Z1 sonucunun calistir() biciminde taklidi (ag cagrisi yok)."""
    return {"result": json.dumps({
        "adres": "Kadıköy Moda Sahili",
        "enlem": enlem, "boylam": boylam,
        "gosterim_adi": "Moda Sahili, Kadıköy",
        "kaynak": kaynak, "aday_sayisi": 1, "adaylar": [],
        "denenen_hatlar": [],
    }, ensure_ascii=False)}


# ── Sunucu: olayın içeriği ──────────────────────────────────────────

class TestOlayIcerigi:
    def test_z0_baglanti_gonderir_koordinat_ve_atif_yok(self):
        """Z0 yalniz baglanti uretir; ekranda OSM verisi yoktur → atıf yok."""
        o = ct._harita_olayi("harita_goster", _z0())
        assert o is not None, "Z0 sonucu harita olayina donusmedi"
        assert o["baglanti"].startswith("https://www.google.com/maps/search/")
        assert o["enlem"] is None and o["boylam"] is None
        assert o["atf"] == "", "koordinat yokken OSM atfi yazilmamali"

    def test_z1_koordinat_atf_ve_turetilmis_baglanti(self):
        o = ct._harita_olayi("konum_coz", _z1())
        assert o["enlem"] == 40.981169 and o["boylam"] == 29.025471
        assert o["gosterim_adi"] == "Moda Sahili, Kadıköy"
        # Baglanti ayni testli kurucudan turetilir (JS'te ikinci URL yok).
        assert o["baglanti"].startswith("https://www.google.com/maps/search/")
        assert "40.981169" in o["baglanti"]
        assert o["atf"] == "© OpenStreetMap contributors"

    def test_osm_turevi_olmayan_kaynakta_atif_yazilmaz(self):
        """open-meteo coğrafi kodu OSM verisi DEĞİLDİR → atıf uydurulmaz."""
        o = ct._harita_olayi("konum_coz", _z1(kaynak="open-meteo"))
        assert o["atf"] == ""

    def test_z0_baglanti_aynen_korunur(self):
        ham = _z0("Tuzla, İstanbul")
        o = ct._harita_olayi("harita_goster", ham)
        assert o["baglanti"] == json.loads(ham["result"])["baglanti"]

    def test_hatali_sonuc_olay_uretmez(self):
        assert ct._harita_olayi("konum_coz", {"error": "Adres bulunamadi."}) \
            is None

    def test_bozuk_json_olay_uretmez(self):
        assert ct._harita_olayi("konum_coz", {"result": "{bozuk"}) is None

    def test_baska_arac_olay_uretmez(self):
        assert ct._harita_olayi("list_tasks", {"result": "{}"}) is None

    def test_hicbir_sonuc_alani_yoksa_olay_uretmez(self):
        assert ct._harita_olayi("konum_coz", {"result": "{}"}) is None


# ── Sunucu: olay gerçekten yolda ────────────────────────────────────

class _Toplayici:
    """Hem çağrılabilir (BasakUI.*) hem .olay(...) taşıyan sahte taşıyıcı."""

    def __init__(self):
        self.olaylar = []
        self.kodlar = []

    def __call__(self, kod):
        self.kodlar.append(kod)

    def olay(self, tur, **veri):
        self.olaylar.append(dict(veri, tur=tur))

    def turleri(self):
        return [o["tur"] for o in self.olaylar]


def _call(ad, args="{}", cid="c1"):
    return {"id": cid, "type": "function",
            "function": {"name": ad, "arguments": args}}


def _dongu(calistir_stub, arac, cagri_ad, cagri_args="{}"):
    from chat.tools import arac_dongusu

    class Beyin:
        def cevapla_yayin(self, *a, **k):
            from brain.yayin import SonHata
            raise SonHata("testte stream yok")
            yield

        def cevapla(self, mesajlar, model, tools=None, tool_choice=None,
                    tercih=None):
            if not Beyin.ilk:
                Beyin.ilk = False
                return ({"tool_calls": [_call(cagri_ad, cagri_args, "c2")]},
                        "nvidia")
            return ({"content": "Konum bulundu."}, "nvidia")

    Beyin.ilk = True
    toplayici = _Toplayici()
    arac_dongusu(
        [_call(cagri_ad, cagri_args, "c1")],
        [{"role": "user", "content": "nereye gideyim"}],
        Beyin(), None, toplayici,
        calistir_stub,
        tools=[arac], tool_choice="auto", tercih=["nvidia"],
    )
    return toplayici


class TestOlayYayini:
    def test_z0_gercek_akista_harita_olayi_yolluyor(self):
        t = _dongu(lambda ad, args: _z0(), HARITA_GOSTER, "harita_goster",
                   '{"konum": "Kadıköy Moda Sahili", "mod": "ara"}')
        assert "harita" in t.turleri(), t.turleri()
        o = [x for x in t.olaylar if x["tur"] == "harita"][0]
        assert o["baglanti"].startswith("https://www.google.com/maps/search/")

    def test_z1_gercek_akista_harita_olayi_yolluyor(self):
        t = _dongu(lambda ad, args: _z1(), KONUM_COZ, "konum_coz",
                   '{"adres": "Kadıköy Moda Sahili"}')
        assert "harita" in t.turleri(), t.turleri()
        o = [x for x in t.olaylar if x["tur"] == "harita"][0]
        assert o["enlem"] == 40.981169
        assert o["atf"] == "© OpenStreetMap contributors"

    def test_tool_done_olayi_aynen_kalir(self):
        """Z2 eklemek mevcut olay sozlesmesini bozmaz."""
        t = _dongu(lambda ad, args: _z0(), HARITA_GOSTER, "harita_goster",
                   '{"konum": "Kadıköy Moda Sahili", "mod": "ara"}')
        assert "toolDone" in t.turleri()
        assert "toolStatus" in [c.split("(")[0] for c in t.kodlar] or \
            any("toolStatus" in c for c in t.kodlar)

    def test_basarisiz_arac_harita_olayi_yollamaz(self):
        t = _dongu(lambda ad, args: {"error": "Konum bos olamaz."},
                   HARITA_GOSTER, "harita_goster", '{"konum": "x"}')
        assert "harita" not in t.turleri()


class TestAkisTasima:
    """GERÇEK akış: SSE çerçevesi üzerinden geçer (2026-10-01).

    Daha önce “SSE taşıyıcısı ölçülmedi” diye kayıtlı sınırdı. Burada
    gerçek `app._canli_olaylar` async üreticisi sürülür: olay türü
    filtresi yoktur, her sözlük olduğu gibi JSON'a çevrilip yazılır.
    """

    def test_harita_olayi_sse_cercevesinde_birebir_gecer(self):
        import asyncio

        from app import _canli_olaylar

        async def _kos():
            kuyruk = asyncio.Queue()
            gorev = asyncio.get_running_loop().create_future()
            akis = _canli_olaylar(kuyruk, gorev, 1)
            o = ct._harita_olayi("konum_coz", _z1())
            kuyruk.put_nowait(dict(o, tur="harita", istek=1))
            kuyruk.put_nowait(
                {"tur": "bitir", "istek": 1, "cevap": "Bulundu."})
            gorev.set_result(None)
            return [json.loads(cerceve)
                    async for cerceve in akis]

        cerceveler = asyncio.run(_kos())
        turler = [c.get("tur") for c in cerceveler]
        assert turler == ["harita", "bitir"], turler
        harita = cerceveler[0]
        assert harita["baglanti"].startswith("https://www.google.com/maps/")
        assert harita["enlem"] == 40.981169
        assert harita["atf"] == "© OpenStreetMap contributors"
        # Türkçe karakterler kaçmaz (ensure_ascii=False yolu).
        assert harita["gosterim_adi"] == "Moda Sahili, Kadıköy"


class TestHandoff:
    def test_harita_olayi_handoff_kumesinde(self):
        """Yonlendirme (stateless devam) harita kartini dusurmemeli."""
        from app import _HANDOFF_OLAYLARI
        assert "harita" in _HANDOFF_OLAYLARI
        assert "source" in _HANDOFF_OLAYLARI


# ── Web yüzeyi ─────────────────────────────────────────────────────

class TestWebYuzey:
    def test_olay_isleyicisi_var(self):
        assert 'o.tur === "harita"' in JS
        assert "haritaEkle(b, o)" in JS

    def test_kart_bolumu_balon_kayitinda(self):
        assert "haritaBolumu" in JS
        assert 'haritaBolumu.className = "map-cards"' in JS

    def test_kart_bilesenleri_yalnizca_sunucudan_gelen_veriden(self):
        for parca in ('kart.className = "map-card"',
                      'baslik.className = "map-card-title"',
                      'dugme.className = "map-card-open"',
                      'koordinat.className = "map-card-coords"',
                      'not.className = "map-card-attribution"'):
            assert parca in JS, parca
        # Etiketler sunucudan gelir; JS içinde sabit metin uydurulmaz.
        assert 'textContent = "Haritada aç"' in JS
        assert 'textContent = ad' in JS
        assert "Number(enlem).toFixed(6)" in JS

    def test_dugme_yeni_sekmede_guvenli_acilir(self):
        assert 'dugme.target = "_blank"' in JS
        assert 'dugme.rel = "noopener noreferrer"' in JS

    def test_tekrar_kart_eklenmez_ve_ust_sinir_var(self):
        assert "map-card-list" in JS
        assert "data-anahtar" in JS
        assert "liste.childElementCount >= 3" in JS

    def test_stiller_mevcut_degiskenleri_kullanir(self):
        for parca in (".map-cards{", ".map-card-list{", ".map-card{",
                      ".map-card-title{", ".map-card-open{",
                      ".map-card-coords{", ".map-card-attribution{"):
            assert parca in CSS, parca
        # Yeni palet icat edilmedi; :root sarti kullanilir.
        for degisken in ("var(--line)", "var(--soft)", "var(--muted)",
                         "var(--ink)", "var(--bg)"):
            assert degisken in CSS, degisken

    def test_dokunma_hedefi_kaygitsiz_deve_kadar(self):
        assert ".map-card-open{min-height:40px" in CSS

    def test_surum_kilidi_yukseltildi(self):
        assert "/chat.css?v=12" in HTML
        assert "/app.js?v=20" in HTML


class TestD4bKaroYok:
    """B secimi: gomulu karo YOK. A/C'ye sessizce gecis bu kapidan gecer."""

    YASAK = ("openfreemap", "leaflet", "maplibre", "tile.openstreetmap",
             "basemaps.cartocdn", "maps.googleapis", "tile.")

    def test_web_tarafinda_harici_karo_yok(self):
        for yol in sorted(list(WEB.rglob("*.html")) +
                          list(WEB.rglob("*.js")) +
                          list(WEB.rglob("*.css"))):
            dusuk = yol.read_text(encoding="utf-8").lower()
            for imza in self.YASAK:
                assert imza not in dusuk, (yol.name, imza)

    def test_gomulu_harita_cercevesi_yok(self):
        assert "<canvas" not in JS.lower()
        assert "maplibre" not in CSS.lower()

    def test_baglanti_navigasyon_kodu_yuklemiyor(self):
        """Dugme <a href> — kod yukleyen etiket degil (gizlilik sozunun
        kendi yorumu: gezinme baglantisi kod calistirmaz)."""
        assert "<img" not in JS.lower()
        assert "<iframe" not in JS.lower()
        assert 'fetch("https://' not in JS

    def test_gizlilik_sozu_ve_kvkk_degismedi(self):
        """B secildigi icin soz ve envanter aynen korunur.

        `tests/test_web_gizlilik_beyani.py` bu dosyayi ayrica denetler;
        buradaki kapı yalniz "karoya geçilmedi" işaretini sabitler.
        """
        bilgi = (WEB / "bilgilendirme.html").read_text(encoding="utf-8")
        envanter = (ROOT / "docs" / "KVKK-ENVANTER.md").read_text(
            encoding="utf-8")
        for metin in (bilgi, envanter):
            assert "OpenFreeMap" not in metin
            assert "harita karosu" not in metin.lower()


class TestAracKilidiDegismedi:
    def test_arac_sayisi_ve_alan_ayni_kaldi(self):
        """Z2 yeni arac EKLEMEZ; gosterim yuzeyidir."""
        from tools.capabilities import validate_registry
        s = validate_registry()
        assert s["ok"] is True
        assert s["tool_count"] == 57
        assert s["namespace_count"] == 15
