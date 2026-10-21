"""tests/test_web_onizleme_ayari.py — barindirilan onizleme icin port/adres.

Neden: bulut onizleme kabugu (3001) gercek uygulamayi gostermeliydi ama
`basak_web.py` portu yalniz `ayarlar.json`dan okuyordu; o dosya depoda
yok, varsayilan 8787 + yalniz 127.0.0.1. Bu yuzden 3001'e eski bir statik
sunucu denk geldi ve ekranda "404 File not found" gorundu.

Sozlesme:
- `BASAK_WEB_PORT` portu belirler.
- `BASAK_WEB_DIS` acikken 0.0.0.0'a baglanir (onizleme dis adresten gorsun).
- Ortam bos ise davranis degismez: 8787 + 127.0.0.1.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import basak_web


@pytest.fixture(autouse=True)
def _ortam_temiz(monkeypatch):
    monkeypatch.delenv("BASAK_WEB_PORT", raising=False)
    monkeypatch.delenv("BASAK_WEB_DIS", raising=False)


def test_varsayilan_degismedi(monkeypatch, tmp_path):
    monkeypatch.setattr(basak_web, "AYARLAR", str(tmp_path / "yok.json"))
    assert basak_web._sunucu_ayarlari() == (8787, "127.0.0.1")


def test_ortam_portu_ve_dis_erisim(monkeypatch, tmp_path):
    monkeypatch.setattr(basak_web, "AYARLAR", str(tmp_path / "yok.json"))
    monkeypatch.setenv("BASAK_WEB_PORT", "3001")
    monkeypatch.setenv("BASAK_WEB_DIS", "1")
    assert basak_web._sunucu_ayarlari() == (3001, "0.0.0.0")


def test_ayarlar_dosyasi_hala_gecerli(monkeypatch, tmp_path):
    ayar = tmp_path / "ayarlar.json"
    ayar.write_text(json.dumps({"web_port": 9100,
                                "web_dis_erisim": True}), encoding="utf-8")
    monkeypatch.setattr(basak_web, "AYARLAR", str(ayar))
    assert basak_web._sunucu_ayarlari() == (9100, "0.0.0.0")


def test_ortam_ayardan_once_gelir(monkeypatch, tmp_path):
    ayar = tmp_path / "ayarlar.json"
    ayar.write_text(json.dumps({"web_port": 9100}), encoding="utf-8")
    monkeypatch.setattr(basak_web, "AYARLAR", str(ayar))
    monkeypatch.setenv("BASAK_WEB_PORT", "3001")
    assert basak_web._sunucu_ayarlari()[0] == 3001


def test_dis_erisim_kapali_degerleri_kapali_kalir(monkeypatch, tmp_path):
    monkeypatch.setattr(basak_web, "AYARLAR", str(tmp_path / "yok.json"))
    for deger in ("0", "", "hayir", "false"):
        monkeypatch.setenv("BASAK_WEB_DIS", deger)
        assert basak_web._sunucu_ayarlari()[1] == "127.0.0.1", deger
