"""tests/test_harita_dedektif.py — Z4: harita zinciri (tek çağrıda dedektif).

Z0/Z1/Z3 parçaları ayrı ayrı çalışıyordu; Z4 bunları TEK çağrıda
bağlar: merkez çözülür (konum_coz) → markanın kayıtlı şubeleri aranır
(Overpass/Photon) → her şube için harita bağlantısı üretilir
(harita_goster; yol modunda merkezden şubeye).

Kabul ölçüsü: docs/HARITA-ZINCIRI-PLANI.md, FAZ 5.
- Zincir adımları çıktıda görünür (zincir alanı)
- YOL modunda bağlantı merkezden şubeye gider (origin)
- Adet/yariçap/mod ile yönlendirme çalışır
- Hata yollarında şube/bağlantı UYDURULMAZ
- Dördün dördü de dolu: şema + dispatcher dalı + yetenek alanı + durum
- Web yüzeyinde şube listesi gösterilir

Tüm testler çevrimdışı: ağ çağrısı yapılmaz, sahte Overpass yanıtı
enjekte edilir.
"""

import json
import os
import sys
import urllib.parse
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools import calistir
from tools.harita import (ARAMA_TABANI, YOL_TABANI, harita_dedektif)

ROOT = Path(__file__).resolve().parents[1]
JS = (ROOT / "web" / "app.js").read_text(encoding="utf-8")
CSS = (ROOT / "web" / "chat.css").read_text(encoding="utf-8")
HTML = (ROOT / "web" / "index.html").read_text(encoding="utf-8")

MERKEZ_ENLEM, MERKEZ_BOYLAM = 41.0111, 29.0254

OVERPASS_GOVDE = {
    "elements": [
        {"type": "node", "id": 1, "lat": 41.0150, "lon": 29.0290,
         "tags": {"name": "BİM - Moda", "brand": "BİM", "shop": "supermarket",
                  "addr:street": "Moda Caddesi", "addr:housenumber": "12",
                  "addr:city": "Istanbul", "phone": "+90 212 000 00 00"}},
        {"type": "way", "id": 2, "center": {"lat": 41.0200, "lon": 29.0350},
         "tags": {"name": "BİM Caferağa", "brand": "BİM",
                  "shop": "supermarket", "website": "https://bim.com.tr"}},
    ],
}

BOS_GOVDE = {"elements": []}


class SahteHat:
    """urllib yerine gecen sahte hat; adresleri kaydeder."""

    def __init__(self, govde=OVERPASS_GOVDE, hata=None):
        self.govde = govde
        self.hata = hata
        self.adresler = []

    def __call__(self, url, sure=None):
        self.adresler.append(url)
        if self.hata is not None:
            return None, self.hata
        if self.govde is None:
            return None, "servise ulasilamadi"
        return self.govde, None


@pytest.fixture
def sahte(monkeypatch):
    hat = SahteHat()
    monkeypatch.setattr("tools.harita._json_al", hat)
    return hat


def _bul(marka="BİM", konum="41.0111, 29.0254", **ek):
    """Basari yolundan 'result' JSON'unu cozer; hata varsa None doner."""
    r = harita_dedektif(marka, konum, **ek)
    if "error" in r:
        return None
    return json.loads(r["result"])


# ── Zincir ──────────────────────────────────────────────────────────

