"""tests/test_router.py — ücretsiz teknik fallback sözleşmesi.

Sağlayıcı seçimi kullanıcı mesajının türüne göre yapılmaz. Sıra sabittir;
yalnız teknik uygunluk, araç desteği ve geçici cooldown etkiler. Ücretli
sağlayıcı otomatik zincire giremez.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import registry, secici
from tools.permissions import ETIKETLER, izinli_mi


class TestRegistry:
    def test_bilinmeyen_saglayici_guvenli_kart(self):
        k = registry.kart("hayali-saglayici")
        assert k["ucretsiz"] is True
        assert "not" in k

    def test_ucretli_kartlar_taninir(self):
        assert registry.ucretli_mi("deepseek") is True
        assert registry.ucretli_mi("genel") is True
        assert registry.ucretli_mi("groq") is False

    def test_varsayilan_zincirde_ucretli_yok(self):
        for ad in registry.VARSAYILAN_SIRA:
            assert registry.ucretli_mi(ad) is False

    def test_qwen_eski_kilidi_runtime_da_kapali(self):
        from brain import brain as brain_mod
        assert brain_mod._QWEN_BEKLEMEDE is False


class TestSiniflandirma:
    def test_mesaj_icerigi_model_sinifi_uretmez(self):
        for metin in (
            "python fonksiyonu yaz",
            "detaylı araştır",
            "hızlı cevap ver",
            "müşteri bul",
            "naber",
        ):
            assert secici.siniflandir(metin) == "genel"


class TestSecici:
    def test_gorev_tipi_sirayi_degistirmez(self):
        mevcut = ["groq", "glm", "nvidia", "kilo"]
        temel, _ = secici.sec(mevcutlar=mevcut)
        for tip in ("kod", "arastirma", "hiz"):
            sirali, _ = secici.sec(gorev_tipi=tip, mevcutlar=mevcut)
            assert sirali == temel

    def test_mesaj_kelimesi_sirayi_degistirmez(self):
        mevcut = ["groq", "glm", "nvidia", "kilo"]
        a, _ = secici.sec(text="python kod yaz", mevcutlar=mevcut)
        b, _ = secici.sec(text="müşteri araştır", mevcutlar=mevcut)
        c, _ = secici.sec(text="naber", mevcutlar=mevcut)
        assert a == b == c

    def test_registry_sirasi_korunur(self):
        mevcut = ["groq", "glm", "nvidia", "kilo"]
        sirali, gerekce = secici.sec(mevcutlar=mevcut)
        beklenen = [a for a in registry.VARSAYILAN_SIRA if a in mevcut]
        assert sirali == beklenen
        assert "teknik" in gerekce

    def test_cooldown_saglayiciyi_sona_atabilir(self):
        import time
        mevcut = ["glm", "groq", "nvidia"]
        sirali, gerekce = secici.sec(
            mevcutlar=mevcut, cooldown={"glm": time.time() + 60})
        assert sirali[-1] == "glm"
        assert "cooldown" in gerekce

    def test_karne_sirayi_degistirmez(self):
        mevcut = ["groq", "glm", "nvidia", "kilo"]
        a, _ = secici.sec(mevcutlar=mevcut, karne_kullan=False)
        b, _ = secici.sec(mevcutlar=mevcut, karne_kullan=True)
        assert a == b


class TestPermissionLayer:
    def test_tum_tanimli_araclar_etiketli(self):
        from tools.executor import TOOL_MAP
        for ad in TOOL_MAP:
            assert izinli_mi(ad), "%s etiketsiz!" % ad

    def test_bilinmeyen_arac_izinsiz(self):
        assert izinli_mi("terminal_calistir") is False
        assert izinli_mi("dosya_sil") is False

    def test_executor_guvenlik_engeli_dondurur(self):
        from tools.executor import calistir
        sonuc = calistir("terminal_calistir", {"komut": "dir"})
        assert "error" in sonuc
        assert "Güvenlik engeli" in sonuc["error"]

    def test_hassas_etiketler_beyaz_liste_disinda_yok(self):
        for ad, etiketler in ETIKETLER.items():
            assert not ({"yazma", "sistem"} <= set(etiketler)), ad


class SahteIstemci:
    def __init__(self, hata=None):
        self.hata = hata
        self.cagrildi = 0

    def cevapla(self, messages, model=None, tools=None):
        self.cagrildi += 1
        if self.hata:
            raise self.hata
        return {"content": "tamam"}


class TestBrainRouter:
    def _brain(self, monkeypatch, zincir):
        from brain.brain import Brain
        b = Brain.__new__(Brain)
        monkeypatch.setattr(b, "_bulut_zinciri", lambda: zincir)
        return b

    def test_teknik_sirada_ilk_saglayici_kazanir(self, monkeypatch):
        groq, glm = SahteIstemci(), SahteIstemci()
        b = self._brain(monkeypatch, [("groq", groq), ("glm", glm)])
        yanit, kaynak = b.cevapla(
            [{"role": "user", "content": "selam"}], "qwen2.5:3b")
        assert yanit["content"] == "tamam"
        assert kaynak == "glm"
        assert glm.cagrildi == 1 and groq.cagrildi == 0

    def test_hata_verince_siradaki_gecer(self, monkeypatch):
        groq = SahteIstemci()
        glm = SahteIstemci(hata=RuntimeError("patladi"))
        b = self._brain(monkeypatch, [("groq", groq), ("glm", glm)])
        yanit, kaynak = b.cevapla(
            [{"role": "user", "content": "selam"}], "qwen2.5:3b")
        assert kaynak == "groq"
        assert groq.cagrildi == 1 and glm.cagrildi == 1


class TestZamanAsimiCooldown:
    def test_zaman_asimi_tespiti(self):
        from brain.brain import _zaman_asimi_mi
        assert _zaman_asimi_mi(RuntimeError("Request timed out."))
        assert _zaman_asimi_mi(RuntimeError("The read operation timed out"))
        assert _zaman_asimi_mi(RuntimeError("Connection reset by peer"))
        assert not _zaman_asimi_mi(RuntimeError("429 rate limit"))
        assert not _zaman_asimi_mi(RuntimeError("patladi"))

    def _taze_brain(self, monkeypatch, zincir, sira):
        from brain import brain as brain_mod
        brain_mod._COOLDOWN.clear()
        monkeypatch.setattr(
            secici, "sec", lambda **kw: (list(sira), "test sirasi"))
        return TestBrainRouter()._brain(monkeypatch, zincir)

    def test_zaman_asimi_sonraki_istekte_atlanir(self, monkeypatch):
        from brain import brain as brain_mod
        glm = SahteIstemci(hata=RuntimeError("The read operation timed out"))
        groq = SahteIstemci()
        b = self._taze_brain(
            monkeypatch, [("glm", glm), ("groq", groq)], ("glm", "groq"))

        _, kaynak = b.cevapla(
            [{"role": "user", "content": "selam"}], "qwen2.5:3b")
        assert kaynak == "groq"
        kalan = brain_mod._cooldown_kaldi("glm")
        assert 30 < kalan <= 60

        glm.cagrildi = 0
        groq.cagrildi = 0
        _, kaynak2 = b.cevapla(
            [{"role": "user", "content": "selam"}], "qwen2.5:3b")
        assert kaynak2 == "groq"
        assert glm.cagrildi == 0 and groq.cagrildi == 1

    def test_429_uzun_cooldown_alir(self, monkeypatch):
        from brain import brain as brain_mod
        glm = SahteIstemci(hata=RuntimeError("429 rate limit exceeded"))
        groq = SahteIstemci()
        b = self._taze_brain(
            monkeypatch, [("glm", glm), ("groq", groq)], ("glm", "groq"))
        b.cevapla([{"role": "user", "content": "selam"}], "qwen2.5:3b")
        kalan = brain_mod._cooldown_kaldi("glm")
        assert 100 < kalan <= 120
