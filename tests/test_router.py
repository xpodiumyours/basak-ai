"""tests/test_router.py — P3 Router v2 testleri.

Registry, Secici Motoru, Permission Layer ve Brain.cevapla entegrasyonu
(sahte istemcilerle, ag yok). Kota katmanı 2026-08-25'te söküldü;
kota testleri kaldırıldı.
"""

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import registry, secici
from tools.permissions import ETIKETLER, izinli_mi


class TestRegistry:
    def test_bilinmeyen_saglayici_guvenli_kart(self):
        k = registry.kart("hayali-saglayici")
        assert k["ucretsiz"] is True  # varsayilan iyimser ama sayaclidir
        assert "not" in k

    def test_deepseek_ucretli(self):
        assert registry.ucretli_mi("deepseek") is True
        assert registry.ucretli_mi("groq") is False

    def test_tum_kartlar_zorunlu_alanlar(self):
        for ad, k in registry.SAGLAYICILAR.items():
            assert "ucretsiz" in k and "tools" in k and "gucleri" in k, ad

    def test_varsayilan_zincirde_ucretli_yok(self):
        # Ucretli saglayici (deepseek) zincirden tamamen cikarildi;
        # kazayla cagrilmasin diye varsayilan zincir tamamen ucretsiz olmali.
        for ad in registry.VARSAYILAN_SIRA:
            assert registry.ucretli_mi(ad) is False, f"{ad} ucretli, zincire giremez"

    def test_varsayilan_sira_olcum_duzenli(self):
        # 2026-09-09 tam tespit: guvenilirler onde, bitikler arkada.
        sira = registry.VARSAYILAN_SIRA
        assert sira.index("glm") < sira.index("gemini")
        assert sira.index("cloudflare") < sira.index("kilo")
        assert sira.index("groq") < sira.index("openrouter")

    def test_qwen_uykuda(self):
        # Qwen hesap etkinlesene kadar zincire giremez.
        assert registry.kart("qwen").get("etkin") is False


class TestSiniflandirma:
    def test_kod(self):
        assert secici.siniflandir("python fonksiyonu yaz") == "kod"

    def test_arastirma(self):
        assert secici.siniflandir("kvantum nedir detaylı araştır") == "arastirma"

    def test_hiz(self):
        assert secici.siniflandir("hızlı bir cevap ver") == "hiz"

    def test_genel(self):
        assert secici.siniflandir("naber") == "genel"


class TestSecici:
    def test_kod_isinde_glm_once(self):
        sirali, gerekce = secici.sec(gorev_tipi="kod")
        # 2026-09-09: kilo-once kurali kaldirildi (basari %25).
        # Kod isinde GLM guvenilir oldugu icin once gelir.
        assert sirali[0] == "glm"
        assert "kod" in gerekce

    def test_arastirmada_glm_once(self):
        sirali, _ = secici.sec(gorev_tipi="arastirma")
        # 2026-09-09: arastirmada GLM once (Cohere %38.1 ile zayif).
        assert sirali[0] == "glm"

    def test_kilo_one_alinmaz(self):
        # Kilo zincirde yedek durur, one alinmaz.
        sirali, _ = secici.sec(text="naber")
        assert "kilo" in sirali
        assert sirali[0] in set(registry.VARSAYILAN_SIRA[:3])

    def test_mevcut_olmayan_tercih_atlanir(self):
        sirali, _ = secici.sec(
            gorev_tipi="kod",
            mevcutlar=["groq"])  # nvidia/glm yok
        assert sirali == ["groq"]

    def test_gerekce_seffaf(self):
        _, gerekce = secici.sec(text="bu bugı debug et")
        assert "one alindi" in gerekce.replace("ö", "o").replace("ı", "i")

    def test_genel_varsayilan_sira(self):
        sirali, gerekce = secici.sec(text="naber")
        # Genel sohbette ilk 3 saglayici rastgele siralanir (dagitim)
        ilk_3 = set(registry.VARSAYILAN_SIRA[:3])
        assert sirali[0] in ilk_3, "ilk saglayici ilk 3 icinden olmali"
        assert len(sirali) == len(registry.VARSAYILAN_SIRA)
        assert "dagitilmis" in gerekce


class TestPermissionLayer:
    def test_tum_tanimli_araclar_etiketli(self):
        from tools.executor import TOOL_MAP
        for ad in TOOL_MAP:
            assert izinli_mi(ad), "%s etiketsiz!" % ad

    def test_bilinmeyen_araç_izinsiz(self):
        assert izinli_mi("terminal_calistir") is False
        assert izinli_mi("dosya_sil") is False

    def test_executor_guvenlik_engeli_dondurur(self):
        from tools.executor import calistir
        sonuc = calistir("terminal_calistir", {"komut": "dir"})
        assert "error" in sonuc
        assert "Güvenlik engeli" in sonuc["error"]

    def test_hassas_etiketler_beyaz_liste_disinda_yok(self):
        # Sistematik: hicbir arac birden fazla yazma+sistem tasiyamaz
        for ad, etiketler in ETIKETLER.items():
            assert not ({"yazma", "sistem"} <= set(etiketler)), ad


class SahteIstemci:
    """Brain.cevapla entegrasyon testi icin agsiz saglayici."""

    def __init__(self, hata=None):
        self.hata = hata
        self.cagrildi = 0

    def cevapla(self, messages, model=None, tools=None):
        self.cagrildi += 1
        if self.hata:
            raise self.hata
        return {"content": "tamam"}


class TestBrainRouterV2:
    def _brain(self, monkeypatch, zincir):
        from brain.brain import Brain
        b = Brain.__new__(Brain)  # __init__ anahtar/ag istemez
        monkeypatch.setattr(b, "_bulut_zinciri", lambda: zincir)
        return b

    def test_ilk_saglayici_kazanir(self, monkeypatch):
        a, c = SahteIstemci(), SahteIstemci()
        b = self._brain(monkeypatch, [("groq", a), ("glm", c)])
        yanit, kaynak = b.cevapla(
            [{"role": "user", "content": "selam"}], "qwen2.5:3b")
        assert yanit["content"] == "tamam"
        # 2026-09-09: varsayilan sirada glm groq'un onunde.
        assert kaynak.startswith("glm")
        assert a.cagrildi == 0 and c.cagrildi == 1

    def test_hata_verince_siradaki_gecer(self, monkeypatch):
        a, c = SahteIstemci(), SahteIstemci(hata=RuntimeError("patladi"))
        b = self._brain(monkeypatch, [("groq", a), ("glm", c)])
        yanit, kaynak = b.cevapla(
            [{"role": "user", "content": "selam"}], "qwen2.5:3b")
        assert kaynak.startswith("groq")
        assert a.cagrildi == 1 and c.cagrildi == 1
