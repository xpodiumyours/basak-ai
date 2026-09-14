"""tests/live/test_katalog_canli.py — Fatura görü provası (GERÇEK bulut).

Sentetik fatura görüntüsü üretilir (PIL), staging'e alınır, gerçek
bulut görü (image_analyzer) okur. Kota harcar — yalnız --live ile.

NVIDIA bileti yoksa atlanır (birim testler sahte görüyle koşar).
"""

import io
import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))


def _bilet_var_mi():
    if os.environ.get("NVIDIA_API_KEY"):
        return True
    try:
        with open(os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(
                    os.path.abspath(__file__)))),
                "ayarlar.json"), "r", encoding="utf-8-sig") as f:
            return bool(json.load(f).get("nvidia_key"))
    except (OSError, ValueError):
        return False


def _sentetik_fatura():
    from PIL import Image, ImageDraw
    resim = Image.new("RGB", (900, 500), "white")
    kalem = ImageDraw.Draw(resim)
    satirlar = [
        "TUTKU TEKSTIL - SATIS TEKLIF FORMU",
        "Tarih: 14.09.2026",
        "TK-102 Siyah S 5 adet 120,50 TL 8691234567890",
        "TK-102 Siyah M 3 adet 120,50 TL 8691234567891",
        "BR-7 Beyaz L 2 adet 200 TL",
    ]
    y = 30
    for satir in satirlar:
        kalem.text((30, y), satir, fill="black")
        y += 70
    tampon = io.BytesIO()
    resim.save(tampon, format="PNG")
    return tampon.getvalue()


def test_fatura_goru_canli(tmp_path, monkeypatch, rapor):
    if not _bilet_var_mi():
        pytest.skip("NVIDIA bileti yok")
    from tools import katalog
    monkeypatch.setattr(katalog, "GELEN_KOK", str(tmp_path))
    kayit = katalog._staging_kaydet(_sentetik_fatura(), "teklif.png")
    assert "result" in kayit, kayit
    fatura_id = json.loads(kayit["result"])["fatura_id"]
    sonuc = katalog.fatura_oku(fatura_id)
    assert "result" in sonuc, sonuc
    veri = json.loads(sonuc["result"])
    rapor("fatura_goru", {"uzunluk": len(veri["yazi"]),
                          "aday": len(veri["aday_satirlar"])})
    assert len(veri["yazi"]) >= 20
    assert "102" in veri["yazi"] or "120" in veri["yazi"]