class TestZincir:
    def test_zincir_adimlari_sozlesmede(self, sahte):
        veri = _bul()
        assert veri["zincir"] == ["konum_coz", "sube_bul", "harita_goster"]

    def test_koordinat_merkezi_ag_cagrisi_yapmaz(self, sahte):
        veri = _bul()
        assert veri["merkez"]["enlem"] == MERKEZ_ENLEM
        assert veri["merkez"]["boylam"] == MERKEZ_BOYLAM
        assert veri["merkez"]["kaynak"] == "koordinat"
        # Cozgecirdirme (q=) istegi atilmadi; yalniz Overpass soruldu.
        assert not [u for u in sahte.adresler if "q=" in u]

    def test_adres_merkezi_konum_coz_ile_cozulur(self, sahte, monkeypatch):
        kayit = {}

        def sahte_konum_coz(adres):
            kayit["adres"] = adres
            return {"result": json.dumps({
                "adres": adres, "enlem": 40.99, "boylam": 29.02,
                "gosterim_adi": "Kadikoy, Istanbul", "kaynak": "photon",
                "aday_sayisi": 1, "adaylar": [],
                "denenen_hatlar": []}, ensure_ascii=False)}

        monkeypatch.setattr("tools.harita.konum_coz", sahte_konum_coz)
        veri = _bul(konum="Kadikoy, Istanbul")
        assert kayit["adres"] == "Kadikoy, Istanbul"
        assert veri["merkez"]["enlem"] == 40.99
        assert veri["merkez"]["kaynak"] == "photon"

    def test_sube_listesi_zincirin_ciktisidir(self, sahte):
        veri = _bul()
        assert veri["sube_sayisi"] == 2
        ad = [s["ad"] for s in veri["subeler"]]
        assert ad == ["BİM - Moda", "BİM Caferağa"]

    def test_en_yakin_ilk_siralanir(self, sahte):
        veri = _bul()
        mesafeler = [s["mesafe_km"] for s in veri["subeler"]]
        assert mesafeler == sorted(mesafeler)

    def test_sube_bilgileri_korunur(self, sahte):
        veri = _bul()
        ilk = veri["subeler"][0]
        assert ilk["adres"] == "Moda Caddesi, 12, Istanbul"
        assert ilk["telefon"] == "+90 212 000 00 00"
        assert ilk["tip"] == "supermarket"
        assert ilk["website"] == "" or ilk["website"].startswith("http")

    def test_osm_atfi_tasir(self, sahte):
        veri = _bul()
        assert "OpenStreetMap" in veri["atif"]
        assert veri["veri_kaynagi"] == "overpass"


# ── Baglantilar (zincirin sonucu) ───────────────────────────────────

class TestBaglantilar:
    def test_yol_modunda_baglanti_merkezden_subeye_gider(self, sahte):
        veri = _bul()
        baglanti = veri["subeler"][0]["baglanti"]
        assert baglanti.startswith(YOL_TABANI)
        assert "origin=" in baglanti
        assert "41.011100" in urllib.parse.unquote(baglanti)

    def test_ara_baglantisi_arama_modundadir(self, sahte):
        veri = _bul()
        ara = veri["subeler"][0]["ara_baglanti"]
        assert ara.startswith(ARAMA_TABANI)
        assert "origin=" not in ara

    def test_merkez_baglantisi_uretilir(self, sahte):
        veri = _bul()
        merkez = veri["baglantilar"]["merkez"]
        assert merkez.startswith(ARAMA_TABANI)
        assert "41.011100" in urllib.parse.unquote(merkez)

    def test_ara_modunda_origin_yazilmaz(self, sahte):
        veri = _bul(mod="ara")
        baglanti = veri["subeler"][0]["baglanti"]
        assert baglanti.startswith(ARAMA_TABANI)
        assert "origin=" not in baglanti
        assert veri["mod"] == "ara"

    def test_baglanti_url_disi_kaçamaz(self, sahte):
        veri = _bul()
        for sube in veri["subeler"]:
            baglanti = sube["baglanti"]
            assert baglanti.count("destination=") == 1
            assert "%2C" in baglanti


# ── Yönlendirme (kullanıcı isteğinden gelen parametreler) ──────────

class TestYonlendirme:
    def test_adet_sonucu_kisitlar(self, sahte):
        veri = _bul(adet=1)
        assert veri["sube_sayisi"] == 1
        assert len(veri["subeler"]) == 1

    def test_adet_sifir_tumunu_dondurur(self, sahte):
        veri = _bul(adet=0)
        assert veri["sube_sayisi"] == 2

    def test_yaricap_kisiti_uygulanir(self, sahte):
        veri = _bul(yaricap_km=1)
        assert veri["yaricap_km"] == 1.0

    def test_yaricap_tavana_kisitlanir(self, sahte):
        veri = _bul(yaricap_km=500)
        assert veri["yaricap_km"] == 25.0


# ── Hata yolları ────────────────────────────────────────────────────

