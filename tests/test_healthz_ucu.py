"""tests/test_healthz_ucu.py — `/healthz` sağlık ucu sözleşmesi (P3.1).

Sözleşme:
- **Kimliksiz 200:** orkestratör erişebilmeli; üretimde de kimlik sorulmaz.
- **Gövde sabit ve dar:** yalnız `{"ok": true}`. Sağlayıcı listesi, model
  adı, commit sha, araç sayısı ve zincir durumu VERİLMEZ — o bilgi
  `/api/durum`'da ve token'lıdır
  (`tests/test_uretim_kapisi.py::test_durum_ucu_kimliksiz_okunamaz`).
- **Ucuz:** hiçbir ağır yola (çekirdek/zincir/kota/hafıza) dokunmaz.

Ağ yok, sağlayıcı yok, disk yok: karar yalnız yanıt gövdesinden ölçülür.
"""

import json
import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as app_modulu


def _istemci(monkeypatch, tmp_path):
    """Üretim modu + token tanımlı: kapı karar verebilir durumda.

    `_hafizayi_bir_kez_sifirla` sahtelenir: gerçek temiz başlangıç
    kilidi testte çalışmamalı (`tests/test_uretim_kapisi.py` ile aynı
    düzen).
    """
    monkeypatch.setenv("BASAK_URETIM", "1")
    monkeypatch.setenv("BASAK_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("BASAK_WEB_TOKEN", "gizli123-test")
    monkeypatch.setattr(app_modulu, "_hafizayi_bir_kez_sifirla",
                        lambda: True)
    return TestClient(app_modulu.app)


def test_kimliksiz_200_ve_govde_sabit(monkeypatch, tmp_path):
    with _istemci(monkeypatch, tmp_path) as istemci:
        cevap = istemci.get("/healthz")
    assert cevap.status_code == 200, cevap.text
    assert cevap.json() == {"ok": True}
    assert cevap.headers.get("cache-control") == "no-store"


def test_govde_bilgi_sizdirmaz(monkeypatch, tmp_path):
    with _istemci(monkeypatch, tmp_path) as istemci:
        veri = istemci.get("/healthz").json()
    assert set(veri) == {"ok"}
    ham = json.dumps(veri).lower()
    for yasak in ("commit", "saglayici", "sağlayıcı", "model", "arac", "araç",
                  "zincir", "runtime", "hafiza", "hafıza", "kota", "surum"):
        assert yasak not in ham, yasak


def test_cekirdege_dokunmaz(monkeypatch, tmp_path):
    """/healthz ağır yolu açmamalı: çekirdek çağrılırsa test patlar."""

    def patlat(*_a, **_k):
        raise AssertionError("/healthz cekirdege dokunmamali")

    monkeypatch.setattr(app_modulu, "_cekirdek", patlat)
    with _istemci(monkeypatch, tmp_path) as istemci:
        assert istemci.get("/healthz").status_code == 200


def test_durum_ucu_tokenli_kalir(monkeypatch, tmp_path):
    """Yeni uç, var olan korumayı gevşetmez: /api/durum 401 kalır."""
    with _istemci(monkeypatch, tmp_path) as istemci:
        assert istemci.get("/api/durum").status_code == 401
        assert istemci.get("/healthz").status_code == 200
