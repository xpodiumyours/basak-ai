"""tests/test_uretim_kapisi.py — Uretim kimlik kapisi (P0, 2026-09-23).

Olculen sorun: `giris_zorunlu_mu()` kullanici tablosu bosken False
donuyordu, `app._kimlik()` de o durumda VARSAYILAN_KULLANICI'ya dusuyordu.
Vercel'de kullanici tablosu gecici klasorde tutuldugu ve bulutta hesap
acma yolu olmadigi icin tablo HER ZAMAN bos -> kapi HER ZAMAN acik.

Sozlesme (OWASP deny-by-default: karar verilemiyorsa REDDET):
- uretimde giris her zaman zorunlu (tablo bos olsa bile),
- uretimde oturum anahtari ortamdan gelmek zorunda (dosyaya uretilmez),
- uretimde kapi: gecerli imzali cerez VEYA dogru X-Basak-Token,
- ikisi de tanimli degilse uygulama 503 verir, sessizce acilmaz,
- yerelde eski davranis (tek-kullanici modu) aynen korunur.

Mock yok: gercek fonksiyonlar gercek Request/TestClient ile cagirilir.
"""

import os
import sys

import pytest
from starlette.requests import Request

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import app as app_modulu  # noqa: E402
import kullanici as kullanici_modulu  # noqa: E402
from chat.kimlik import VARSAYILAN_KULLANICI, state_kok  # noqa: E402


def _uretim(monkeypatch):
    """Uretim modunu acar (Vercel'in kendi bayragiyla)."""
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("BASAK_URETIM", raising=False)


def _yerel(monkeypatch):
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("BASAK_URETIM", raising=False)


def _anahtarsiz(monkeypatch):
    monkeypatch.delenv("BASAK_OTURUM_ANAHTARI", raising=False)
    monkeypatch.delenv("BASAK_WEB_TOKEN", raising=False)


def _istek(basliklar=None, cerez=None):
    """Gercek Starlette Request (ASGI scope'undan)."""
    ham = []
    for ad, deger in (basliklar or {}).items():
        ham.append((ad.lower().encode("ascii"), deger.encode("utf-8")))
    if cerez:
        ham.append((b"cookie", ("%s=%s" % cerez).encode("utf-8")))
    return Request({
        "type": "http", "http_version": "1.1", "method": "GET",
        "scheme": "http", "path": "/api/sohbetler",
        "raw_path": b"/api/sohbetler", "query_string": b"",
        "root_path": "", "headers": ham,
        "client": ("203.0.113.9", 4242), "server": ("testserver", 80),
    })


class TestGirisZorunlulugu:
    def test_uretimde_tablo_bossa_giris_zorunlu(self, monkeypatch):
        """1. Uretim + bos tablo -> giris_zorunlu_mu() True."""
        _uretim(monkeypatch)
        assert kullanici_modulu.kullanici_listesi() == {}
        assert kullanici_modulu.uretim_mi() is True
        assert kullanici_modulu.giris_zorunlu_mu() is True

    def test_yerelde_tablo_bossa_giris_zorunlu_degil(self, monkeypatch):
        """2. Yerel + bos tablo -> False (eski tek-kullanici davranisi)."""
        _yerel(monkeypatch)
        assert kullanici_modulu.kullanici_listesi() == {}
        assert kullanici_modulu.uretim_mi() is False
        assert kullanici_modulu.giris_zorunlu_mu() is False


class TestAnahtarFailClosed:
    def test_uretimde_env_anahtari_yoksa_hata(self, monkeypatch, tmp_path):
        """3. Uretim + env anahtari yok -> RuntimeError, dosyaya YAZILMAZ."""
        _uretim(monkeypatch)
        _anahtarsiz(monkeypatch)
        yol = os.path.join(state_kok(), "oturum.anahtar")
        assert not os.path.exists(yol)
        with pytest.raises(RuntimeError):
            kullanici_modulu._anahtar()
        assert not os.path.exists(yol), "uretimde anahtar dosyaya uretildi"

    def test_yerelde_anahtar_dosyadan_uretilir(self, monkeypatch):
        """Yan guvence: yerelde eski dosya davranisi bozulmadi."""
        _yerel(monkeypatch)
        _anahtarsiz(monkeypatch)
        anahtar = kullanici_modulu._anahtar()
        assert isinstance(anahtar, bytes) and len(anahtar) >= 32
        assert os.path.exists(os.path.join(state_kok(), "oturum.anahtar"))


class TestUretimKimlikKapisi:
    def test_cerezsiz_ve_tokensiz_istek_kimliksiz(self, monkeypatch):
        """4. Uretim + cerez yok + token yok -> kimlik None."""
        _uretim(monkeypatch)
        # (a) hicbir sey tanimli degil
        _anahtarsiz(monkeypatch)
        assert app_modulu._kimlik(_istek()) is None
        # (b) sunucuda token var ama istek tasimiyor
        monkeypatch.setenv("BASAK_WEB_TOKEN", "gizli-token-123")
        assert app_modulu._kimlik(_istek()) is None
        # (c) yanlis token da gecmez
        assert app_modulu._kimlik(
            _istek({"X-Basak-Token": "yanlis"})) is None

    def test_dogru_token_ile_kimlik_doner(self, monkeypatch):
        """5. Uretim + dogru X-Basak-Token -> kimlik doner."""
        _uretim(monkeypatch)
        _anahtarsiz(monkeypatch)
        monkeypatch.setenv("BASAK_WEB_TOKEN", "gizli-token-123")
        kid = app_modulu._kimlik(_istek({"X-Basak-Token": "gizli-token-123"}))
        assert kid == VARSAYILAN_KULLANICI

    def test_ascii_disi_token_cokmez(self, monkeypatch):
        """6. Uretim + Turkce harfli token -> None (500 degil)."""
        _uretim(monkeypatch)
        _anahtarsiz(monkeypatch)
        monkeypatch.setenv("BASAK_WEB_TOKEN", "gizli-token-123")
        istek = _istek({"X-Basak-Token": "Başak123"})
        assert not istek.headers.get("x-basak-token").isascii()
        assert app_modulu._kimlik(istek) is None

    def test_bozuk_cerez_uretimde_cokmez(self, monkeypatch):
        """Yan guvence: anahtarsiz uretimde bozuk cerez 500 yapmaz."""
        _uretim(monkeypatch)
        _anahtarsiz(monkeypatch)
        istek = _istek(cerez=(kullanici_modulu.cookie_adi(), "abc.def"))
        assert app_modulu._kimlik(istek) is None


class TestAnahtarsizUretim503:
    def test_anahtar_ve_token_yoksa_503(self, monkeypatch):
        """Uretimde hic anahtar/token yoksa kapi karar veremez: 503."""
        from fastapi.testclient import TestClient

        _uretim(monkeypatch)
        _anahtarsiz(monkeypatch)
        with TestClient(app_modulu.app) as istemci:
            cevap = istemci.get("/api/sohbetler")
        assert cevap.status_code == 503
        assert "BASAK_OTURUM_ANAHTARI" in cevap.json()["error"]

    def test_token_varsa_401(self, monkeypatch):
        """Token tanimliysa karar verilebilir: 503 degil, duz 401."""
        from fastapi.testclient import TestClient

        _uretim(monkeypatch)
        _anahtarsiz(monkeypatch)
        monkeypatch.setenv("BASAK_WEB_TOKEN", "gizli-token-123")
        with TestClient(app_modulu.app) as istemci:
            cevap = istemci.get("/api/sohbetler")
        assert cevap.status_code == 401
