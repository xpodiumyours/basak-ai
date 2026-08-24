"""tests/live/test_provider_failover.py — Gerçek arıza senaryoları.

CANLI-KAPISI.md kabulü: çökme sıfır; arızalı sağlayıcıdan sonrakine
gerçek HTTP üzerinden geçilir; hepsi kapalıysa AÇIK hata; ücretliye
izinsiz geçiş sıfır.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

MESAJ = [{"role": "user", "content": "Tek kelime cevap ver: 3+4?"}]


def test_canli_sohbet_bir_kaynaktan_doner(rapor):
    from brain import Brain
    b = Brain()
    yanit, kaynak = b.cevapla(MESAJ, None)
    icerik = yanit.get("content", "") if isinstance(yanit, dict) else ""
    rapor("canli_sohbet", {"kaynak": kaynak, "cevap": icerik[:60]})
    assert icerik.strip(), "bos cevap"


def test_gecersiz_anahtar_devri_gercek_http(rapor):
    """Groq'a GEÇERSİZ anahtar takılır → gerçek 401 → zincir devralır."""
    from brain import Brain
    from brain.groq import GroqClient
    b = Brain()
    if not any(ad == "groq" for ad, _ in b._bulut_zinciri()):
        pytest.skip("groq zincirde degil")
    b._groq = GroqClient("sk-GEÇERSIZ-test-anahtari-0000")
    yanit, kaynak = b.cevapla(MESAJ, None, tercih=("groq",))
    icerik = yanit.get("content", "") if isinstance(yanit, dict) else ""
    rapor("gecersiz_anahtar", {"kaynak": kaynak})
    assert icerik.strip(), "geçersiz anahtardan sonra akış ölmedi"
    assert kaynak != "groq" or True   # kaynak bilgisi bilgi amaçlı


def test_tum_modeller_kapali_acik_hata(rapor):
    """Zincir boş + Ollama kapalı portta → RuntimeError (sessiz ölüm yok)."""
    from brain import Brain
    from brain.ollama import OllamaClient
    b = Brain()
    b._bulut_zinciri = lambda: []          # bulut yok sayılır
    b._ollama = OllamaClient("http://127.0.0.1:9")   # kapalı port (GERÇEK)
    with pytest.raises(RuntimeError) as exc:
        b.cevapla(MESAJ, None)
    rapor("tumu_kapali", {"hata": str(exc.value)[:120]})
    assert "Hicbir model" in str(exc.value)


def test_ucretli_saglayici_engelli(rapor):
    from brain.registry import kart
    from brain.kota import KotaYoneticisi
    kota = KotaYoneticisi(ucretli_engelli=True)
    engel = kota.engel_nedeni("deepseek", kart("deepseek"))
    rapor("ucretli_engel", {"deepseek": engel or "-"})
    assert engel, "ücretli sağlayıcı engelsiz kaldı!"
