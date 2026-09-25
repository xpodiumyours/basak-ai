"""tests/test_saglayici_hata_turu.py — saglayici hatasi resmi koddan okunur.

Eski kod hata METNINDE "limit/rate/quota" arardi. Groq'un 413 cevabi
("Request too large ... Limit 8000, Requested 9313") bu yuzden 429 sayilip
saglayici bosuna cooldown aliyor, kullaniciya "Cok fazla istek" deniyordu.
Bu testler gercek OpenAI SDK hata nesneleriyle (ag yok) davranisi olcer.
"""

import os
import sys

import httpx
import openai
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import brain as brain_mod
from brain.brain import (
    Brain, HATA_COK_BUYUK, HATA_COK_SIK, HATA_DIGER, HATA_ZAMAN_ASIMI,
    ZincirHatasi, hata_turu,
)

MESAJ = [{"role": "user", "content": "selam"}]

# Groq'un gercek 413 govdesi: metinde "Limit" ve "rate_limit_exceeded" gecer,
# ama resmi durum kodu 413'tur.
GROQ_413_METIN = (
    "Request too large for model `llama-3.3-70b-versatile` on tokens per "
    "minute (TPM): Limit 8000, Requested 9313, please reduce your message "
    "size and try again."
)


def _sdk_hatasi(kod, mesaj, govde=None, basliklar=None):
    istek = httpx.Request("POST", "https://saglayici.test/v1/chat/completions")
    cevap = httpx.Response(kod, request=istek, headers=basliklar or {})
    if kod == 429:
        return openai.RateLimitError(mesaj, response=cevap, body=govde)
    if kod == 400:
        return openai.BadRequestError(mesaj, response=cevap, body=govde)
    return openai.APIStatusError(mesaj, response=cevap, body=govde)


def _groq_413():
    return _sdk_hatasi(413, GROQ_413_METIN, govde={"error": {
        "message": GROQ_413_METIN, "type": "tokens",
        "code": "rate_limit_exceeded"}})


@pytest.fixture(autouse=True)
def temiz_durum(monkeypatch, tmp_path):
    brain_mod._COOLDOWN.clear()
    monkeypatch.setattr(brain_mod, "STATE_DIR", str(tmp_path))
    monkeypatch.setattr(brain_mod, "_yerel_kota_doldu", lambda ad, istat: "")
    yield
    brain_mod._COOLDOWN.clear()


class SahteIstemci:
    def __init__(self, hata=None):
        self.hata = hata
        self.cagrildi = 0

    def cevapla(self, messages, model=None, tools=None):
        self.cagrildi += 1
        if self.hata is not None:
            raise self.hata
        return {"content": "tamam"}


def _brain(monkeypatch, zincir):
    b = Brain.__new__(Brain)
    monkeypatch.setattr(b, "_bulut_zinciri", lambda tools=False: zincir)
    return b


class TestHataTuru:
    def test_groq_413_metninde_limit_gecse_de_cok_buyuktur(self):
        assert hata_turu(_groq_413()) == HATA_COK_BUYUK

    def test_429_cok_sik(self):
        assert hata_turu(_sdk_hatasi(429, "slow down")) == HATA_COK_SIK

    def test_400_resmi_baglam_kodu_cok_buyuk(self):
        hata = _sdk_hatasi(400, "too long", govde={"error": {
            "code": "context_length_exceeded", "message": "x"}})
        assert hata_turu(hata) == HATA_COK_BUYUK

    def test_sarilmis_hata_asil_koddan_okunur(self):
        try:
            try:
                raise _groq_413()
            except openai.APIStatusError as e:
                raise RuntimeError("Cohere API hatasi: %s" % e) from e
        except RuntimeError as sarili:
            assert hata_turu(sarili) == HATA_COK_BUYUK

    def test_kodsuz_metin_kelimeden_siniflanmaz(self):
        # Durum kodu olmayan duz metin: kelimesine bakilip 429 sayilmaz.
        assert hata_turu(RuntimeError("rate limit 429 quota")) == HATA_DIGER

    def test_zaman_asimi_resmi_turden(self):
        istek = httpx.Request("POST", "https://saglayici.test")
        assert hata_turu(openai.APITimeoutError(request=istek)) == \
            HATA_ZAMAN_ASIMI
        assert hata_turu(TimeoutError("x")) == HATA_ZAMAN_ASIMI


class TestZincir:
    def test_413_cooldown_almaz_siradaki_cevaplar(self, monkeypatch):
        groq, glm = SahteIstemci(_groq_413()), SahteIstemci()
        b = _brain(monkeypatch, [("groq", groq), ("glm", glm)])
        yanit, kaynak = b.cevapla(MESAJ, None, tercih=("groq", "glm"))
        assert kaynak == "glm" and yanit["content"] == "tamam"
        assert brain_mod._cooldown_kaldi("groq") == 0

    def test_429_cooldown_alir(self, monkeypatch):
        hata = _sdk_hatasi(429, "slow", basliklar={"retry-after": "30"})
        groq, glm = SahteIstemci(hata), SahteIstemci()
        b = _brain(monkeypatch, [("groq", groq), ("glm", glm)])
        b.cevapla(MESAJ, None, tercih=("groq", "glm"))
        assert brain_mod._cooldown_kaldi("groq") > 0

    def test_hepsi_413_ise_tur_tasiyan_hata(self, monkeypatch):
        b = _brain(monkeypatch, [("groq", SahteIstemci(_groq_413())),
                                 ("glm", SahteIstemci(_groq_413()))])
        with pytest.raises(ZincirHatasi, match="Hicbir model calismadi") as e:
            b.cevapla(MESAJ, None, tercih=("groq", "glm"))
        assert e.value.turler == {"groq": HATA_COK_BUYUK, "glm": HATA_COK_BUYUK}
        assert e.value.ortak_tur() == HATA_COK_BUYUK
        assert brain_mod._cooldown_kaldi("groq") == 0
        assert brain_mod._cooldown_kaldi("glm") == 0


class TestKullaniciMesaji:
    def test_hepsi_cok_buyuk_ise_dogru_sebep_soylenir(self):
        from chat.flow import _beyin_hata_mesaji
        hata = ZincirHatasi("Hicbir model calismadi (x)",
                            {"groq": HATA_COK_BUYUK})
        mesaj = _beyin_hata_mesaji(hata, "Beyin hatasi: ")
        assert "boyutu asti" in mesaj
        assert "Cok fazla istek" not in mesaj

    def test_cok_sik_varsa_bekle_denir(self):
        from chat.flow import _beyin_hata_mesaji
        hata = ZincirHatasi("x", {"groq": HATA_COK_BUYUK,
                                  "gemini": HATA_COK_SIK})
        assert _beyin_hata_mesaji(hata, "") == "Cok fazla istek, biraz bekle"

    def test_duz_metin_hata_kelimeden_bekle_demez(self):
        from chat.flow import _beyin_hata_mesaji
        mesaj = _beyin_hata_mesaji(RuntimeError("rate 429"), "Beyin hatasi: ")
        assert mesaj == "Beyin hatasi: rate 429"
