"""tests/test_web_ek_staging.py — web'e eklenen fotoğraf staging'e yazar.

Sözleşme: resim ek `katalog.fatura_kaydet_b64` ile data/gelen altına iner,
model `Dosya verisi:` satırında fatura_id + staging yolunu görür ve aynı
akış içinde `fatura_oku` o dosyayı bulur. Katalog hata dönerse (pdf/bozuk)
eski geçici dosya yoluna düşülür; temizlik her iki durumda da akış sonunda
yapılır. Ağ yok: chat.flow.mesaj_isle sahtelenir.
"""

import json
import os
import sys
import tempfile
from unittest import mock

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as app_modulu  # noqa: E402
from tools import katalog  # noqa: E402

PNG = ("data:image/png;base64,"
       "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
       "z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


def _istemci(monkeypatch, tmp_path):
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setenv("BASAK_OTURUM_ANAHTARI", "test-staging-anahtari-1")
    monkeypatch.setattr(app_modulu, "_cekirdek", lambda: (object(), []))
    monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path))
    return TestClient(app_modulu.app)


def _mesaj_isle(yakalanan):
    def _sahte(metin, beyin, sistem, js, tools=None, **kwargs):
        yakalanan["metin"] = metin
        if "Dosya verisi: " in metin:
            bilgi = json.loads(metin.split("Dosya verisi: ", 1)[1])
            yakalanan["bilgi"] = bilgi
            yakalanan["akista_var"] = os.path.isfile(bilgi["path"])
            if bilgi.get("fatura_id"):
                yakalanan["staging_yolu"] = katalog._fatura_yolu(
                    bilgi["fatura_id"])
        js('BasakUI.bitir("tamam", "test")')
    return _sahte


def _ek(ad="fatura.png"):
    return {"tur": "image", "ad": ad, "data_url": PNG}


def _gonder(istemci, yakalanan, ek, akis=False):
    baslik = {"accept": "application/x-ndjson"} if akis else {}
    with mock.patch("chat.flow.mesaj_isle", _mesaj_isle(yakalanan)):
        return istemci.post("/api/sohbet",
                            json={"metin": "faturayi oku", "ek": ek},
                            headers=baslik)


def test_ek_staginge_yazilir_ve_metinde_fatura_id_var(monkeypatch, tmp_path):
    yakalanan = {}
    with _istemci(monkeypatch, tmp_path) as istemci:
        cevap = _gonder(istemci, yakalanan, _ek())

    assert cevap.status_code == 200, cevap.text
    bilgi = yakalanan["bilgi"]
    assert bilgi["fatura_id"].startswith("gln_")
    assert bilgi["path"] == yakalanan["staging_yolu"]
    assert bilgi["path"].startswith(os.path.realpath(str(tmp_path)))
    assert yakalanan["akista_var"] is True, "staging dosyasi akis icinde yok"
    assert '"fatura_id"' in yakalanan["metin"]
    assert bilgi["fatura_id"] in yakalanan["metin"]


def test_katalog_hatada_gecici_dosya_yoluna_duser(monkeypatch, tmp_path):
    yakalanan = {}
    with _istemci(monkeypatch, tmp_path) as istemci:
        cevap = _gonder(istemci, yakalanan, _ek(ad="fatura.pdf"))

    assert cevap.status_code == 200, cevap.text
    bilgi = yakalanan["bilgi"]
    assert "fatura_id" not in bilgi
    assert os.path.dirname(bilgi["path"]) == tempfile.gettempdir()
    assert os.path.basename(bilgi["path"]).startswith("basak-")
    assert yakalanan["akista_var"] is True
    assert not os.path.exists(bilgi["path"]), (
        "gecici dosya da akis sonunda silinmeli")


def test_akis_sonunda_ek_dosyasi_silinir(monkeypatch, tmp_path):
    for akis in (False, True):
        yakalanan = {}
        with _istemci(monkeypatch, tmp_path) as istemci:
            cevap = _gonder(istemci, yakalanan, _ek(), akis=akis)

        assert cevap.status_code == 200, cevap.text
        yol = yakalanan["bilgi"]["path"]
        assert yakalanan["akista_var"] is True
        assert not os.path.exists(yol), "akis sonunda dosya kalmamali"
