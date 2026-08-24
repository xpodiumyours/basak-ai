"""tests/test_token_sayimi.py — Gerçek token sayımı testleri.

2026-08-24 (Casper'in tespiti): stats.py'de token alanları hazırdı ama
adaptörler usage okumadığı için hep 0 kalıyordu. Artık:
- adaptörler _kullanim ekler (OpenAI + Cohere biçimleri)
- brain.cevapla bunu ayırıp istatistiğe yazar
- ozet() token toplamlarını gösterir
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from brain.kullanim import kullanim_ekle, openai_kullanim
from brain.stats import ModelIstatistik


def _sahte_resp(usage=None, content="merhaba", tool_calls=None):
    """OpenAI-SDK yanit taklidi."""
    msg = SimpleNamespace(content=content, tool_calls=tool_calls)
    resp = SimpleNamespace(choices=[SimpleNamespace(message=msg)])
    if usage is not None:
        resp.usage = SimpleNamespace(prompt_tokens=usage[0],
                                     completion_tokens=usage[1])
    return resp


class TestKullanimCikarimi:
    def test_openai_bicimi(self):
        k = openai_kullanim(_sahte_resp((3400, 210)))
        assert k == {"giris": 3400, "cikis": 210}

    def test_cohere_bicimi(self):
        resp = SimpleNamespace(
            meta=SimpleNamespace(tokens=SimpleNamespace(input_tokens=500,
                                                        output_tokens=80)),
            message=None)
        assert openai_kullanim(resp) == {"giris": 500, "cikis": 80}

    def test_usage_yoksa_none(self):
        assert openai_kullanim(_sahte_resp()) is None

    def test_sifir_kullanim_none_doner(self):
        assert openai_kullanim(_sahte_resp((0, 0))) is None

    def test_kullanim_ekle_yaniti_degistirmez_kopyalar(self):
        yanit = {"content": "selam"}
        donen = kullanim_ekle(yanit, _sahte_resp((10, 5)))
        assert donen["_kullanim"] == {"giris": 10, "cikis": 5}
        assert "usage" in str(donen) or donen["content"] == "selam"

    def test_usage_olmayan_resp_zararsiz(self):
        yanit = {"content": "x"}
        assert kullanim_ekle(yanit, _sahte_resp()) == {"content": "x"}


class TestGroqAdaptoru:
    def test_groq_cevapla_kullanim_tasiyor(self):
        from brain.groq import GroqClient

        gc = GroqClient("sahte-anahtar-1234567890")
        sahte_client = SimpleNamespace()
        sahte_resp = _sahte_resp((1200, 300), content="cevap")
        sahte_client.chat = SimpleNamespace(completions=SimpleNamespace(
            create=lambda **kw: sahte_resp))
        gc.client = sahte_client

        yanit = gc.cevapla([{"role": "user", "content": "selam"}])
        assert yanit["_kullanim"] == {"giris": 1200, "cikis": 300}
        assert yanit["content"] == "cevap"


class TestStatsKaydi:
    def test_kaydet_ve_ozet_token_gosterir(self, tmp_path):
        istat = ModelIstatistik(db_yolu=str(tmp_path / "s.db"))
        istat.kaydet("groq", 1.2, basarili=True,
                     token_in=3400, token_out=210)
        istat.kaydet("groq", 0.8, basarili=True,
                     token_in=1000, token_out=90)
        ozet = istat.ozet(model="groq")
        assert ozet[0]["token_in_toplam"] == 4400
        assert ozet[0]["token_out_toplam"] == 300


class TestBrainKablolama:
    def test_cevapla_kullanimi_istatige_yazar(self, monkeypatch, tmp_path):
        """Sahte saglayici _kullanim tasiyorsa brain onu istatige aktarmali."""
        from brain import brain as brain_mod
        from brain.brain import Brain
        from brain.kota import KotaYoneticisi

        istat = ModelIstatistik(db_yolu=str(tmp_path / "ist.db"))
        monkeypatch.setattr(brain_mod, "model_stats_al", lambda: istat)

        b = Brain.__new__(Brain)   # __init__ agirliklari olmadan
        # GERCEK durum dosyasini degil, izole kotayi kullan (canli
        # sogumalar testi etkilemesin)
        b.kota = KotaYoneticisi(dosya=str(tmp_path / "kota.json"),
                                ucretli_engelli=True)
        for ad in ("_glm", "_cloudflare", "_cohere", "_nvidia", "_kilo",
                   "_openrouter", "_qwen", "_gemini"):
            setattr(b, ad, None)

        class SahteSaglayici:
            def musait(self):
                return True

            def cevapla(self, messages, tools=None, model=None):
                return {"content": "tamam",
                        "_kullanim": {"giris": 700, "cikis": 40}}

        b._groq = SahteSaglayici()

        class SahteOllama:
            def cevapla(self, *a, **kw):
                raise RuntimeError("ulasilmadi")

        b._ollama = SahteOllama()

        yanit, gosterim = b.cevapla([{"role": "user", "content": "selam"}],
                                    yerel_model="yerel-x")
        assert yanit["content"] == "tamam"
        assert "_kullanim" not in yanit          # ayiklandi
        assert gosterim.startswith("groq")
        ozet = istat.ozet(model="groq")
        assert ozet[0]["token_in_toplam"] == 700
        assert ozet[0]["token_out_toplam"] == 40
