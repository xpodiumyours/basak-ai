"""tests/live/test_seviye1_native.py — Duzey 1 kabul testi.

Yalniz --live ile kosar (gercek model + kota):
    python -m pytest tests/live/test_seviye1_native.py --live -q
"""
import pytest


def test_seviye1_8native_protokol(rapor):
    from tests.live import kosucu
    sonuc = kosucu.kos_tumu()
    for ad, (durum, mesaj) in sonuc.items():
        rapor("seviye1_%s" % ad, {"durum": durum, "mesaj": mesaj[:200]})

    kirmizi = [ad for ad, (d, _) in sonuc.items() if d == "KIRMIZI"]
    assert not kirmizi, (
        "Duzey 1 KIRMIZI saglayicilar: %s — kabul plani 8/8 YESIL ister "
        "(SKIP yalniz anahtarsiz icin)" % ", ".join(kirmizi))
