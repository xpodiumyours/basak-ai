"""tests/test_harita_z1.py — Z1: konum_coz (adres → enlem/boylam).

Kabul olcusu: docs/HARITA-ZINCIRI-PLANI.md, FAZ 2.
- Gercek adres -> koordinat dunya araliginda
- Bulunamayan adres -> hata, koordinat UYDURULMAZ
- SSRF: ic/ozel ag adresi aga CIKMADAN reddedilir; koruma ortak
  (tools/web_search) savunmadan cagrilir, burada yeniden yazilmaz
- Fallback: Photon basarisizsa Open-Meteo geocoding denenir
- Dordun dordu de dolu: sema + dispatcher dali + yetenek alani +
  durum etiketi

Butun testler cevrimdisi: ag cagrisi yapilmaz, sahte yanit enjekte edilir.
"""

import json
import os
import sys
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools import calistir
from tools.harita import KONUM_TAVANI, _json_al, konum_coz

# Gercekci Photon govdesi: GeoJSON coordinates = [boylam, enlem].
PHOTON_GOVDE = {
    "features": [
        {"geometry": {"coordinates": [29.0254, 41.0111]},
         "properties": {"name": "Moda", "street": "Moda Caddesi",
                        "district": "Kadikoy", "city": "Istanbul",
                        "country": "Turkiye", "osm_id": 123,
                        "osm_value": "neighbourhood",
                        "postcode": "34710", "countrycode": "TR"}},
        {"geometry": {"coordinates": [28.9784, 41.0082]},
         "properties": {"name": "Istanbul", "city": "Istanbul",
                        "country": "Turkiye"}},
    ],
}

OPEN_METEO_GOVDE = {
    "results": [{"name": "Istanbul", "latitude": 41.01384,
                 "longitude": 28.94966, "admin1": "Istanbul",
                 "country": "Turkiye", "country_code": "TR",
                 "feature_code": "PPLA", "postcodes": ["34000"]}],
}


class SahteHat:
    """urllib yerine gecen sahte hat: cagrilan adresleri kaydeder."""

    def __init__(self, photon=PHOTON_GOVDE, open_meteo=OPEN_METEO_GOVDE):
        self.photon = photon
        self.open_meteo = open_meteo
        self.adresler = []
        self.hata = None

    def __call__(self, url):
        self.adresler.append(url)
        if self.hata is not None:
            return None, self.hata
        if "photon" in url:
            if self.photon is None:
                return None, "servise ulasilamadi"
            return self.photon, None
        if self.open_meteo is None:
            return None, "servise ulasilamadi"
        return self.open_meteo, None


@pytest.fixture
def sahte(monkeypatch):
    hat = SahteHat()
    monkeypatch.setattr("tools.harita._json_al", hat)
    return hat


def _coz(adres):
    """Basari yolundan 'result' JSON'unu cozer; hata varsa None doner."""
    r = konum_coz(adres)
    if "error" in r:
        return None
    return json.loads(r["result"])


# ── Koordinat cozumu ──────────────────────────────────────────────

class TestKoordinatCozumu:
    def test_photon_yaniti_koordinata_cevrilir(self, sahte):
        veri = _coz("Moda, Kadikoy")
        assert veri["kaynak"] == "photon"
        assert veri["gosterim_adi"].startswith("Moda")
        assert veri["aday_sayisi"] == 2
        assert len(veri["adaylar"]) == 2

    def test_geojson_sirasi_karistirilmaz(self, sahte):
        """GeoJSON [boylam, enlem] verir; ters yazilirsa TR koordinati
        Afrika'ya duser. Bu test o hatayi yakalar."""
        veri = _coz("Moda, Kadikoy")
        assert veri["enlem"] == 41.0111
        assert veri["boylam"] == 29.0254

    def test_koordinat_dunya_araliginda(self, sahte):
        veri = _coz("Moda, Kadikoy")
        assert -90.0 <= veri["enlem"] <= 90.0
        assert -180.0 <= veri["boylam"] <= 180.0
        for aday in veri["adaylar"]:
            assert -90.0 <= aday["enlem"] <= 90.0
            assert -180.0 <= aday["boylam"] <= 180.0

    def test_adres_sorguya_kacirilarak_girer(self, sahte):
        _coz("Şişli/İstanbul")
        adres = sahte.adresler[0]
        assert " " not in adres.split("q=")[1].split("&")[0]
        assert "%C5%9E" in adres or "%C5%9F" in adres

    def test_limit_parametresi_ve_gecersiz_dil_yok(self, sahte):
        """Photon yalniz de/en/fr/it kabul eder; lang=tr canli olculdu ve
        HTTP 400 dondurdu (tum birincil hat yedege dusuyordu). """
        _coz("Ankara")
        adres = sahte.adresler[0]
        assert "photon" in adres
        assert "limit=5" in adres
        assert "lang=" not in adres

    def test_adres_alani_girdiyi_yansitir(self, sahte):
        veri = _coz("  Moda,   Kadikoy ")
        assert veri["adres"] == "Moda, Kadikoy"


