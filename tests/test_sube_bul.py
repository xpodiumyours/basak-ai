"""tests/test_sube_bul.py — Z3: sube_bul (marka + bolge -> kayitli subeler).

Kabul olcusu: ucretsiz kombin — OpenStreetMap Overpass, anahtar yok.
- Overpass yaniti sube kayitlarina cevrilir (en yakin ilk, mesafe hesapli)
- Merkez 'enlem,boylam' dogrudan okunur; adres konum_coz'e devredilir
- Sonuc 0: hata DEGIL — OSM'de kayitli degil notu yazilir (uydurma yok)
- Servis hatasi: hata doner, sube UYDURULMAZ
- Yaricap sinirlanir (25 km tavani); gecersiz girdi hata doner
- Marka regex olarak kacirilir (kullanici girdisi desen olamaz)
- Dordun dortu de dolu: sema + dispatcher dali + yetenek alani + durum

Butun testler cevrimdisi: ag cagrisi yapilmaz, sahte Overpass yaniti
enjekte edilir.
"""

import json
import os
import sys
import urllib.parse

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools import calistir
from tools.harita import (_YARICAP_TAVANI, _mesafe_km, _overpass_sorgusu,
                          sube_bul)

MERKEZ_ENLEM, MERKEZ_BOYLAM = 41.0111, 29.0254

# Gercekci Overpass govdesi: bir node, bir way (center ile), bir de
# gecersiz eleman (merkezsiz way + bozuk tip) — hepsi ayni yanitta.
OVERPASS_GOVDE = {
    "elements": [
        {"type": "node", "id": 1, "lat": 41.0150, "lon": 29.0290,
         "tags": {"name": "BİM - Moda", "brand": "BİM", "shop": "supermarket",
                  "addr:street": "Moda Caddesi", "addr:housenumber": "12",
                  "addr:city": "Istanbul", "phone": "+90 212 000 00 00"}},
        {"type": "way", "id": 2,
         "center": {"lat": 41.0200, "lon": 29.0350},
         "tags": {"name": "BİM Caferağa", "brand": "BİM",
                  "shop": "supermarket", "website": "https://bim.com.tr"}},
        {"type": "way", "id": 3,
         "tags": {"name": "merkezsiz"}},
        {"type": "relation", "id": 4,
         "center": {"lat": "bozuk", "lon": 29.0},
         "tags": {"name": "BİM Kopru"}},
    ],
}

BOS_GOVDE = {"elements": []}


class SahteHat:
    """urllib yerine gecen sahte Overpass hatti.

    `hata`: tum aynalar hata doner. `ilk_ayna_hatali`: ilk ayna (ana
    sunucu) hata doner, sonrakiler basarili — fallback yolu icin.
    """

    def __init__(self, govde=OVERPASS_GOVDE, ilk_ayna_hatali=False):
        self.govde = govde
        self.adresler = []
        self.hata = None
        self.ilk_ayna_hatali = ilk_ayna_hatali

    def __call__(self, url, sure=None):
        self.adresler.append(url)
        if self.hata is not None:
            return None, self.hata
        if self.ilk_ayna_hatali and "overpass-api.de" in url:
            return None, "HTTP 406 Not Acceptable"
        if self.govde is None:
            return None, "servise ulasilamadi"
        return self.govde, None


@pytest.fixture
def sahte(monkeypatch):
    hat = SahteHat()
    monkeypatch.setattr("tools.harita._json_al", hat)
    return hat


def _bul(marka="BİM", konum="41.0111, 29.0254", yaricap_km=None):
    """Basari yolundan 'result' JSON'unu cozer; hata varsa None doner."""
    r = sube_bul(marka, konum, yaricap_km)
    if "error" in r:
        return None
    return json.loads(r["result"])


# ── Sube kaydi donusumu ───────────────────────────────────────────

