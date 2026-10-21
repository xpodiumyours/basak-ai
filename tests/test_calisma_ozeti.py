"""tests/test_calisma_ozeti.py — "yapılan iş" özeti: çekirdekten okunur.

Sözleşme
--------
- `/api/calisma` yalnız ÇEKİRDEĞİN kayıtlarını okur: çalışma notları,
  yayın kaydı, fikir tabloları, görevler. İkinci beyin/model çağrısı yok.
- Kayıt yoksa boş doldurulmaz: liste boş döner, sayfa "kayıt yok" yazar.
- Notlar özel içeriktir → uç kimlik ister (üretimde 401/503).
- `tools/calisma.py` bir MODEL ARACI DEĞİLDİR: araç listesinde yoktur.
"""

import os
import re
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as app_modulu  # noqa: E402
from tools import calisma as calisma_modulu  # noqa: E402
from tools import definitions as tanimlar  # noqa: E402
from tools import matris as matris_modulu  # noqa: E402
from tools import tasks as tasks_modulu  # noqa: E402

KOK = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


@pytest.fixture
def web_istemci(monkeypatch, tmp_path):
    monkeypatch.setenv("BASAK_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("BASAK_URETIM", raising=False)
    monkeypatch.setattr(app_modulu, "_hafizayi_bir_kez_sifirla", lambda: True)
    return TestClient(app_modulu.app)


def _oku_yol(yol):
    with open(os.path.join(KOK, yol), encoding="utf-8") as f:
        return f.read()


# ── Uç ────────────────────────────────────────────────────────────────


def test_calisma_ucu_gercek_kayitlari_okur(web_istemci):
    """Uç dört kaynağı da getirir; notlar depoda GERÇEKTEN vardır."""
    cevap = web_istemci.get("/api/calisma")
    assert cevap.status_code == 200, cevap.text
    veri = cevap.json()
    for alan in ("notlar", "yayin", "tablolar", "gorevler"):
        assert alan in veri, alan
    notlar = veri["notlar"]
    assert notlar["hata"] is None, notlar
    assert notlar["liste"], "knowledge/ içinde not yok — kaynak bozuk"
    for not_ in notlar["liste"]:
        assert not_["ad"] and not_["baslik"]


def test_yayin_kaydi_tarihli_girdiler(web_istemci):
    """Yayın kaydı gerçekten tarihli satırları çözer (uydurma yok)."""
    veri = web_istemci.get("/api/calisma").json()
    yayin = veri["yayin"]
    assert yayin["hata"] is None, yayin
    assert yayin["liste"], "yayın kaydı boş — kaynak okunamadı"
    for kayit in yayin["liste"]:
        assert re.match(r"^\d{4}-\d{2}-\d{2}$", kayit["tarih"]), kayit
        assert kayit["metin"].strip()


def test_bos_durum_dogru_yazilir(web_istemci, tmp_path):
    """Kayıt yoksa SAYI UYDURMAZ: tablo ve görev listesi boş kalır."""
    veri = web_istemci.get("/api/calisma").json()
    assert veri["tablolar"]["liste"] == []
    assert veri["gorevler"]["acik"] == 0
    assert veri["gorevler"]["toplam"] == 0


def test_uretimde_kimliksiz_okunamaz(monkeypatch, tmp_path):
    """Notlar özel içeriktir: üretimde kimliksiz istek reddedilir."""
    monkeypatch.setenv("BASAK_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.delenv("BASAK_URETIM", raising=False)
    monkeypatch.setattr(app_modulu, "_hafizayi_bir_kez_sifirla", lambda: True)
    istemci = TestClient(app_modulu.app)
    cevap = istemci.get("/api/calisma")
    assert cevap.status_code in (401, 503), cevap.text


def test_calisma_model_araci_degil():
    """tools/calisma.py bir araç DEĞİLDİR: modele sunulmaz."""
    assert "calisma" not in tanimlar.TANINMIS_TOOLLAR
    adlar = [t["function"]["name"] for t in tanimlar.TOOLS]
    assert not any("calisma" in ad for ad in adlar), adlar


# ── Çekirdek okuyucular ───────────────────────────────────────────────


def test_matris_ozeti_kaniti_gosterir(monkeypatch, tmp_path):
    """Kanıtlı satır özette görünür: işin sonucu kanıtla birlikte çıkar."""
    monkeypatch.setattr(matris_modulu, "MATRIS_KOK", str(tmp_path))
    matris_modulu.matris_ac("Test fikri", "ornek")
    matris_modulu.satir_ekle(1, "adim", "Ilk adim")
    matris_modulu.kanit_ekle(1, 1, "olculdu")
    matris_modulu.satir_kapat(1, 1)

    ozet = matris_modulu.calisma_ozeti()
    assert ozet["hata"] is None
    assert len(ozet["liste"]) == 1
    tablo = ozet["liste"][0]
    assert tablo["baslik"] == "Test fikri"
    assert tablo["kanitli"] == 1 and tablo["toplam"] == 1
    assert tablo["satirlar"][0]["kanitlar"] == ["olculdu"]


def test_gorev_ozeti_sayar(tmp_path):
    """Görev özeti açık/kapalı sayar; dosya yoksa sıfır döner."""
    yol = str(tmp_path / "gorevler.json")
    bos = tasks_modulu.gorev_ozeti(yol)
    assert bos["toplam"] == 0 and bos["acik"] == 0 and bos["hata"] is None

    tasks_modulu.add_task("Bir is", yol)
    dolu = tasks_modulu.gorev_ozeti(yol)
    assert dolu["toplam"] == 1 and dolu["acik"] == 1
    assert dolu["liste"][0]["text"] == "Bir is"


def test_not_ozeti_bozuk_dosyayi_yutmaz(monkeypatch, tmp_path):
    """Okunamayan not atlanır; hata uydurma yok."""
    (tmp_path / "bozuk.md").write_text("﻿", encoding="utf-8")
    (tmp_path / "sağlam.md").write_text("# Baslik\n\nBir cumle.\n",
                                        encoding="utf-8")
    monkeypatch.setattr(calisma_modulu, "BILGI_KOK", str(tmp_path))
    sonuc = calisma_modulu.notlar()
    assert sonuc["hata"] is None
    adlar = [n["ad"] for n in sonuc["liste"]]
    assert "sağlam.md" in adlar


# ── Ekran ─────────────────────────────────────────────────────────────


def test_sayfa_calisma_blogunu_gosterir():
    """Durum sayfası çalışma özetini gösterir ve doğru uçtan okur."""
    html = _oku_yol("web/durum.html")
    assert 'id="calisma"' in html
    betik = _oku_yol("web/durum.js")
    assert "/api/calisma" in betik
    # Dürüst boş durum metinleri gömülü (kayıt yok yazılır).
    assert "Bu sunucuda henüz fikir tablosu yok." in betik
    assert "Kayıt yok." in betik
    # Özet bloğu ikinci bir model çağrısı yapmaz.
    assert "method: \"POST\"" in betik
