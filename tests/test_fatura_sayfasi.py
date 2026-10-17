"""tests/test_fatura_sayfasi.py — canlı fatura okuma ekranı sözleşmesi.

Sözleşme:
- `/fatura` sayfası servis edilir ve gerçek uca (`/api/fatura-oku`) bağlanır.
- Metin modu anahtar gerektirmez: alanlar + tablo + denetimler döner.
- Fotoğraf modu GERÇEK staging yapar; okuma başarısızsa hata AYNEN
  döner (sahte sonuç yok, kırpılmış "başarı" yok).
- Boş gövde 400.

Ağ yok: `fatura_oku` sahtelenir; staging gerçek dosyaya yazılır.
"""

import json
import os
import sys

from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as app_modulu
from tools import katalog

METIN = (
    "MAPA MOBİLYA VE AKSESUAR PAZARLAMA A.Ş.\n"
    "Tarih : 14.10.2026\n"
    "Fatura No : IK-2026-10427\n"
    "Düzenleme Saati : 15:42\n"
    "Vergi Dairesi: Ümraniye\n"
    "VKN: 6120729513\n"
    "Mersis No: 0612072951300010\n"
    "SATICI BİLGİLERİ\n"
    "MAPA MOBİLYA VE AKSESUAR PAZARLAMA A.Ş.\n"
    "ALICI BİLGİLERİ\n"
    "Nova İç Mimarlık ve Tasarım Ltd. Şti.\n"
    "Vergi Dairesi: Zincirlikuyu\n"
    "VKN: 2345678901\n"
    "1 200.114.08 LACK Yan Sehpa Siyah 55x55 cm 2 189,00 TL 378,00 TL\n"
    "2 000.000.02 Deneme Ürün Beyaz 10x10 cm 1 54.342,00 TL 54.342,00 TL\n"
    "Matrah: 54.720,00 TL\n"
    "KDV (%20): 10.944,00 TL\n"
    "GENEL TOPLAM: 65.664,00 TL"
)

PNG = ("data:image/png;base64,"
       "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAYAAAAfFcSJAAAADUlEQVR42mP8"
       "z8BQDwAEhQGAhKmMIQAAAABJRU5ErkJggg==")


def _istemci(monkeypatch, tmp_path):
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setenv("BASAK_OTURUM_ANAHTARI", "test-fatura-anahtari-1")
    monkeypatch.setattr(app_modulu, "_cekirdek", lambda: (object(), []))
    monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path / "gelen"))
    monkeypatch.setattr(katalog, "KATALOG_KOK", str(tmp_path / "kat"))
    return TestClient(app_modulu.app)


def test_sayfa_servis_edilir(monkeypatch, tmp_path):
    with _istemci(monkeypatch, tmp_path) as istemci:
        cevap = istemci.get("/fatura")
    assert cevap.status_code == 200, cevap.text
    assert "Fatura okuma" in cevap.text
    assert "/api/fatura-oku" in cevap.text


def test_metinden_rapor_uretir(monkeypatch, tmp_path):
    with _istemci(monkeypatch, tmp_path) as istemci:
        cevap = istemci.post("/api/fatura-oku", json={"metin": METIN})
    assert cevap.status_code == 200, cevap.text
    veri = cevap.json()
    assert veri["kaynak"] == "metin"
    assert len(veri["satirlar"]) == 2
    assert veri["eksik"] == []
    assert veri["ustbilgi"]["fis_no"] == "IK-2026-10427"
    assert veri["ustbilgi"]["alici_vkn"] == "2345678901"
    assert [d["durum"] for d in veri["denetim"]] == [True, True, True]


def test_satir_tutari_tutmazsa_rapor_uyarir(monkeypatch, tmp_path):
    bozuk = METIN.replace(
        "2 000.000.02 Deneme Ürün Beyaz 10x10 cm 1 54.342,00 TL 54.342,00 TL",
        "2 000.000.02 Deneme Ürün Beyaz 10x10 cm 1 54.342,00 TL 51.000,00 TL")
    with _istemci(monkeypatch, tmp_path) as istemci:
        veri = istemci.post("/api/fatura-oku", json={"metin": bozuk}).json()
    durumlar = {d["ad"]: d["durum"] for d in veri["denetim"]}
    assert durumlar["Her satırda miktar × birim fiyat = tutar"] is False
    assert durumlar[
        "Satır tutarları toplamı = genel toplam ya da matrah"] is False


def test_fotograf_gercek_staging_yapar_ve_hatayi_aynen_dondurur(
        monkeypatch, tmp_path):
    monkeypatch.setattr(katalog, "fatura_oku",
                        lambda fid: {"error": "test: saglayici anahtari yok"})
    with _istemci(monkeypatch, tmp_path) as istemci:
        cevap = istemci.post("/api/fatura-oku",
                             json={"b64": PNG, "ad": "deneme.png"})
    assert cevap.status_code == 200, cevap.text
    veri = cevap.json()
    assert veri["fatura_id"].startswith("gln_")
    assert veri["okuma"]["ok"] is False
    assert veri["okuma"]["hata"] == "test: saglayici anahtari yok"
    assert veri["satirlar"] == []


def test_kaydedilemeyen_dosya_400(monkeypatch, tmp_path):
    with _istemci(monkeypatch, tmp_path) as istemci:
        cevap = istemci.post("/api/fatura-oku",
                             json={"b64": "data:image/png;base64,!!bozuk!!",
                                   "ad": "bozuk.png"})
    assert cevap.status_code == 400, cevap.text
    assert "error" in cevap.json()


def test_bos_govde_400(monkeypatch, tmp_path):
    with _istemci(monkeypatch, tmp_path) as istemci:
        cevap = istemci.post("/api/fatura-oku", json={})
    assert cevap.status_code == 400, cevap.text


def test_rapor_govdesi_ayni_sozlesmeyi_tasir(monkeypatch, tmp_path):
    """Gövde alanları istemci sözleşmesidir; sessizce değişmemeli."""
    from fatura_rapor import govde
    veri = govde("metin", "yazi", {"fis_no": "X"}, [])
    assert set(veri) == {"kaynak", "fatura_id", "okuma", "yazi", "ustbilgi",
                         "satirlar", "eksik", "denetim"}
    assert json.dumps(veri)  # serileştirilebilir