class TestHataYollari:
    def test_bos_marka_hata(self, sahte):
        assert "error" in harita_dedektif("", "41.0111, 29.0254")

    def test_bos_konum_hata(self, sahte):
        assert "error" in harita_dedektif("BİM", "")

    def test_bilinmeyen_mod_hata(self, sahte):
        r = harita_dedektif("BİM", "41.0111, 29.0254", mod="ucak")
        assert "error" in r
        assert "ara" in r["error"] and "yol" in r["error"]

    def test_yaricap_disi_hata(self, sahte):
        assert "error" in harita_dedektif("BİM", "41.0111, 29.0254", 0)
        assert "error" in harita_dedektif("BİM", "41.0111, 29.0254", "fifth")

    def test_adet_disi_hata(self, sahte):
        assert "error" in harita_dedektif("BİM", "41.0111, 29.0254", adet=-1)
        assert "error" in harita_dedektif("BİM", "41.0111, 29.0254", adet=99)
        assert "error" in harita_dedektif("BİM", "41.0111, 29.0254",
                                          adet="cok")

    def test_bulunamayan_merkez_hata(self, sahte, monkeypatch):
        monkeypatch.setattr("tools.harita.konum_coz",
                            lambda adres: {"error": "Konum bulunamadı: x"})
        r = harita_dedektif("BİM", "Kayip Yer")
        assert "error" in r
        assert "Merkez bulunamadı" in r["error"]

    def test_servis_hatasi_hata_doner(self, sahte):
        sahte.hata = "HTTP 429 Too Many Requests"
        r = harita_dedektif("BİM", "41.0111, 29.0254")
        assert "error" in r
        assert "aynalar" in r["error"]

    def test_hata_yolunda_sube_ve_baglanti_uydurulmaz(self, sahte):
        sahte.hata = "HTTP 500"
        r = harita_dedektif("BİM", "41.0111, 29.0254")
        assert "result" not in r
        assert "google.com/maps" not in str(r)

    def test_sonuc_sifir_hata_degildir(self, monkeypatch):
        monkeypatch.setattr("tools.harita._json_al",
                            lambda url, sure=None: (BOS_GOVDE, None))
        veri = _bul()
        assert veri["sube_sayisi"] == 0
        assert veri["subeler"] == []
        assert "OSM" in veri["not"] or "OpenStreetMap" in veri["not"]


# ── Dört yer (AGENTS.md §0) ────────────────────────────────────────

class TestDortYer:
    def test_sema_kayitli(self):
        from tools.definitions import TANINMIS_TOOLLAR
        assert "harita_dedektif" in TANINMIS_TOOLLAR

    def test_dispatcher_dali_calisir(self, sahte):
        r = calistir("harita_dedektif",
                     {"marka": "BİM", "konum": "41.0111, 29.0254"})
        assert "error" not in r, r
        veri = json.loads(r["result"])
        assert veri["sube_sayisi"] == 2
        assert veri["zincir"][0] == "konum_coz"

    def test_dispatcher_parametreleri_aktarir(self, sahte):
        r = calistir("harita_dedektif",
                     {"marka": "BİM", "konum": "41.0111, 29.0254",
                      "yaricap_km": 3, "adet": 1, "mod": "ara"})
        veri = json.loads(r["result"])
        assert veri["yaricap_km"] == 3.0
        assert veri["sube_sayisi"] == 1
        assert veri["mod"] == "ara"

    def test_dispatcher_bos_markada_hata(self):
        assert "error" in calistir("harita_dedektif",
                                   {"marka": "", "konum": "x"})

    def test_yetenek_alaninda(self):
        from chat.agent_protocol import YETENEK_ALANLARI
        assert "harita_dedektif" in YETENEK_ALANLARI["harita"]

    def test_durum_etiketi_var(self):
        from chat.tools import DURUM_METNI
        assert DURUM_METNI.get("harita_dedektif")

    def test_durum_satirinda_marka_gorunur(self):
        from chat.tools import _durum
        assert "BİM" in _durum("harita_dedektif", {"marka": "BİM"})

    def test_kapasite_defteri_eksiksiz(self):
        from tools.capabilities import validate_registry
        sonuc = validate_registry()
        assert sonuc["ok"] is True
        assert sonuc["tool_count"] == 75
        assert sonuc["namespace_count"] == 17


# ── Sunucu olayı (Z2 yüzeyi) ────────────────────────────────────────

