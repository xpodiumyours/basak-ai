"""tests/test_harita_z8_mesafe_sure.py — FAZ 8: mesafe_sure (OSRM).

Kabul olcusu: ucretsiz kombin — OSRM demo + FOSSGIS yedegi, anahtar yok.
- gecersiz girdi hata doner; sayi/metin UYDURULMAZ
- 'enlem,boylam' merkez dogrudan okunur; OSRM nokta sirasi boylam,enlem
- ilk hat code!=Ok donerse yedek hat (FOSSGIS) denenir
- tum hatlar duserse acik hata; sayi UYDURULMAZ
- baglanti Google Maps URL semasindan uretilir (anahtar yok, ag yok)
- dordun dortu de dolu: sema + dispatcher dali + yetenek alani + durum

Butun testler cevrimdisi: ag cagrisi yapilmaz, sahte OSRM yaniti
enjekte edilir (tools.harita._json_al monkeypatch).
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools import calistir
from tools.definitions import TOOLS
from tools.harita import mesafe_sure
from chat.tools import DURUM_METNI, _harita_olayi
from chat.agent_protocol import YETENEK_ALANLARI
from tools.capabilities import validate_registry

MERKEZ_ENLEM, MERKEZ_BOYLAM = 41.0111, 29.0254
BITIS_ENLEM, BITIS_BOYLAM = 39.9208, 32.8541

OSRM_OK_GOVDE = {
    "code": "Ok",
    "routes": [{"distance": 15700.0, "duration": 1188.0}],
}


class SahteOSRM:
    """tools.harita._json_al yerine gecen sahte OSRM hatti.

    kodlar: onceden dondurulecek code!=Ok yanitlari (fallback provasi).
    govde: None ise hat hata dondurur ("HTTP 500").
    """

    def __init__(self, govde=OSRM_OK_GOVDE, kodlar=None):
        self.govde = govde
        self.kodlar = list(kodlar or [])
        self.adresler = []

    def __call__(self, url, sure=None):
        self.adresler.append(url)
        if self.kodlar:
            kod = self.kodlar.pop(0)
            return {"code": kod}, None
        if self.govde is None:
            return None, "HTTP 500 yuk dengeleme"
        return self.govde, None


def _koordinat(en, boy):
    return "%s, %s" % (en, boy)


def test_gecersiz_seyahat_hata():
    sonuc = mesafe_sure(_koordinat(MERKEZ_ENLEM, MERKEZ_BOYLAM),
                        _koordinat(BITIS_ENLEM, BITIS_BOYLAM),
                        seyahat="ucak")
    assert "error" in sonuc
    assert "Desteklenenler" in sonuc["error"]


def test_bos_ve_uzun_girdi_hata():
    assert "error" in mesafe_sure("", "Ankara")
    assert "error" in mesafe_sure("Ankara", "")
    assert "error" in mesafe_sure("x" * 500, "Ankara")
    assert "error" in mesafe_sure("Ankara", "x" * 500)


def test_yol_sirasi_ve_olcum(monkeypatch):
    hat = SahteOSRM()
    monkeypatch.setattr("tools.harita._json_al", hat)
    sonuc = mesafe_sure(_koordinat(MERKEZ_ENLEM, MERKEZ_BOYLAM),
                        _koordinat(BITIS_ENLEM, BITIS_BOYLAM))
    assert "error" not in sonuc
    veri = json.loads(sonuc["result"])
    # OSRM nokta sirasi boylam,enlem — KARISTIRMA testinin kendisi.
    yol_sorgu = hat.adresler[0].split("/route/v1/driving/")[1]
    beklenen = "%s,%s;%s,%s" % (MERKEZ_BOYLAM, MERKEZ_ENLEM,
                                BITIS_BOYLAM, BITIS_ENLEM)
    assert yol_sorgu.startswith(beklenen)
    assert veri["mesafe_km"] == 15.7
    assert veri["sure_dk"] == 19.8
    assert veri["kaynak"] == "osrm"
    assert veri["atif"]
    # Baglanti Google Maps yol tarifi semasindan uretilir (ag YOK).
    assert "maps/dir" in veri["baglanti"]


def test_yedek_hat_fallback(monkeypatch):
    # project-osrm.org "NoRoute" doner; FOSSGIS yedegi devralir.
    hat = SahteOSRM(kodlar=["NoRoute"])
    monkeypatch.setattr("tools.harita._json_al", hat)
    sonuc = mesafe_sure(_koordinat(MERKEZ_ENLEM, MERKEZ_BOYLAM),
                        _koordinat(BITIS_ENLEM, BITIS_BOYLAM))
    assert "error" not in sonuc
    veri = json.loads(sonuc["result"])
    assert veri["hat"] == "routing.openstreetmap.de"
    assert len(hat.adresler) == 2


def test_tum_hatlar_duser_uydurma_yok(monkeypatch):
    hat = SahteOSRM(govde=None)
    monkeypatch.setattr("tools.harita._json_al", hat)
    sonuc = mesafe_sure(_koordinat(MERKEZ_ENLEM, MERKEZ_BOYLAM),
                        _koordinat(BITIS_ENLEM, BITIS_BOYLAM))
    assert "error" in sonuc
    assert "denenen hatlar" in sonuc["error"]


def test_merkez_cozulemezse_ag_dokunulmaz(monkeypatch):
    hat = SahteOSRM()
    monkeypatch.setattr("tools.harita._json_al", hat)
    monkeypatch.setattr("tools.harita.konum_coz",
                        lambda *a, **k: {"error": "bulunamadi"})
    sonuc = mesafe_sure("olmayan yer", "Ankara")
    assert "error" in sonuc
    assert hat.adresler == []  # ag cagrisi hic yapilmaz


def _uygulama_calistir(monkeypatch):
    hat = SahteOSRM()
    monkeypatch.setattr("tools.harita._json_al", hat)
    return calistir("mesafe_sure",
                    {"nereden": _koordinat(MERKEZ_ENLEM, MERKEZ_BOYLAM),
                     "nereye": _koordinat(BITIS_ENLEM, BITIS_BOYLAM)})


def test_dordun_dordu_dolu(monkeypatch):
    # 1 sema
    adlar = [(t["function"]["name"]) for t in TOOLS]
    assert adlar.count("mesafe_sure") == 1
    # 2 dispatcher
    sonuc = _uygulama_calistir(monkeypatch)
    assert "error" not in sonuc
    # 3 yetenek alani
    assert "mesafe_sure" in YETENEK_ALANLARI["harita"]
    # 4 ekran durumu
    assert DURUM_METNI["mesafe_sure"]
    # kayit tutarliligi: her semanin bir alani var, kopuk/eksik yok
    kayit = validate_registry()
    assert kayit["ok"], kayit
    assert kayit["tool_count"] == 78


def test_harita_olayi_baglanti_karti(monkeypatch):
    sonuc = _uygulama_calistir(monkeypatch)
    olay = _harita_olayi("mesafe_sure", sonuc)
    assert olay is not None
    assert olay.get("baglanti")