# ── Hata yollari: uydurma koordinat yok ───────────────────────────

class TestHataYollari:
    def test_bos_adres_hata(self):
        assert "error" in konum_coz("")
        assert "error" in konum_coz("   ")
        assert "error" in konum_coz(None)

    def test_asiri_uzun_adres_hata(self):
        assert "error" in konum_coz("a" * (KONUM_TAVANI + 1))

    def test_bulunamayan_adres_hata_ve_koordinat_yok(self, monkeypatch):
        hat = SahteHat(photon={"features": []}, open_meteo={"results": []})
        monkeypatch.setattr("tools.harita._json_al", hat)
        r = konum_coz("zzz bilinmeyen yer zzz")
        assert "error" in r
        assert "result" not in r
        assert "enlem" not in str(r)

    def test_photon_hataliyken_open_meteo_denenir(self, monkeypatch):
        hat = SahteHat(photon=None, open_meteo=OPEN_METEO_GOVDE)
        monkeypatch.setattr("tools.harita._json_al", hat)
        veri = _coz("Istanbul")
        assert veri["kaynak"] == "open-meteo"
        assert veri["enlem"] == 41.01384
        assert veri["boylam"] == 28.94966
        assert len(hat.adresler) == 2, "iki hat da denenmeli"
        assert "photon" in hat.adresler[0]
        assert "geocoding-api.open-meteo.com" in hat.adresler[1]

    def test_iki_hat_da_yoksa_hata(self, monkeypatch):
        hat = SahteHat(photon=None, open_meteo=None)
        monkeypatch.setattr("tools.harita._json_al", hat)
        assert "error" in konum_coz("Istanbul")

    def test_iki_hat_da_bossa_hata_ve_hatlar_yazilir(self, monkeypatch):
        hat = SahteHat(photon={"features": []}, open_meteo=None)
        monkeypatch.setattr("tools.harita._json_al", hat)
        hata = konum_coz("Istanbul")["error"]
        assert "open-meteo" in hata

    def test_aralik_disi_koordinat_kabul_edilmez(self, monkeypatch):
        """Bozuk servis yaniti (enlem 300) koordinat sayilmaz."""
        bozuk = {"features": [{"geometry": {"coordinates": [29.0, 300.0]},
                               "properties": {"name": "X"}}]}
        hat = SahteHat(photon=bozuk, open_meteo=None)
        monkeypatch.setattr("tools.harita._json_al", hat)
        r = konum_coz("X")
        assert "error" in r

    def test_bozuk_govde_cokme_yerine_hata(self, monkeypatch):
        monkeypatch.setattr("tools.harita._json_al", lambda url: ("metin", None))
        assert "error" in konum_coz("Ankara")

    def test_yanlis_eslesme_gizlenmez(self, monkeypatch):
        """Bilinen sinir (2026-10-01 canli olcum): Photon bulanik eslesir,
        sacma sorguya da aday dondurur (orn. UK posta kodu). Arac adayi
        GIZLEMEZ; servisin kendi gosterim adi ve aday sayisi doner, boylece
        uyusmazlik gorunur kalir ve model kararini ona gore verir."""
        sacma = {"features": [{"geometry": {"coordinates": [-2.63907, 50.94154]},
                               "properties": {"name": "BA20 9ZZ",
                                              "city": "Yeovil",
                                              "country": "United Kingdom"}}]}
        hat = SahteHat(photon=sacma)
        monkeypatch.setattr("tools.harita._json_al", hat)
        veri = _coz("zzz bilinmeyen yer zzz")
        assert "Yeovil" in veri["gosterim_adi"]
        assert veri["aday_sayisi"] == 1


