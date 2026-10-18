"""tests/test_harita_z3.py — Z3 katmani: yakin_ara (Overpass) +
mesafe_sure (OSRM) birim testleri.

Tum ag cagrilari monkeypatch ile sahtelestirilir; testler gercek ag'a
bagli degildir. Canli kanitlar (2026-10-18) ayrica notlandi:
- yakin_ara('Kadikoy Moda, Istanbul','eczane',1000) -> 15 sonuc, 4,0 sn
- mesafe_sure('Kadikoy Moda','Taksim','araba') -> 15,7 km / 19,8 dk
"""

import json

import pytest

from tools import harita


# ── yardimcilar ────────────────────────────────────────────────────

def _overpass_oge(oge_id, enlem, boylam, ad, tip_anahtar, tip):
    return {
        "type": "node", "id": oge_id, "lat": enlem, "lon": boylam,
        "tags": {"name": ad, tip_anahtar: tip},
    }


def _overpass_veri(ogeler):
    return {"version": 0.6, "generator": "test",
            "elements": list(ogeler)}


def _osrm_ok(mesafe_m, sure_s):
    return {"code": "Ok",
            "routes": [{"distance": mesafe_m, "duration": sure_s}]}


@pytest.fixture(autouse=True)
def _onbellek_temiz():
    harita._ONBELLEK.clear()
    yield
    harita._ONBELLEK.clear()


# ── mesafe hesabi ─────────────────────────────────────────────────

def test_haversine_bilinen_mesafe():
    # Ayni nokta = 0
    assert harita._mesafe_m(41.0, 29.0, 41.0, 29.0) == 0.0
    # 1 derece boylam, ekvator cizgisinde ~111 km
    m = harita._mesafe_m(0.0, 29.0, 0.0, 30.0)
    assert 110_500 < m < 112_000


def test_koordinat_metni():
    assert harita._koordinat_metni("41.02, 29.09") == (41.02, 29.09)
    assert harita._koordinat_metni("95, 10") is None      # enlem aralik disi
    assert harita._koordinat_metni("Istanbul") is None
    assert harita._koordinat_metni("") is None


# ── yakin_ara: giris denetimi ─────────────────────────────────────

def test_yakin_ara_bos_girisler_hata():
    assert "error" in harita.yakin_ara("", "eczane")
    assert "error" in harita.yakin_ara("Kadikoy", "")
    assert "Desteklenenler" in harita.yakin_ara("Kadikoy", "")["error"]
    # uzun merkez
    assert "error" in harita.yakin_ara("x" * 400, "eczane")


def test_yakin_ara_bilinmeyen_tabir_uydurma_yok():
    sonuc = harita.yakin_ara("Kadikoy Moda", "yildiz gazinosu")
    assert "error" in sonuc
    assert "Desteklenenler" in sonuc["error"]


def test_yakin_ara_yaricap_denetimi():
    assert "error" in harita.yakin_ara("Kadikoy", "eczane", 30)
    assert "error" in harita.yakin_ara("Kadikoy", "eczane", 10001)
    assert "error" in harita.yakin_ara("Kadikoy", "eczane", "elma")
    # bos -> varsayilan 1000 kullanilir (mock ajanin bekledigi değer)


# ── yakin_ara: ag akisi (mocklu) ─────────────────────────────────,


def test_yakin_ara_sirali_ve_isimsizler_atlanir(monkeypatch):
    ogeler = [
        _overpass_oge(1, 40.9800, 29.0200, "Yakin", "amenity", "pharmacy"),
        _overpass_oge(2, 40.9850, 29.0250, "Uzak", "amenity", "pharmacy"),
        {"type": "node", "id": 3, "lat": 40.9810, "lon": 29.0210,
         "tags": {"amenity": "pharmacy"}},  # isimsiz
        _overpass_oge(1, 40.98000, 29.02000, "Yakin", "amenity",
                      "pharmacy"),  # kopya (ayni yuvarlandimis koordinat)
    ]

    monkeypatch.setattr(harita, "_merkezi_coz", lambda metin: (
        {"enlem": 40.98, "boylam": 29.02, "gosterim_adi": "Moda",
         "kaynak": "girilen koordinat"}, None))
    monkeypatch.setattr(harita, "_overpass_json_al",
                        lambda sorgu: (_overpass_veri(ogeler), "hat", None))

    sonuc = harita.yakin_ara("40.98,29.02", "ECZANE")   # buyuk harf de cozer
    assert "result" in sonuc
    d = json.loads(sonuc["result"])
    adlar = [s["ad"] for s in d["sonuclar"]]
    assert adlar == ["Yakin", "Uzak"]          # isimsiz yok, kopya tek
    mesafeler = [s["mesafe_m"] for s in d["sonuclar"]]
    assert mesafeler == sorted(mesafeler)      # yakindan uzaga
    assert d["sonuc_sayisi"] == len(adlar)
    for s in d["sonuclar"]:
        assert s["baglanti"].startswith("https://www.google.com/maps/")
    assert d["yaricap_m"] == 1000              # bos -> varsayilan


