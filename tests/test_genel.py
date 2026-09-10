"""tests/test_genel.py — Ozel (ucretli) saglayici yuvasi testleri.

2026-09-10 (Casper karari): parali anahtar takilinca HICBIR SEY
degismeyecek. Kurallar:
- Uc parca (adres+bilet+model) yoksa adaptor None doner (bedava duzen ayni).
- Varsa zincirin EN SONUNA girer (secici bilinmeyeni sona alir).
- Sozlesme diger istemcilerle birebir aynidir (cevapla imzasi).
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import registry, secici
from brain.adapters.genel_adapter import adapter
from brain.genel import GenelClient


class TestGenelAdapter:
    def test_eksik_parcada_none(self):
        assert adapter.create({}) is None
        assert adapter.create({"genel_api_key": "x"}) is None
        assert adapter.create({"genel_api_key": "x",
                               "genel_api_url": "https://ornek.test/v1"}) is None

    def test_tam_parcada_istemci(self):
        c = adapter.create({"genel_api_url": "https://ornek.test/v1",
                            "genel_api_key": "bilet",
                            "genel_model": "ornek-model"})
        assert c is not None and c.musait() is True
        assert c.model == "ornek-model"

    def test_bos_degerler_reddedilir(self):
        try:
            GenelClient("", "https://ornek.test/v1", "m")
            assert False, "bos bilet kabul edilmemeli"
        except ValueError:
            pass
        try:
            GenelClient("b", "", "m")
            assert False, "bos adres kabul edilmemeli"
        except ValueError:
            pass


class TestGenelSira:
    def test_kart_var_ucretli_isaretli(self):
        k = registry.kart("genel")
        assert k["tools"] is True
        assert registry.ucretli_mi("genel") is True

    def test_varsayilan_sirada_yok(self):
        # Bedava duzen degismez: genel, kayitta olmayan isim olarak
        # secicide otomatik SONA duser.
        assert "genel" not in registry.VARSAYILAN_SIRA

    def test_bilinmeyen_sona_duser(self):
        # kod turu (karistirmasiz) ile sira nettir: genel en sonda.
        sirali, _ = secici.sec(gorev_tipi="kod",
                               mevcutlar=["genel", "glm", "nvidia"])
        assert sirali[-1] == "genel"
        assert sirali[0] == "glm"
