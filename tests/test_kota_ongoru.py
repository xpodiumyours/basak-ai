# -*- coding: utf-8 -*-
"""tests/test_kota_ongoru.py — kota/hiz ongorulu deneme sirasi.

Casper talebi (2026-10-10): kota sikisikliginda zincir olur-olmaz
saglayiciyi deneyip saniyeler yiyor; ilk icerik (TTFT) 50+ sn'ye cikiyor.
secici.sec imzasi kilitli oldugu icin siralama beyin katmaninda olur
(secici docstring'i de kota filtresini beyne verir). Kural yalniz olcum
verisine dayanir: kota durumu, token butce dolulugu, olculen basari+hiz
skoru. Ad/kisi/kelime kurali YOK.
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import brain as brain_mod
from brain.brain import Brain, _kota_ongorulu_sira
from brain.stats import ModelIstatistik


class SahteIstat:
    def __init__(self, sira=(), tokenler=None):
        self._sira = list(sira)
        self._tok = tokenler or {}

    def siralama(self, son_saat=24):
        return [{"model": a, "skor": 100 - i * 10}
                for i, a in enumerate(self._sira)]

    def token_bugun(self, ad):
        return self._tok.get(ad, (0, 0))


def _duz_zemin(monkeypatch):
    monkeypatch.setattr(brain_mod, "_yerel_kota_doldu",
                        lambda ad, istat: "")
    monkeypatch.setattr(brain_mod, "_cooldown_kaldi", lambda ad: 0)
    monkeypatch.setattr(brain_mod.registry, "kart",
                        lambda ad: {"gunluk_token": None})
    return SahteIstat()


class TestKotaOngoruluSira:
    def test_kota_dolu_sona(self, monkeypatch):
        istat = _duz_zemin(monkeypatch)
        monkeypatch.setattr(brain_mod, "_yerel_kota_doldu",
                            lambda ad, istat: ("gunluk istek kotasi"
                                               if ad == "groq" else ""))
        sirali, _ = _kota_ongorulu_sira(["groq", "gemini"], istat)
        assert sirali == ["gemini", "groq"]

    def test_cooldown_sona(self, monkeypatch):
        istat = _duz_zemin(monkeypatch)
        monkeypatch.setattr(brain_mod, "_cooldown_kaldi",
                            lambda ad: 100 if ad == "groq" else 0)
        sirali, _ = _kota_ongorulu_sira(["groq", "gemini"], istat)
        assert sirali == ["gemini", "groq"]

    def test_butce_dolulugu(self, monkeypatch):
        istat = SahteIstat(tokenler={"groq": (90, 0), "gemini": (10, 0)})
        monkeypatch.setattr(brain_mod, "_yerel_kota_doldu",
                            lambda ad, istat: "")
        monkeypatch.setattr(brain_mod, "_cooldown_kaldi", lambda ad: 0)
        monkeypatch.setattr(brain_mod.registry, "kart",
                            lambda ad: {"gunluk_token": 100})
        sirali, _ = _kota_ongorulu_sira(["groq", "gemini"], istat)
        assert sirali == ["gemini", "groq"]

    def test_olculen_skor_once(self, monkeypatch):
        istat = SahteIstat(sira=["gemini", "groq"])
        _duz_zemin(monkeypatch)
        sirali, _ = _kota_ongorulu_sira(["groq", "gemini"], istat)
        assert sirali == ["gemini", "groq"]

    def test_esitlikte_girdi_sirasi_korunur(self, monkeypatch):
        istat = _duz_zemin(monkeypatch)
        sirali, _ = _kota_ongorulu_sira(["gemini", "groq"], istat)
        assert sirali == ["gemini", "groq"]

    def test_veri_yoksa_ayni_sira(self, monkeypatch):
        class Bozuk:
            def siralama(self, son_saat=24):
                raise RuntimeError("istatistik yok")

            def token_bugun(self, ad):
                raise RuntimeError("istatistik yok")

        monkeypatch.setattr(brain_mod, "_yerel_kota_doldu",
                            lambda ad, istat: "")
        monkeypatch.setattr(brain_mod, "_cooldown_kaldi", lambda ad: 0)
        sirali, _ = _kota_ongorulu_sira(["groq", "gemini"], Bozuk())
        assert sirali == ["groq", "gemini"]


class TestSiralamaSaglamlik:
    def test_tum_sureler_sifirsa_cokmez(self, tmp_path):
        """Gercek veri sekli (2026-10-10 yerel DB): 24 saatte tum kayitlar
        0ms — min() bos kumede patliyordu. Yalniz basari siralar."""
        istat = ModelIstatistik(db_yolu=str(tmp_path / "s.db"))
        istat.kaydet("groq", 0.0, basarili=False, hata="kota")
        istat.kaydet("groq", 0.0, basarili=True)
        istat.kaydet("gemini", 0.0, basarili=False, hata="429")
        sira = istat.siralama(son_saat=24)
        assert [r["model"] for r in sira] == ["groq", "gemini"]
        assert all(r["hiz_skoru"] == 0 for r in sira)

    def test_bos_veride_bos_doner(self, tmp_path):
        istat = ModelIstatistik(db_yolu=str(tmp_path / "s.db"))
        assert istat.siralama(son_saat=24) == []


def _tek_cagri_sdk(cevap, kayit, ad):
    def _cagri(messages, **kw):
        kayit.append(ad)
        return {"content": cevap}
    return SimpleNamespace(cevapla=_cagri, model="m")


class TestBaglanti:
    def test_cevapla_siralamayi_kullanir(self, monkeypatch, tmp_path):
        """Siralayici tersine cevirirse zincir de ters dener (baglanti)."""
        brain_mod._COOLDOWN.clear()
        monkeypatch.setattr(brain_mod, "STATE_DIR", str(tmp_path))
        monkeypatch.setattr(brain_mod, "_yerel_kota_doldu",
                            lambda ad, istat: "")
        deneme = []
        zincir = [("groq", _tek_cagri_sdk("groq-cevap", deneme, "groq")),
                  ("gemini", _tek_cagri_sdk("gemini-cevap", deneme,
                                            "gemini"))]
        b = Brain.__new__(Brain)
        monkeypatch.setattr(b, "_bulut_zinciri", lambda tools=False: zincir)

        gercek = brain_mod._kota_ongorulu_sira

        def terse_cevir(sirali, istat):
            s, g = gercek(sirali, istat)
            return list(reversed(s)), g

        monkeypatch.setattr(brain_mod, "_kota_ongorulu_sira", terse_cevir)
        yanit, kaynak = b.cevapla([{"role": "user", "content": "selam"}])

        assert deneme == ["gemini"], deneme
        assert kaynak == "gemini"
        assert yanit["content"] == "gemini-cevap"
