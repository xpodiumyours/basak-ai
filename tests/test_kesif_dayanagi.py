"""tests/test_kesif_dayanagi.py — Kesifte gozlemsiz cevaba tek durtme.

2026-09-10 (Casper karari: kalip degil ilke): kesif sorusu
("belgelerimde ne var" gibi) arac kosturmadan cevapla gelirse
sistem TEK kez durter ("bak, sonra cevapla"); ikinci cevap ne
gelirse kabul edilir. Cumle-esleme kalibi degil, sinif-dayanakli
mekanizma: _dosya_islemi_sinyali karar verir.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chat  # once tam paket (dairesel import onlemi)
import _chat_legacy as L
from brain.orkestra import Orkestra

ARACLAR = [{"function": {"name": "list_files"}}]


class SahteBeyin:
    def __init__(self, yanitlar):
        self._yanitlar = list(yanitlar)
        self.cagrilar = []

    def yerel_modeller(self):
        return []

    def bulut_musait(self):
        return True

    def _bulut_zinciri(self):
        return []

    def cevapla(self, messages, model, tools=None):
        self.cagrilar.append({"model": model,
                              "arac_var": bool(tools)})
        icerik = self._yanitlar.pop(0)
        if isinstance(icerik, dict):
            return icerik, "sahte"
        return {"content": icerik}, "sahte"


def _kos(beyin, soru):
    bilesenler = L.orkestra_bilesenleri(beyin)
    bilesenler["ogren"] = lambda *a: None
    return Orkestra(bilesenler).kos(soru, gecmis=[], tools=ARACLAR,
                                    sistem="SYS")


class TestKesifDayanagi:
    def test_gozlemsiz_kesifte_tek_durtme(self, monkeypatch):
        monkeypatch.setattr(L, "_hafiza", False)
        beyin = SahteBeyin(["liste su", "son cevap"])
        rapor = _kos(beyin, "belgelerimde ne var")
        assert len(beyin.cagrilar) == 2
        assert rapor["cevap"] == "son cevap"

    def test_sohbette_durtme_yok(self, monkeypatch):
        monkeypatch.setattr(L, "_hafiza", False)
        beyin = SahteBeyin(["merhaba Casper"])
        rapor = _kos(beyin, "merhaba nasilsin")
        assert len(beyin.cagrilar) == 1
        assert rapor["cevap"] == "merhaba Casper"

    def test_aracli_cevapta_durtme_yok(self, monkeypatch):
        monkeypatch.setattr(L, "_hafiza", False)
        ilk = {"content": "", "tool_calls": [{
            "id": "c1", "type": "function",
            "function": {"name": "bilinmeyen_arac",
                         "arguments": "{}"}}]}
        beyin = SahteBeyin([ilk, {"content": "OZET"}])
        rapor = _kos(beyin, "belgelerimde ne var")
        assert len(beyin.cagrilar) == 2  # ilk + ozet, durtme degil
        assert rapor["cevap"] == "OZET"

    def test_yerel_yokken_model_none_akar(self, monkeypatch):
        monkeypatch.setattr(L, "_hafiza", False)
        beyin = SahteBeyin(["merhaba Casper"])
        _kos(beyin, "merhaba nasilsin")
        assert beyin.cagrilar[0]["model"] is None

    def test_dolas_cumlesi_kesif_sayilir(self):
        assert L._dosya_islemi_sinyali(
            "bilgisayarda dolas bakalim neler gorebiliyorsun")

    def test_dolas_soruda_durtme_calisir(self, monkeypatch):
        monkeypatch.setattr(L, "_hafiza", False)
        beyin = SahteBeyin(["hangi klasore bakayim?", "son cevap"])
        rapor = _kos(beyin,
                     "bilgisayarda dolas bakalim neler gorebiliyorsun")
        assert len(beyin.cagrilar) == 2
        assert rapor["cevap"] == "son cevap"