class TestOlay:
    def _sonuc(self, **ek):
        veri = {
            "marka": "BİM",
            "merkez": {"enlem": 41.0111, "boylam": 29.0254,
                       "gosterim_adi": "Moda, Kadıköy", "kaynak": "photon"},
            "yaricap_km": 5.0,
            "sube_sayisi": 1,
            "subeler": [{"ad": "BİM - Moda", "adres": "Moda Caddesi, 12",
                         "mesafe_km": 0.5,
                         "baglanti": YOL_TABANI + "41.015%2C%2029.029"
                                     + "&origin=41.0111%2C%2029.0254",
                         "ara_baglanti": ARAMA_TABANI + "41.015%2C%2029.029"}],
            "atif": "Veri: © OpenStreetMap katkıda bulunanlar (ODbL)",
        }
        veri.update(ek)
        return {"result": json.dumps(veri, ensure_ascii=False)}

    def test_zincir_sonucu_harita_olayi_uretir(self):
        from chat import tools as ct
        o = ct._harita_olayi("harita_dedektif", self._sonuc())
        assert o is not None
        assert o["enlem"] == 41.0111
        assert o["gosterim_adi"] == "Moda, Kadıköy"
        assert o["atf"] == "© OpenStreetMap contributors"

    def test_sube_listesi_olaya_tasir(self):
        from chat import tools as ct
        o = ct._harita_olayi("harita_dedektif", self._sonuc())
        assert len(o["subeler"]) == 1
        sube = o["subeler"][0]
        assert sube["ad"] == "BİM - Moda"
        assert sube["mesafe_km"] == 0.5
        assert "destination=" in sube["baglanti"]

    def test_sube_bul_da_olay_uretir(self):
        from chat import tools as ct
        o = ct._harita_olayi("sube_bul", self._sonuc())
        assert o is not None
        assert o["subeler"][0]["ad"] == "BİM - Moda"

    def test_bozuk_sube_listesi_olay_durdurmaz(self):
        from chat import tools as ct
        o = ct._harita_olayi("harita_dedektif",
                             self._sonuc(subeler="bozuk"))
        assert o is not None
        assert "subeler" not in o


# ── Web yüzeyi ──────────────────────────────────────────────────────

class TestWebYuzey:
    def test_sube_listesi_cizilir(self):
        assert "function subeListesi(subeler)" in JS
        assert 'liste.className = "map-card-branches"' in JS
        assert 'adEl.className = "map-card-branch-name"' in JS
        assert 'mesafeEl.className = "map-card-branch-distance"' in JS
        assert 'yol.className = "map-card-branch-link"' in JS

    def test_yol_baglantisi_yeni_sekmede_guvenli_acilir(self):
        assert 'yol.target = "_blank"' in JS
        assert 'yol.rel = "noopener noreferrer"' in JS

    def test_stiller_mevcut_degiskenleri_kullanir(self):
        for parca in (".map-card-branches{", ".map-card-branch-name{",
                      ".map-card-branch-distance{", ".map-card-branch-link{"):
            assert parca in CSS, parca
        for degisken in ("var(--line)", "var(--soft)", "var(--muted)",
                         "var(--ink)", "var(--bg)"):
            assert degisken in CSS

    def test_surum_kilidi_yukseltildi(self):
        assert "/chat.css?v=18" in HTML
        assert "/app.js?v=27" in HTML

    def test_harici_karo_yok(self):
        """D4b = B: zincir de karo yuklemez."""
        for imza in ("openfreemap", "leaflet", "maplibre",
                     "tile.openstreetmap", "tile."):
            assert imza not in JS.lower()
            assert imza not in CSS.lower()


# ── Z5: adım raporu (zincir akışı) ──────────────────────────────────

class TestAdimRaporu:
    def test_adimlar_zincir_sirasinda(self, sahte):
        veri = _bul()
        adlar = [a["ad"] for a in veri["adimlar"]]
        assert adlar == ["konum_coz", "sube_bul", "harita_goster"]
        assert adlar == veri["zincir"]

    def test_her_adim_baslik_ve_ozet_tasir(self, sahte):
        veri = _bul()
        for adim in veri["adimlar"]:
            assert adim["baslik"], adim
            assert adim["ozet"], adim
            assert adim["durum"] in ("tamam", "bos")

    def test_adim_ozetleri_gercek_sayilardir(self, sahte):
        veri = _bul()
        assert "2 şube bulundu" in veri["adimlar"][1]["ozet"]
        # 2 şube × 2 baglanti + 1 merkez = 5
        assert "5 bağlantı üretildi" in veri["adimlar"][2]["ozet"]

    def test_bos_sonucta_adim_bos_isaretlenir(self, monkeypatch):
        monkeypatch.setattr("tools.harita._json_al",
                            lambda url, sure=None: (BOS_GOVDE, None))
        veri = _bul()
        assert veri["adimlar"][1]["durum"] == "bos"
        assert veri["adimlar"][2]["durum"] == "tamam"  # merkez baglantisi

    def test_adim_raporu_hata_yolunda_uydurulmaz(self, sahte):
        sahte.hata = "HTTP 500"
        r = harita_dedektif("BİM", "41.0111, 29.0254")
        assert "result" not in r
        assert "adimlar" not in str(r)