# ── SSRF: ortak savunma, aga cikmadan ─────────────────────────────

class TestSsrfKorumasi:
    def _agi_kapat(self, monkeypatch):
        def _patlat(*a, **k):
            raise AssertionError("SSRF engelli adres icin aga cikildi")
        monkeypatch.setattr(urllib.request, "build_opener", _patlat)

    def test_loopback_aga_cikmadan_reddedilir(self, monkeypatch):
        self._agi_kapat(monkeypatch)
        veri, hata = _json_al("http://127.0.0.1/ic")
        assert veri is None and hata

    def test_ozel_ag_aga_cikmadan_reddedilir(self, monkeypatch):
        self._agi_kapat(monkeypatch)
        veri, hata = _json_al("http://192.168.1.10/gizli")
        assert veri is None and hata

    def test_standart_disi_port_reddedilir(self, monkeypatch):
        self._agi_kapat(monkeypatch)
        veri, hata = _json_al("https://example.com:8080/x")
        assert veri is None and hata

    def test_http_disi_sema_reddedilir(self, monkeypatch):
        self._agi_kapat(monkeypatch)
        veri, hata = _json_al("file:///etc/passwd")
        assert veri is None and hata

    def test_koruma_ortak_savunmadan_cagrilir(self):
        """Yeni SSRF savunmasi YAZILMADI: web_search'teki ortak uc kullanilir."""
        import inspect

        import tools.harita as harita
        kaynak = inspect.getsource(harita)
        assert "from tools.web_search import _guvenli_adres, _GuvenliYonlendirme" \
            in kaynak
        assert "_GuvenliYonlendirme()" in inspect.getsource(harita._json_al)
        assert "def _engelli_ip_nedeni" not in kaynak
        assert "def _guvenli_adres" not in kaynak

    def test_gercek_adres_icin_denetim_engel_dondurmez(self):
        from tools.web_search import _guvenli_adres
        assert _guvenli_adres("https://photon.komoot.io/api/?q=Ankara") is None


# ── Hat görünürlüğü: sessiz bozulma imkânsız ─────────────────────

class TestDenenenHatlar:
    """2026-10-01 dersi: `lang=tr` birincil hattı bozduğu halde hata
    "servise ulasilamadi" diye yutuldu; kusur sessizce yedeğe düştü.
    Artık her hattın durumu ve hata SEBEBİ çıktıda görünür."""

    def test_basarili_hattaki_aday_sayisi_yazilir(self, sahte):
        veri = _coz("Moda, Kadikoy")
        assert veri["denenen_hatlar"] == [
            {"kaynak": "photon", "durum": "ok", "aday_sayisi": 2}]

    def test_yedek_hat_denendiyse_gerekcesi_gorunur(self, monkeypatch):
        hat = SahteHat(photon=None)
        monkeypatch.setattr("tools.harita._json_al", hat)
        veri = _coz("Istanbul")
        assert veri["denenen_hatlar"][0] == {
            "kaynak": "photon", "durum": "hata",
            "hata": "servise ulasilamadi"}
        assert veri["denenen_hatlar"][1]["kaynak"] == "open-meteo"

    def test_hata_mesaji_denenen_hatlari_soyler(self, monkeypatch):
        hat = SahteHat(photon=None, open_meteo={"results": []})
        monkeypatch.setattr("tools.harita._json_al", hat)
        hata = konum_coz("zzz")["error"]
        assert "photon" in hata and "open-meteo" in hata
        assert "servise ulasilamadi" in hata

    def test_http_hatasinin_sebebi_yutulmaz(self, monkeypatch):
        """Canlı bulguyu kilitler: HTTP 400 artık gizlenmiyor."""
        def patlat(*a, **k):
            raise urllib.error.HTTPError(
                "https://photon.komoot.io/api/", 400, "Bad Request", {}, None)
        monkeypatch.setattr(urllib.request, "build_opener", patlat)
        veri, hata = _json_al("https://photon.komoot.io/api/?q=Tuzla")
        assert veri is None
        assert hata.startswith("HTTP 400") and "Bad Request" in hata

    def test_ssrf_engeli_de_hata_sebebi_olarak_doner(self):
        _veri, hata = _json_al("http://127.0.0.1/ic")
        assert "cozuldu" in hata


