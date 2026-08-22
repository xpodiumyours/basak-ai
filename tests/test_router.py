"""tests/test_router.py — P3 Router v2 testleri.

Registry, Secici Motoru, Kota Yoneticisi, Permission Layer ve
Brain.cevapla entegrasyonu (sahte istemcilerle, ag yok).
"""

import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain import registry, secici
from brain.kota import KotaYoneticisi, rate_limit_hatasi_mi, _retry_suresi_oku
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

    def test_varsayilan_sirada_ucretli_sonda(self):
        sira = registry.VARSAYILAN_SIRA
        assert sira.index("deepseek") == len(sira) - 1 or \
            all(not registry.ucretli_mi(a)
                for a in sira[sira.index("deepseek") + 1:])


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
    def test_kod_isinde_nvidia_once(self):
        sirali, gerekce = secici.sec(gorev_tipi="kod")
        assert sirali[0] == "nvidia"
        assert "kod" in gerekce

    def test_arastirmada_gemini_once(self):
        sirali, _ = secici.sec(gorev_tipi="arastirma")
        assert sirali[0] == "gemini"

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
        assert sirali[0] == "groq"  # varsayilan zincir basi
        assert "varsayilan" in gerekce


@pytest.fixture
def kota(tmp_path):
    k = KotaYoneticisi(dosya=str(tmp_path / "kota.json"))
    yield k


class TestKota:
    def test_ucretli_varsayilan_engelli(self, kota):
        neden = kota.engel_nedeni("deepseek", registry.kart("deepseek"))
        assert "ucretli" in neden

    def test_ucretli_izin_verilirse_acilir(self, tmp_path):
        k = KotaYoneticisi(dosya=str(tmp_path / "k.json"), ucretli_engelli=False)
        assert k.engel_nedeni("deepseek", registry.kart("deepseek")) is None

    def test_gunluk_limit_dolunca_engel(self, kota):
        kart = {"ucretsiz": True, "gunluk_istek": 2}
        assert kota.engel_nedeni("groq", kart) is None
        kota.harca("groq")
        kota.harca("groq")
        neden = kota.engel_nedeni("groq", kart)
        assert "limiti doldu" in neden

    def test_sayac_kalici(self, tmp_path):
        yol = str(tmp_path / "k.json")
        KotaYoneticisi(dosya=yol).harca("groq")
        k2 = KotaYoneticisi(dosya=yol)
        assert k2.durum["sayac"]["groq"]["istek"] == 1

    def test_429_soguma_kurar(self, kota):
        kurdu = kota.hata_isle(
            "gemini", "Error code: 429 - RESOURCE_EXHAUSTED retryDelay '52s'")
        assert kurdu is True
        neden = kota.engel_nedeni("gemini", {"ucretsiz": True})
        assert "soguma" in neden or "soğuma" in neden

    def test_normal_hata_soguma_kurmaz(self, kota):
        assert kota.hata_isle("groq", "connection timeout") is False
        assert kota.engel_nedeni("groq", {"ucretsiz": True}) is None

    def test_tarih_degisimi_sayaci_sifirlar(self, kota):
        kart = {"ucretsiz": True, "gunluk_istek": 1}
        kota.harca("groq")
        assert kota.engel_nedeni("groq", kart) is not None
        kota.durum["tarih"] = "2000-01-01"  # dün gibi göster
        assert kota.engel_nedeni("groq", kart) is None  # yeni gün → sıfırlandı

    def test_retry_suresi_okuma(self):
        assert _retry_suresi_oku("Please try again in 14m4s") >= 14 * 60
        assert _retry_suresi_oku("Please retry in 52.8s") >= 50
        assert _retry_suresi_oku("anlasilmayan hata") is None

    def test_rate_limit_tanimasi(self):
        assert rate_limit_hatasi_mi("429 Too Many Requests")
        assert rate_limit_hatasi_mi("quota exceeded for metric")
        assert not rate_limit_hatasi_mi("invalid api key")


class TestPermissionLayer:
    def test_tum_tanimli_araclar_etiketli(self):
        from tools.executor import TOOL_MAP
        for ad in TOOL_MAP:
            if ad == "get_reminders":
                continue  # placeholder lambda, gercek arac reminders'da
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
        b.kota = KotaYoneticisi(
            dosya=os.path.join(os.path.dirname(__file__), "_kota_test.json"))
        monkeypatch.setattr(b, "_bulut_zinciri", lambda: zincir)
        return b

    def test_ilk_saglayici_kazanir(self, monkeypatch):
        a, c = SahteIstemci(), SahteIstemci()
        b = self._brain(monkeypatch, [("groq", a), ("glm", c)])
        yanit, kaynak = b.cevapla(
            [{"role": "user", "content": "selam"}], "qwen2.5:3b")
        assert yanit["content"] == "tamam"
        assert kaynak.startswith("groq")
        assert a.cagrildi == 1 and c.cagrildi == 0

    def test_hata_verince_siradaki_gecer(self, monkeypatch):
        a, c = SahteIstemci(hata=RuntimeError("patladi")), SahteIstemci()
        b = self._brain(monkeypatch, [("groq", a), ("glm", c)])
        yanit, kaynak = b.cevapla(
            [{"role": "user", "content": "selam"}], "qwen2.5:3b")
        assert kaynak.startswith("glm")
        assert a.cagrildi == 1 and c.cagrildi == 1

    def test_kota_dolan_atlanir(self, monkeypatch, tmp_path):
        from brain.brain import Brain
        a, c = SahteIstemci(), SahteIstemci()
        b = Brain.__new__(Brain)
        b.kota = KotaYoneticisi(dosya=str(tmp_path / "k.json"))
        monkeypatch.setattr(b, "_bulut_zinciri", lambda: [("groq", a), ("glm", c)])
        # Groq'un gunluk limitini tek istekte dolacak sekilde kucuk ayarla
        b.kota.durum["sayac"]["groq"] = {"istek": registry.kart("groq")["gunluk_istek"]}
        yanit, kaynak = b.cevapla(
            [{"role": "user", "content": "naber"}], "qwen2.5:3b")
        assert kaynak.startswith("glm")
        assert a.cagrildi == 0 and c.cagrildi == 1

    def test_ucretli_zincirde_olsa_bile_engellenir(self, monkeypatch):
        from brain.brain import Brain
        a, yerel = SahteIstemci(), SahteIstemci()
        b = Brain.__new__(Brain)
        b.kota = KotaYoneticisi(
            dosya=os.path.join(os.path.dirname(__file__), "_kota_test.json"))
        b._ollama = yerel
        monkeypatch.setattr(b, "_bulut_zinciri", lambda: [("deepseek", a)])
        yanit, kaynak = b.cevapla(
            [{"role": "user", "content": "selam"}], "qwen2.5:3b")
        # Ucretli engellendi → kimse bulutu cagirmadi, yerel fallback devrede
        assert a.cagrildi == 0
        assert kaynak == "yerel"
        assert yanit["content"] == "tamam"
        b.kota.soguma_temizle("deepseek")
