"""tests/test_saglayici_yuvalari.py — FAZ4-4 kapali yuvalar.

Kural (P0): veri karti olmadan hassas veri gitmez; ucretli cagri
varsayilan engelli. DeepSeek/Kimi adaptorleri cifte kapilidir:
bayrak + kart dosyasi. Ikisi de yoksa zincire GIREMEZ — ayarlardaki
anahtar TEK BASINA yetmez (kritik: deepseek_key dosyada durur).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


class TestKapaliYuvalar:
    def test_deepseek_varsayilan_kapali(self):
        from brain.adapters import deepseek_adapter as _m
        assert _m.adapter.create({}) is None

    def test_deepseek_anahtar_tek_basina_yetmez(self):
        from brain.adapters import deepseek_adapter as _m
        assert _m.adapter.create({"deepseek_key": "sk-test",
                                  "deepseek_acik": True}) is None

    def test_deepseek_bayrak_yoksa_kart_yetmez(self, tmp_path,
                                               monkeypatch):
        from brain.adapters import deepseek_adapter as _m
        kart = tmp_path / "deepseek.md"
        kart.write_text("kart", encoding="utf-8")
        monkeypatch.setattr(_m, "KART_YOLU", str(kart))
        assert _m.adapter.create({"deepseek_key": "sk-test"}) is None

    def test_deepseek_cifte_kapi_acilir(self, tmp_path, monkeypatch):
        from brain.adapters import deepseek_adapter as _m
        kart = tmp_path / "deepseek.md"
        kart.write_text("kart", encoding="utf-8")
        monkeypatch.setattr(_m, "KART_YOLU", str(kart))
        istemci = _m.adapter.create({"deepseek_key": "sk-test",
                                     "deepseek_acik": True})
        assert istemci is not None and istemci.musait()

    def test_kimi_varsayilan_kapali(self):
        from brain.adapters import kimi_adapter as _m
        assert _m.adapter.create({}) is None

    def test_kimi_model_sart(self, tmp_path, monkeypatch):
        from brain.adapters import kimi_adapter as _m
        kart = tmp_path / "kimi.md"
        kart.write_text("kart", encoding="utf-8")
        monkeypatch.setattr(_m, "KART_YOLU", str(kart))
        assert _m.adapter.create({"kimi_key": "sk-test",
                                  "kimi_acik": True}) is None

    def test_kimi_cifte_kapi_acilir(self, tmp_path, monkeypatch):
        from brain.adapters import kimi_adapter as _m
        kart = tmp_path / "kimi.md"
        kart.write_text("kart", encoding="utf-8")
        monkeypatch.setattr(_m, "KART_YOLU", str(kart))
        istemci = _m.adapter.create({"kimi_key": "sk-test",
                                     "kimi_model": "ornek-model",
                                     "kimi_acik": True})
        assert istemci is not None and istemci.musait()

    def test_kartlar_ucretli_isaretli(self):
        from brain import registry
        assert registry.ucretli_mi("deepseek") is True
        assert registry.ucretli_mi("kimi") is True

    def test_zincir_ucretliyi_sokmaz(self):
        from brain.adapters.registry import create_providers
        saglayicilar = create_providers(
            {"deepseek_key": "sk-test", "kimi_key": "sk-test",
             "kimi_model": "ornek-model"})
        assert "deepseek" not in saglayicilar
        assert "kimi" not in saglayicilar