def test_yakin_ara_ag_hatlari_seffaf(monkeypatch):
    monkeypatch.setattr(harita, "_merkezi_coz", lambda metin: (
        {"enlem": 40.98, "boylam": 29.02, "gosterim_adi": "Moda",
         "kaynak": "girilen koordinat"}, None))

    def hatali(sorgu):
        return None, "overpass", "HTTP 429 Too Many Requests"

    monkeypatch.setattr(harita, "_overpass_json_al", hatali)
    sonuc = harita.yakin_ara("40.98,29.02", "eczane")
    assert "error" in sonuc
    assert "HTTP 429" in sonuc["error"]


def test_yakin_ara_bos_sonuc_hatadir(monkeypatch):
    monkeypatch.setattr(harita, "_merkezi_coz", lambda metin: (
        {"enlem": 40.98, "boylam": 29.02, "gosterim_adi": "Moda",
         "kaynak": "girilen koordinat"}, None))
    monkeypatch.setattr(harita, "_overpass_json_al",
                        lambda sorgu: (_overpass_veri([]), "hat", None))
    sonuc = harita.yakin_ara("40.98,29.02", "eczane")
    assert "error" in sonuc
    assert "Sonuc bulunamadi" in sonuc["error"]


def test_yakin_ara_onbellek_ziyaretsiz_ikinci_tur(monkeypatch):
    monkeypatch.setattr(harita, "_merkezi_coz", lambda metin: (
        {"enlem": 40.98, "boylam": 29.02, "gosterim_adi": "Moda",
         "kaynak": "girilen koordinat"}, None))
    cagri = {"adet": 0}

    def sahte(sorgu):
        cagri["adet"] += 1
        return (_overpass_veri([
            _overpass_oge(1, 40.9801, 29.0201, "A", "amenity", "pharmacy")
        ]), "hat", None)

    monkeypatch.setattr(harita, "_overpass_json_al", sahte)
    ilk = harita.yakin_ara("40.98,29.02", "eczane")
    ikinci = harita.yakin_ara("40.98,29.02", "eczane")
    assert cagri["adet"] == 1                      # ikinci tur ag'a gitmez
    d2 = json.loads(ikinci["result"])
    assert [h["durum"] for h in d2["denenen_hatlar"]] == ["onbellek"]
    assert json.loads(ilk["result"])["sonuclar"] == d2["sonuclar"]


def test_yakin_ara_sorgu_metni_kurala_uygun(monkeypatch):
    """QL sorgusu tabir listesinden kurar; out adedi 15x3."""
    yakalanan = {}

    def sahte(sorgu):
        yakalanan["sorgu"] = sorgu
        return (_overpass_veri([]), "hat", None)

    monkeypatch.setattr(harita, "_merkezi_coz", lambda metin: (
        {"enlem": 41.0, "boylam": 29.0, "gosterim_adi": "M",
         "kaynak": "girilen koordinat"}, None))
    monkeypatch.setattr(harita, "_overpass_json_al", sahte)
    assert "error" in harita.yakin_ara("41.0,29.0", "market")
    metin = yakalanan["sorgu"]
    assert metin.startswith("[out:json][timeout:25];")
    assert "nwr[shop=supermarket](around:1000,41.0,29.0);" in metin
    assert "nwr[shop=convenience](around:1000,41.0,29.0);" in metin
    assert "out center 45;" in metin


# ── mesafe_sure: giris denetimi ───────────────────────────────────

