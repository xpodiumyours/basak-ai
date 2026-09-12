"""tests/test_erisim_engeli.py - 403/401 ayrimi testleri (P3).

403/401/paid-plan/gecersiz-anahtar dakikalarda iyilesmez: ölü saglayici
her turda yeniden denenmemeli (kota + sure yakar), 1 saat pas gecilir.
Anahtar/model degisince tablo temizlenir (iyilesme sansi korunur).

Bu testler kendi _COOLDOWN kirini temizler (global state sizintisi
diger testleri zehirlemesin diye).
"""

import pytest


@pytest.fixture(autouse=True)
def _cooldown_temizligi():
    import brain.brain as _b
    _b._COOLDOWN.clear()
    yield
    _b._COOLDOWN.clear()


class SahteIstemci:
    def __init__(self, hata=None, model="openai/gpt-oss-20b"):
        self.hata = hata
        self.model = model
        self.cagrildi = 0

    def cevapla(self, messages, model=None, tools=None):
        self.cagrildi += 1
        if self.hata:
            raise self.hata
        return {"content": "tamam"}


def _brain(monkeypatch, zincir):
    from brain.brain import Brain
    b = Brain.__new__(Brain)
    monkeypatch.setattr(b, "_bulut_zinciri", lambda: zincir)
    return b


class TestErisimTespiti:
    @pytest.mark.parametrize("mesaj", [
        "403 Forbidden",
        "401 Unauthorized",
        "Access to model denied. Please make sure you are eligible",
        "Error code: 403 - requires paid plan",
        "invalid api key provided",
        "Incorrect API key",
        "permission denied for this model",
    ])
    def test_engel_tespiti(self, mesaj):
        from brain.brain import _erisim_engeli_mi
        assert _erisim_engeli_mi(RuntimeError(mesaj)) is True

    @pytest.mark.parametrize("mesaj", [
        "429 rate limit exceeded",
        "Request timed out.",
        "Groq bağlı değil",
        "connection reset by peer",
    ])
    def test_engel_olmayanlar(self, mesaj):
        from brain.brain import _erisim_engeli_mi
        assert _erisim_engeli_mi(RuntimeError(mesaj)) is False


class TestErisimZinciri:
    def test_403_veren_atlanir_siradaki_devralir(self, monkeypatch):
        olu = SahteIstemci(hata=RuntimeError("403 Forbidden"))
        saglam = SahteIstemci()
        b = _brain(monkeypatch, [("cloudflare", olu), ("glm", saglam)])
        yanit, kaynak = b.cevapla(
            [{"role": "user", "content": "selam"}], "qwen2.5:7b",
            tercih=["cloudflare", "glm"])
        assert yanit["content"] == "tamam"
        assert kaynak.startswith("glm")
        assert olu.cagrildi == 1 and saglam.cagrildi == 1

    def test_403_uzun_cooldown_alir(self, monkeypatch):
        import brain.brain as _b
        olu = SahteIstemci(hata=RuntimeError("403 Forbidden"))
        b = _brain(monkeypatch, [("cloudflare", olu)])
        try:
            b.cevapla([{"role": "user", "content": "selam"}], None)
        except RuntimeError:
            pass  # yerel de yoksa zincir duser; sorun degil
        assert _b._cooldown_kaldi("cloudflare") > 120  # 2 dk'dan uzun

    def test_olu_saglayici_sonraki_turda_denenmez(self, monkeypatch):
        olu = SahteIstemci(hata=RuntimeError("403 Forbidden"))
        saglam = SahteIstemci()
        b = _brain(monkeypatch, [("cloudflare", olu), ("glm", saglam)])
        b.cevapla([{"role": "user", "content": "bir"}], "qwen2.5:7b",
                  tercih=["cloudflare", "glm"])
        b.cevapla([{"role": "user", "content": "iki"}], "qwen2.5:7b",
                  tercih=["cloudflare", "glm"])
        assert olu.cagrildi == 1  # ikinci turda denenmedi
        assert saglam.cagrildi == 2

    def test_anahtar_degisimi_tabloyu_temizler(self, monkeypatch):
        import brain.brain as _b
        _b._cooldown_ekle("groq", sure=3600)
        assert _b._cooldown_kaldi("groq") > 0
        b = _b.Brain.__new__(_b.Brain)
        monkeypatch.setattr(_b, "_ayar_yukle", lambda: {})
        monkeypatch.setattr(_b, "_ayar_kaydet", lambda v: None)
        b.groq_key = ""
        b.groq_model = "openai/gpt-oss-20b"
        b.anahtar_ayarla("yeni-anahtar")
        assert _b._cooldown_kaldi("groq") == 0
