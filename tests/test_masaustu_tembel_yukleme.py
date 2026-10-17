"""tests/test_masaustu_tembel_yukleme.py — masaüstü katmanı gecikmeli yüklenir.

2026-10-13 ÖLÇÜMÜ: `basak_app.py` modül yüklenirken `import webview` ve
`from voice import TTS, STT` yapıyordu. `pywebview` ve ses katmanı
(`sounddevice` -> PortAudio sistem kütüphanesi) requirements.txt'te yalnız
`sys_platform == "win32"` için kurulur. Sonuç: `import basak_app` Linux'ta
düşüyordu ve TEST PAKETİ DAHA TOPLANIRKEN kırılıyordu
("PortAudio library not found"; `pytest tests` -> Interrupted) — oysa
üretim (Vercel) Linux'tur.

Bu dosya iki şeyi kilitler:
1. Masaüstü bağımlılıkları modül yüklenirken İSTENMEZ (yapısal).
2. Gevşetme gerçek bir erişim noktasıdır: kullanım anında içe aktarılır,
   yani masaüstünde davranış aynıdır (sahte modüllerle davranışsal).
"""

import ast
import pathlib
import sys
import types

import pytest

import basak_app

KAYNAK = pathlib.Path("basak_app.py").read_text(encoding="utf-8")


def _modul_seviyesi_importlar():
    """Yalniz GERCEK modul seviyesi importlar (girintili olanlar degil).

    Metin aramasi yaniltir: `_webview()` yardimcisinin ICINDEKI
    `    import webview` satiri modul yuklenirken calismaz. Bu yuzden
    AST ile yalniz agacin govdesi (body) taranir.
    """
    agac = ast.parse(KAYNAK)
    adlar = set()
    for dugum in agac.body:
        if isinstance(dugum, ast.Import):
            adlar.update(a.name.split(".")[0] for a in dugum.names)
        elif isinstance(dugum, ast.ImportFrom) and dugum.module:
            adlar.add(dugum.module.split(".")[0])
    return adlar


class TestModulYuklenirkenIstenmez:
    def test_modul_seviyesinde_webview_importu_yok(self):
        assert "webview" not in _modul_seviyesi_importlar(), (
            "modül seviyesinde pywebview importu var; Linux'ta (üretim "
            "platformu) `import basak_app` düşer")

    def test_modul_seviyesinde_ses_importu_yok(self):
        assert "voice" not in _modul_seviyesi_importlar(), (
            "modül seviyesinde ses katmanı importu var (PortAudio ister)")

    def test_modul_uzayinda_agir_nesne_tutulmaz(self):
        """Gevsetme yarim kalmis olmasin: import aninda cozulen nesne yok."""
        assert not hasattr(basak_app, "webview")
        assert not hasattr(basak_app, "TTS")
        assert not hasattr(basak_app, "STT")


class TestGevsetmeKullanimAnindaCalisir:
    """Erişim noktaları gerçekten çalışmalı — yoksa sessiz çökme olurdu."""

    def test_tts_ve_stt_siniflari_kullanim_aninda_cozulur(self, monkeypatch):
        sahte = types.ModuleType("voice")

        class SahteTTS:
            def __init__(self, **kw):
                self.kw = kw

        class SahteSTT:
            pass

        sahte.TTS = SahteTTS
        sahte.STT = SahteSTT
        monkeypatch.setitem(sys.modules, "voice", sahte)

        assert basak_app._tts_sinifi() is SahteTTS
        assert basak_app._stt_sinifi() is SahteSTT

    def test_webview_kullanim_aninda_cozulur_ve_pencereyi_kullanir(
            self, monkeypatch):
        cagrilar = []

        class SahtePencere:
            def show(self):
                cagrilar.append("show")

            def hide(self):
                cagrilar.append("hide")

        sahte = types.ModuleType("webview")
        sahte.windows = [SahtePencere()]
        monkeypatch.setitem(sys.modules, "webview", sahte)

        basak_app._pencere_goster()
        basak_app._pencere_gizle()
        assert cagrilar == ["show", "hide"]

    def test_pencere_yokken_cagri_patlamaz(self, monkeypatch):
        sahte = types.ModuleType("webview")
        sahte.windows = []
        monkeypatch.setitem(sys.modules, "webview", sahte)

        basak_app._pencere_goster()      # istisna BEKLENMEZ
        basak_app._pencere_gizle()

    def test_eksik_kutuphane_gizlenmez(self, monkeypatch):
        """Gevşetme hatayı yutmamalı: gerçekten gerektiğinde ImportError."""
        monkeypatch.setitem(sys.modules, "webview", None)
        with pytest.raises(ImportError):
            basak_app._webview()
