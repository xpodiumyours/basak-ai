"""tests/test_yerel_kimlik.py — Yerel web kimliği anonimdir (2026-10-01).

Ölçülen sorun: kişisel kimlik (`casper`) HER ortamın düşüğüydü. Sonuç:
kimlik tanımlanmayan her web kurulumu (yerel `uvicorn app:app`, önizleme,
kendi sunucusuna kuran) "Casper'in kisisel asistanina" dönüyor ve yalnız
casper'a açılan kişisel bağlam (profil, knowledge/, Obsidian) kullanıcıya
giriyordu. Canlı sitede anonim kimlik (`u<16>`) verildiği için genel asistan
dönüyordu; iki yüz aynı koddan geliyordu.

Kilitler:
1. yerel kimlik varsayılan ANONİM'dir (casper asla otomatik değil),
2. kişisel kimlik yalnız BASAK_YEREL_KIMLIK ile bilinçli açılır,
3. masaüstü/Telegram hâlâ AÇIKÇA kişisel (dokunulmadı),
4. ÜRETIM (Vercel) kimlik yolu BİRBİR AYNIDIR — bu kısıt.
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pytest
from fastapi.testclient import TestClient

import app as app_modulu
import kullanici as kullanici_modulu
import chat.kimlik as kimlik
from chat.prompts import kisilik_blogu


def _yerel_kur(monkeypatch, tmp_path):
    """Üretim DEĞİL — yerel web modu (app'in anonim düştüğü dal)."""
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("BASAK_URETIM", raising=False)
    monkeypatch.delenv("VERCEL_ENV", raising=False)
    monkeypatch.delenv("BASAK_YEREL_KIMLIK", raising=False)
    monkeypatch.setenv("BASAK_STATE_DIR", str(tmp_path / "state"))


def _uretim_kur(monkeypatch, tmp_path):
    """Vercel üretimi — bu yola yerel kimlik FONKSİYONU DÜŞMEZ."""
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("BASAK_URETIM", raising=False)
    monkeypatch.delenv("BASAK_YEREL_KIMLIK", raising=False)
    monkeypatch.setenv("BASAK_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setattr(app_modulu, "_hafizayi_bir_kez_sifirla", lambda: True)


# ── 1. Varsayılan anonim ───────────────────────────────────────────

def test_yerel_kimlik_varsayilani_anonimdir(monkeypatch, tmp_path):
    _yerel_kur(monkeypatch, tmp_path)
    ids = {kullanici_modulu.yerel_kimlik() for _ in range(50)}
    assert len(ids) == 50
    assert all(re.fullmatch(r"u\d{16}", x) for x in ids)
    assert "casper" not in ids


def test_yerel_kimlik_bilincli_casper(monkeypatch, tmp_path):
    _yerel_kur(monkeypatch, tmp_path)
    monkeypatch.setenv("BASAK_YEREL_KIMLIK", "casper")
    assert kullanici_modulu.yerel_kimlik() == "casper"


def test_yerel_kimlik_bos_bayrak_anonim_uyarir(monkeypatch, tmp_path):
    """Bayrak tanımlı ama boş -> fail-closed anonim, sessizce casper değil."""
    _yerel_kur(monkeypatch, tmp_path)
    monkeypatch.setenv("BASAK_YEREL_KIMLIK", "")
    assert re.fullmatch(r"u\d{16}", kullanici_modulu.yerel_kimlik())


# ── 2. Uygulama gerçekten anonim kimlik veriyor ────────────────────

def test_web_api_kimligi_yerelde_casper_degil(monkeypatch, tmp_path):
    _yerel_kur(monkeypatch, tmp_path)
    with TestClient(app_modulu.app) as c:
        d = c.post("/api/kimlik", json={}).json()
    assert d["ok"] is True
    assert re.fullmatch(r"u\d{16}", d["kullanici"])
    assert d["kullanici"] != "casper"


def test_yerelde_casper_kisisel_baglami_acilmaz(monkeypatch, tmp_path):
    """Kişisel profil/NOT indeksi yalnız casper'a ait; anonimde yok."""
    _yerel_kur(monkeypatch, tmp_path)
    kid = kullanici_modulu.yerel_kimlik()

    # profil_blogu (chat.context._baglam_kur) kid == casper diye kontrol eder
    assert kid != kimlik.VARSAYILAN_KULLANICI

    # kişilik bloğu kişisel asistan SÖYLEMEZ
    kisi = kisilik_blogu(kid)
    assert "Casper'in kisisel asistanisin" not in kisi
    assert "Casper" not in kisi


# ── 3. Masaüstü/Telegram kişisel kalır (dokunulmadı) ──────────────

def test_masaustu_hala_acikca_kisisel(monkeypatch, tmp_path):
    """basak_app.py kullanici_kur('casper') ile KENDİ kimliğini kurar."""
    _yerel_kur(monkeypatch, tmp_path)
    kaynak = (Path(__file__).resolve().parents[1] / "basak_app.py") \
        .read_text(encoding="utf-8")
    assert 'kullanici_kur("casper")' in kaynak

    kimlik.kullanici_kur("casper")
    try:
        kisi = kisilik_blogu()
        assert "Casper'in kisisel asistanisin" in kisi
    finally:
        kimlik.kullanici_kur(kimlik.VARSAYILAN_KULLANICI)


# ── 4. ÜRETİM (Vercel) YOLU DEĞİŞMEDİ — kısıt ─────────────────────

def test_uretimde_cerezsiz_kimlik_degismedi(monkeypatch, tmp_path):
    """Üretim + çerez yok + token yok -> None (yerel kimlik DEVRE DIŞI)."""
    _uretim_kur(monkeypatch, tmp_path)
    monkeypatch.delenv("BASAK_OTURUM_ANAHTARI", raising=False)
    monkeypatch.delenv("BASAK_WEB_TOKEN", raising=False)
    from starlette.requests import Request
    istek = Request({
        "type": "http", "http_version": "1.1", "method": "GET",
        "scheme": "https", "path": "/api/sohbetler",
        "raw_path": b"/api/sohbetler", "query_string": b"",
        "root_path": "", "headers": [], "client": ("203.0.113.9", 1),
        "server": ("testserver", 443),
    })
    assert app_modulu._kimlik(istek) is None


def test_uretimde_token_hala_casper_doner(monkeypatch, tmp_path):
    """X-Basak-Token yine Casper'e çıkar — üretimin kimliği korundu."""
    _uretim_kur(monkeypatch, tmp_path)
    monkeypatch.delenv("BASAK_OTURUM_ANAHTARI", raising=False)
    monkeypatch.setenv("BASAK_WEB_TOKEN", "gizli-token-123")
    from starlette.requests import Request
    istek = Request({
        "type": "http", "http_version": "1.1", "method": "GET",
        "scheme": "https", "path": "/api/sohbetler",
        "raw_path": b"/api/sohbetler", "query_string": b"",
        "root_path": "",
        "headers": [(b"x-basak-token", b"gizli-token-123")],
        "client": ("203.0.113.9", 1), "server": ("testserver", 443),
    })
    assert app_modulu._kimlik(istek) == kimlik.VARSAYILAN_KULLANICI


def test_uretimde_yerel_kimlik_fonksiyonu_kullanilmiyor(monkeypatch, tmp_path):
    """Yalın kanıt: üretim dalı yerel kimlik fonksiyonunu ÇAĞIRMAZ."""
    _uretim_kur(monkeypatch, tmp_path)
    monkeypatch.setenv("BASAK_WEB_TOKEN", "gizli-token-123")

    def _patladi():
        raise AssertionError("Üretim yolu yerel_kimlik'e düştü")

    monkeypatch.setattr(kullanici_modulu, "yerel_kimlik", _patladi)

    from starlette.requests import Request
    istek = Request({
        "type": "http", "http_version": "1.1", "method": "GET",
        "scheme": "https", "path": "/api/sohbetler",
        "raw_path": b"/api/sohbetler", "query_string": b"",
        "root_path": "",
        "headers": [(b"x-basak-token", b"gizli-token-123")],
        "client": ("203.0.113.9", 1), "server": ("testserver", 443),
    })
    assert app_modulu._kimlik(istek) == kimlik.VARSAYILAN_KULLANICI