# ── Z5: adım raporu olayı ───────────────────────────────────────────

class TestAdimOlayi:
    def _sonuc(self):
        veri = {
            "merkez": {"enlem": 41.0111, "boylam": 29.0254,
                       "gosterim_adi": "Moda, Kadıköy", "kaynak": "photon"},
            "subeler": [],
            "adimlar": [
                {"ad": "konum_coz", "durum": "tamam",
                 "baslik": "Konum çözüldü", "ozet": "merkez: Moda"},
                {"ad": "sube_bul", "durum": "bos",
                 "baslik": "Şubeler arandı", "ozet": "0 şube bulundu (5.0 km)"},
            ],
        }
        return {"result": json.dumps(veri, ensure_ascii=False)}

    def test_adimlar_olaya_tasir(self):
        from chat import tools as ct
        o = ct._harita_olayi("harita_dedektif", self._sonuc())
        assert len(o["adimlar"]) == 2
        assert o["adimlar"][0]["baslik"] == "Konum çözüldü"
        assert o["adimlar"][1]["durum"] == "bos"

    def test_bozuk_adim_olayi_durdurmaz(self):
        from chat import tools as ct
        veri = json.loads(self._sonuc()["result"])
        veri["adimlar"] = "bozuk"
        o = ct._harita_olayi("harita_dedektif",
                             {"result": json.dumps(veri)})
        assert o is not None
        assert "adimlar" not in o

    def test_js_tarafi_metin_uydurmaz(self):
        # zincirAkisi yalnız sunucunun baslik/ozet alanlarını gösterir.
        assert "function zincirAkisi(adimlar)" in JS
        assert "adim?.baslik" in JS or "adim.baslik" in JS
        for sinif in (".map-card-chain{", ".map-card-chain-step{",
                      ".map-card-chain-title{", ".map-card-chain-detail{"):
            assert sinif in CSS, sinif

    def test_hareket_azaltma_desteklenir(self):
        assert "prefers-reduced-motion" in CSS


# ── Z5: kullanıcı istem formu ───────────────────────────────────────

class TestIstemFormu:
    def test_form_alanlari_html_de(self):
        for alan in ("haritaForm", "haritaMarka", "haritaKonum",
                     "haritaYaricap", "haritaIstek", "haritaGonder"):
            assert 'id="%s"' % alan in HTML, alan

    def test_form_acma_dugmesi_bagli(self):
        assert 'id="haritaButton"' in HTML
        assert "haritaButton.addEventListener" in JS
        assert "haritaFormunuAc" in JS

    def test_istek_metni_duz_metindir_arac_secmesi_yok(self):
        # AGENTS.md §0: kod kullanıcı metninden araç/alan seçmez.
        assert "function haritaIstegiOlustur()" in JS
        govde = JS[JS.index("function haritaIstegiOlustur()"):]
        govde = govde[:govde.index("\n}")]
        assert "harita_dedektif" not in govde
        assert "sube_bul" not in govde
        assert "konum_coz" not in govde
        assert "harita_goster" not in govde

    def test_gonder_normal_akisi_kullanir(self):
        # İstek, sohbetin normal gönderme yolundan gider (send).
        govde = JS[JS.index("haritaGonderEl.addEventListener"):]
        govde = govde[:govde.index("\n}")]
        assert "send({ text: metin })" in govde

    def test_erisilebilirlik(self):
        for alan in ("haritaMarka", "haritaKonum", "haritaYaricap",
                     "haritaIstek"):
            assert 'for="%s"' % alan in HTML, alan
        assert 'role="alert"' in HTML
        assert "Escape" in JS