class TestSubeDonusumu:
    def test_overpass_yaniti_subeye_cevrilir(self, sahte):
        veri = _bul()
        assert veri["marka"] == "BİM"
        assert veri["sube_sayisi"] == 2  # merkezsiz/bozuk elemanlar atlandi
        ad = [s["ad"] for s in veri["subeler"]]
        assert ad == ["BİM - Moda", "BİM Caferağa"]

    def test_en_yakin_ilk_siralanir(self, sahte):
        veri = _bul()
        mesafeler = [s["mesafe_km"] for s in veri["subeler"]]
        assert mesafeler == sorted(mesafeler)
        assert mesafeler[0] > 0

    def test_adres_ve_iletisim_alanlari_tasinir(self, sahte):
        veri = _bul()
        ilk = veri["subeler"][0]
        assert ilk["adres"] == "Moda Caddesi, 12, Istanbul"
        assert ilk["telefon"] == "+90 212 000 00 00"
        assert ilk["tip"] == "supermarket"
        assert veri["subeler"][1]["website"] == "https://bim.com.tr"

    def test_osm_id_ve_tip_kayitli(self, sahte):
        veri = _bul()
        assert veri["subeler"][0]["osm_id"] == 1
        assert veri["subeler"][0]["osm_tip"] == "node"
        assert veri["subeler"][1]["osm_tip"] == "way"

    def test_osm_atfi_tasir(self, sahte):
        veri = _bul()
        assert "OpenStreetMap" in veri["atif"]

    def test_merkez_kayitli(self, sahte):
        veri = _bul(konum="41.0111,29.0254")
        assert veri["merkez"]["enlem"] == 41.0111
        assert veri["merkez"]["boylam"] == 29.0254
        assert veri["merkez"]["kaynak"] == "koordinat"


# ── Mer cozumu ────────────────────────────────────────────────────

class TestMerkez:
    def test_adres_konum_coz_e_devredilir(self, sahte, monkeypatch):
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

    def test_bulunamayan_merkez_hata(self, sahte, monkeypatch):
        monkeypatch.setattr("tools.harita.konum_coz",
                            lambda adres: {"error": "Konum bulunamadı: x"})
        assert "error" in sube_bul("BİM", "Kayip Yer")


# ── Sonuc 0 ve hata yollari ───────────────────────────────────────

class TestHataYollari:
    def test_sonuc_sifir_hata_degildir(self, monkeypatch):
        monkeypatch.setattr("tools.harita._json_al",
                            lambda url, sure=None: (BOS_GOVDE, None))
        veri = _bul()
        assert veri["sube_sayisi"] == 0
        assert veri["subeler"] == []
        assert "OSM" in veri["not"] or "OpenStreetMap" in veri["not"]

    def test_servis_hatasi_hata_doner(self, sahte):
        sahte.hata = "HTTP 429 Too Many Requests"
        r = sube_bul("BİM", "41.0111, 29.0254")
        assert "error" in r
        assert "429" in r["error"]
        # Tum aynalar denenir, hata mesaji hangilerinin denendigini soyler.
        # 2026-10-21: Overpass aynalari tikandiginda Photon yedek hatti da
        # denenir (ayni OSM kayitlari) — yani 3 + 1 istek.
        overpass = [u for u in sahte.adresler if "overpass" in u]
        assert len(overpass) == 3
        assert any("photon" in u for u in sahte.adresler)
        assert "aynalar" in r["error"]

    def test_ilk_ayna_bozuk_ikinciden_devralir(self, monkeypatch):
        hat = SahteHat(ilk_ayna_hatali=True)
        monkeypatch.setattr("tools.harita._json_al", hat)
        veri = _bul()
        assert veri["sube_sayisi"] == 2
        assert len(hat.adresler) == 2  # ana sunucu + kumi; ucuncuya gerek kalmadi
        assert veri["denenen_hatlar"][0]["durum"] == "hata"
        assert "406" in veri["denenen_hatlar"][0]["hata"]
        assert veri["denenen_hatlar"][1]["durum"] == "ok"

    def test_basarili_tek_aynada_duranir(self, sahte):
        veri = _bul()
        assert len(sahte.adresler) == 1
        assert veri["denenen_hatlar"] == [
            {"ayna": "https://overpass-api.de/api/interpreter",
             "durum": "ok"}]

    def test_bos_marka_hata(self):
        assert "error" in sube_bul("", "41.0111, 29.0254")

    def test_bos_konum_hata(self):
        assert "error" in sube_bul("BİM", "")

    def test_bos_merkez_kaynagi_hatada_gorunur(self, sahte, monkeypatch):
        monkeypatch.setattr("tools.harita.konum_coz",
                            lambda adres: {"error": "Konum bulunamadı: y"})
        r = sube_bul("BİM", "yok boyle yer")
        assert "Konum bulunamadı" in r["error"]