def test_mesafe_sure_bos_girisler_hata():
    assert "error" in harita.mesafe_sure("", "Taksim")
    assert "error" in harita.mesafe_sure("Kadikoy", "")
    assert "Desteklenenler" in harita.mesafe_sure(
        "Kadikoy", "Taksim", "helikopter")["error"]


# ── mesafe_sure: ag akisi (mocklu) ───────────────────────────────

def _mesafe_mocklu(monkeypatch, yanitlar):
    """yanitlar: hat sirasina gore [(url_parca, (veri, hata)), ...]."""
    sirasi = {"adet": 0}

    def sahte_json_al(url):
        i = sirasi["adet"]
        sirasi["adet"] += 1
        url_parca, (veri, hata) = yanitlar[i]
        assert url_parca in url, (url_parca, url)
        return veri, hata

    def sahte_coz(metin):
        if metin == "40.98,29.02":
            return ({"enlem": 40.98, "boylam": 29.02,
                     "gosterim_adi": "Moda",
                     "kaynak": "girilen koordinat"}, None)
        return ({"enlem": 41.03, "boylam": 28.97,
                 "gosterim_adi": "Taksim",
                 "kaynak": "girilen koordinat"}, None)

    monkeypatch.setattr(harita, "_json_al", sahte_json_al)
    monkeypatch.setattr(harita, "_merkezi_coz", sahte_coz)
    return sirasi


def test_mesafe_sure_birincil_hattan_okur(monkeypatch):
    sirasi = _mesafe_mocklu(monkeypatch, [(
        "router.project-osrm.org", (_osrm_ok(15_700, 1_190.0), None))])
    sonuc = harita.mesafe_sure("40.98,29.02", "41.03,28.97", "araba")
    assert "result" in sonuc
    d = json.loads(sonuc["result"])
    assert d["mesafe_km"] == 15.7
    assert d["sure_dk"] == 19.8
    assert d["hat"] == "router.project-osrm.org"
    assert [h["durum"] for h in d["denenen_hatlar"]] == ["ok"]
    assert d["seyahat"] == "araba"
    assert d["baglanti"].startswith("https://www.google.com/maps/dir/")
    assert sirasi["adet"] == 1


def test_mesafe_sure_yedek_hatta_duser(monkeypatch):
    sirasi = _mesafe_mocklu(monkeypatch, [
        ("router.project-osrm.org", (None, "HTTP 503 Service Unavailable")),
        ("routing.openstreetmap.de", (_osrm_ok(16_000, 1_300.0), None)),
    ])
    sonuc = harita.mesafe_sure("40.98,29.02", "41.03,28.97", "araba")
    assert "result" in sonuc
    d = json.loads(sonuc["result"])
    assert d["hat"] == "routing.openstreetmap.de"
    durumlar = [h["durum"] for h in d["denenen_hatlar"]]
    assert durumlar == ["hata", "ok"]
    assert "HTTP 503" in d["denenen_hatlar"][0]["hata"]


def test_mesafe_sure_tum_hatlar_yanit_vermezse_hata(monkeypatch):
    sirasi = _mesafe_mocklu(monkeypatch, [
        ("routing.openstreetmap.de/routed-foot", (None, "zaman asimi")),
    ])
    sonuc = harita.mesafe_sure("40.98,29.02", "41.03,28.97", "piyade")
    assert "error" in sonuc


def test_mesafe_sure_osrm_kodu_ok_degilse_hata(monkeypatch):
    sirasi = _mesafe_mocklu(monkeypatch, [
        ("routing.openstreetmap.de/routed-bike",
         ({"code": "NoRoute", "routes": []}, None)),
    ])
    sonuc = harita.mesafe_sure("40.98,29.02", "41.03,28.97", "bisiklet")
    assert "error" in sonuc
    assert "code=NoRoute" in sonuc["error"]


def test_mesafe_sure_osrm_sonucu_sayilari_dogrula(monkeypatch):
    """distance/duration eksik gorunmez alani hata donemelidir."""
    sirasi = _mesafe_mocklu(monkeypatch, [
        ("router.project-osrm.org", (_osrm_ok(None, None), None)),
    ])
    sonuc = harita.mesafe_sure("40.98,29.02", "41.03,28.97", "araba")
    assert "error" in sonuc