class TestAdayZenginligi:
    def test_photon_adayinda_posta_ve_ulke_kodu(self, sahte):
        aday = _coz("Moda, Kadikoy")["adaylar"][0]
        assert aday["posta_kodu"] == "34710"
        assert aday["ulke_kodu"] == "TR"
        assert aday["tip"] == "neighbourhood"

    def test_iki_hat_ayni_sekli_dondurur(self, monkeypatch):
        """Yedek hat da aday LİSTESİ döndürür (eskiden tek aday + boş
        liste dönüyordu)."""
        hat = SahteHat(photon=None)
        monkeypatch.setattr("tools.harita._json_al", hat)
        veri = _coz("Istanbul")
        assert veri["kaynak"] == "open-meteo"
        assert veri["aday_sayisi"] == len(veri["adaylar"]) == 1
        assert veri["adaylar"][0]["ulke_kodu"] == "TR"
        assert veri["adaylar"][0]["tip"] == "PPLA"
        assert veri["adaylar"][0]["posta_kodu"] == "34000"

    def test_yedek_hata_bes_aday_ister(self, monkeypatch):
        hat = SahteHat(photon=None)
        monkeypatch.setattr("tools.harita._json_al", hat)
        _coz("Istanbul")
        assert "count=5" in hat.adresler[1]


# ── Dort yer (AGENTS.md §0) ───────────────────────────────────────

class TestDortYer:
    def test_sema_kayitli(self):
        from tools.definitions import TANINMIS_TOOLLAR
        assert "konum_coz" in TANINMIS_TOOLLAR

    def test_dispatcher_dali_calisir(self, sahte):
        r = calistir("konum_coz", {"adres": "Moda, Kadikoy"})
        assert "error" not in r, r
        veri = json.loads(r["result"])
        assert veri["kaynak"] == "photon"

    def test_dispatcher_bos_adreste_hata(self):
        assert "error" in calistir("konum_coz", {"adres": ""})

    def test_yetenek_alaninda(self):
        from chat.agent_protocol import YETENEK_ALANLARI
        assert "konum_coz" in YETENEK_ALANLARI["harita"]

    def test_alan_sayisi_ve_namespace_degismedi(self):
        """Yeni arac AYNI alana girdi: namespace 15 kalir."""
        from chat.agent_protocol import ALAN_ACIKLAMALARI, YETENEK_ALANLARI
        assert len(YETENEK_ALANLARI) == 15
        assert set(ALAN_ACIKLAMALARI) == set(YETENEK_ALANLARI)

    def test_alan_aciklamasi_koordinati_soyler(self):
        from chat.agent_protocol import ALAN_ACIKLAMALARI
        assert "koordinat" in ALAN_ACIKLAMALARI["harita"]

    def test_durum_etiketi_var(self):
        from chat.tools import DURUM_METNI
        assert DURUM_METNI.get("konum_coz")

    def test_durum_satirinda_adres_gorunur(self):
        from chat.tools import _durum
        assert "Kadikoy" in _durum("konum_coz", {"adres": "Kadikoy"})

    def test_kapasite_defteri_eksiksiz(self):
        from tools.capabilities import validate_registry
        sonuc = validate_registry()
        assert sonuc["ok"] is True
        assert sonuc["tool_count"] == 57
        assert sonuc["namespace_count"] == 15


# ── Uctan uca: sirket_ara adresi -> koordinat (cevrimdisi) ────────

class TestUctanUca:
    def test_sirket_ara_adresi_konum_coza_girer(self, monkeypatch):
        """Adres metni olu kalmasin: ayni metin koordinata cevrilebilir."""
        from tools import katalog

        monkeypatch.setattr(katalog, "sirket_ara",
                            lambda marka: {"marka": marka,
                                           "adresler": ["Moda, Kadikoy"]})
        adres = katalog.sirket_ara("Tutku")["adresler"][0]

        hat = SahteHat()
        monkeypatch.setattr("tools.harita._json_al", hat)
        veri = _coz(adres)
        assert veri["enlem"] == 41.0111 and veri["boylam"] == 29.0254