# ── Yaricap sinirlari ─────────────────────────────────────────────

class TestYaricap:
    def test_varsayilan_yaricap(self, sahte):
        veri = _bul()
        assert veri["yaricap_km"] == 5.0

    def test_yaricap_tavana_kisitlanir(self, sahte):
        veri = _bul(yaricap_km=500)
        assert veri["yaricap_km"] == _YARICAP_TAVANI

    def test_sayi_dismi_red(self):
        assert "error" in sube_bul("BİM", "41.0111, 29.0254", "fifth")
        assert "error" in sube_bul("BİM", "41.0111, 29.0254", 0)
        assert "error" in sube_bul("BİM", "41.0111, 29.0254", -3)

    def test_sorguda_yaricap_gecer(self, sahte):
        _bul(yaricap_km=12)
        sorgu = _sorgu_metni(sahte.adresler[0])
        assert "around:12000," in sorgu


# ── Guvenlik: marka regex kacisi + Overpass sorgu bicimi ──────────

def _sorgu_metni(url):
    """Sahte hatta yakalanan URL'den Overpass QL metnini cozer."""
    return urllib.parse.unquote(urllib.parse.urlsplit(url).query
                                .replace("data=", "", 1))


class TestGuvenlik:
    def test_marka_regex_olarak_kacirilir(self, sahte):
        _bul(marka="A(B)[C]")
        sorgu = _sorgu_metni(sahte.adresler[0])
        assert "A\\(B\\)\\[C\\]" in sorgu
        assert '"name"~"A(B)[C]"' not in sorgu

    def test_sorgu_dort_dal_tasir(self, sahte):
        _bul()
        sorgu = _sorgu_metni(sahte.adresler[0])
        for dal in ('node(around:', 'way(around:', '"brand"~', '"name"~'):
            assert dal in sorgu

    def test_sorgu_ureticisi_baslik_tasir(self):
        sorgu = _overpass_sorgusu(MERKEZ_ENLEM, MERKEZ_BOYLAM, 5000, "BİM")
        assert sorgu.startswith("[out:json]")
        assert "out center" in sorgu

    def test_mesafe_haversine_dogruluguna(self):
        # Ayni nokta: 0 km. Kuzeyde ~1 derece: ~111 km.
        assert _mesafe_km(41.0, 29.0, 41.0, 29.0) == 0.0
        yaklasik = _mesafe_km(41.0, 29.0, 42.0, 29.0)
        assert 110 < yaklasik < 112


# ── Dort yer (AGENTS.md §0) ──────────────────────────────────────

class TestDortYer:
    def test_sema_kayitli(self):
        from tools.definitions import TANINMIS_TOOLLAR
        assert "sube_bul" in TANINMIS_TOOLLAR

    def test_dispatcher_dali_calisir(self, sahte):
        r = calistir("sube_bul", {"marka": "BİM", "konum": "41.0111, 29.0254"})
        assert "error" not in r, r
        veri = json.loads(r["result"])
        assert veri["sube_sayisi"] == 2

    def test_dispatcher_bos_markada_hata(self):
        assert "error" in calistir("sube_bul", {"marka": "", "konum": "x"})

    def test_yetenek_alaninda(self):
        from chat.agent_protocol import YETENEK_ALANLARI
        assert "sube_bul" in YETENEK_ALANLARI["harita"]

    def test_durum_etiketi_var(self):
        from chat.tools import DURUM_METNI
        assert DURUM_METNI.get("sube_bul")

    def test_durum_satirinda_marka_gorunur(self):
        from chat.tools import _durum
        assert "BİM" in _durum("sube_bul", {"marka": "BİM"})

    def test_kapasite_defteri_eksiksiz(self):
        from tools.capabilities import validate_registry
        sonuc = validate_registry()
        assert sonuc["ok"] is True
        assert sonuc["tool_count"] == 60
        assert sonuc["namespace_count"] == 16
