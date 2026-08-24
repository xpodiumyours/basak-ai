"""tests/test_orkestra.py — ORKESTRA-0 iskelet testleri.

Tasarim: defter/orkestra-0-tasarim.md
Kabul olcutleri: basit soru izinde tam dizi; atlanan durumlar SEBEPiyle;
arac sorusunda EXPERIMENT kosar ve MEASURE kanitli doner; iz deterministik.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from brain.orkestra import Durum, Orkestra


def bilesenler(**fazlalar):
    b = {
        "observe": lambda s: (s.strip(), None),
        "model_baglami": lambda: "NOTLAR",
        "anilar": lambda s: [],
        "gecmis_pencere": lambda g: g,
        "siniflandir": lambda t: "genel",
        "dinamik_araclar": lambda t, tools: tools,
        "aday_uret": lambda mesajlar, araclar: (
            {"content": "tek aday cevap"}, "groq"),
        "deney_kos": lambda tool_calls: None,
        "olcu_kapisi": lambda metin, o: (metin, []),
        "ham_olcum": lambda o: [],
        "ogren": lambda s, c, onem=1: None,
    }
    b.update(fazlalar)
    return b


def durumlar(rapor):
    return [(i["durum"], i["atlandi"]) for i in rapor["iz"]]


class TestIzDizilimi:
    def test_basit_soru_tam_dizi_ve_atlama_sebepleri(self):
        rapor = Orkestra(bilesenler()).kos("merhaba nasilsin?")
        d = durumlar(rapor)
        beklenen = [("OBSERVE", False), ("MODEL", False),
                    ("QUESTION", False), ("HYPOTHESIZE", False),
                    ("DIVERSIFY", True), ("CRITICIZE", True),
                    ("EXPERIMENT", True), ("MEASURE", False),
                    ("SELECT", False), ("LEARN", False)]
        assert d == beklenen

    def test_atlama_sebepleri_yazili(self):
        rapor = Orkestra(bilesenler()).kos("selam")
        sebep_durum = {i["durum"]: i["sebep"] for i in rapor["iz"]}
        assert "FAY-1" in sebep_durum["DIVERSIFY"]
        assert "olcu kapisi" in sebep_durum["CRITICIZE"]
        assert "arac cagrisi yok" in sebep_durum["EXPERIMENT"]


class TestDeneyYolu:
    def test_arac_cagrisinda_experiment_kosar(self):
        deney_girdileri = []

        def deney_kos(tool_calls):
            deney_girdileri.append(tool_calls)
            return ("olcum sonucu cevap",
                    [("git_durum", "Dal: main")])

        def aday(mesajlar, araclar):
            return {"content": "", "tool_calls": [
                {"id": "1", "type": "function",
                 "function": {"name": "git_durum",
                              "arguments": "{\"proje\":\"vixrex\"}"}}]}, "gq"

        b = bilesenler(
            siniflandir=lambda t: "kod",
            dinamik_araclar=lambda t, tools: tools,
            aday_uret=aday,
            deney_kos=deney_kos)
        rapor = Orkestra(b).kos("VixRex'te durum ne?",
                                tools=[{"x": 1}])
        durumlar_dict = {d: a for d, a in durumlar(rapor)}
        assert durumlar_dict["EXPERIMENT"] is False   # koştu
        assert deney_girdileri and "git_durum" in \
            deney_girdileri[0][0]["function"]["name"]

    def test_kapi_elince_ham_olcum_devreye_girer(self):
        def kapi(metin, o):
            return "Bunu ölçemedim.", ["elenmis satir"]
        ham = lambda o: ['badge::Ö::git_durum "Dal: main"']
        def deney_kos(tc):
            # arac kostu ama model cumlesi yine kapidan gecemedi
            return ("Bunu ölçemedim.", [("git_durum", "Dal: main")])
        def aday(mesajlar, araclar):
            return {"content": "", "tool_calls": [
                {"id": "1", "type": "function",
                 "function": {"name": "git_durum", "arguments": "{}"}}]}, "gq"
        b = bilesenler(olcu_kapisi=kapi, ham_olcum=ham,
                       deney_kos=deney_kos, aday_uret=aday)
        rapor = Orkestra(b).kos("durum ne?", tools=[
            {"function": {"name": "git_durum"}}])
        assert rapor["cevap"].startswith('badge::Ö::git_durum')
        sec_izleri = [i for i in rapor["iz"] if i["durum"] == "SELECT"]
        assert len(sec_izleri) == 1


class TestOgrenVeGuvenlik:
    def test_learn_cevapla_birkez_calisir(self):
        cagrilan = []
        b = bilesenler(ogren=lambda s, c, onem=1: cagrilan.append((s, c)))
        Orkestra(b).kos("merhaba")
        assert len(cagrilan) == 1

    def test_bos_soru_hata_ile_doner(self):
        rapor = Orkestra(bilesenler()).kos("   ")
        assert rapor.get("hata") == "Bos mesaj"
        assert durumlar(rapor) == [("OBSERVE", False)]

    def test_aday_uret_hatasi_rapora_duser(self):
        def patlak(m, a):
            raise RuntimeError("saglayici yok")
        b = bilesenler(aday_uret=patlak)
        rapor = Orkestra(b).kos("merhaba")
        assert "saglayici yok" in rapor["hata"]

    def test_eksik_bilesen_reddedilir(self):
        with pytest.raises(ValueError):
            Orkestra({"observe": lambda s: s})
