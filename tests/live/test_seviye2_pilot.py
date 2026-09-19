"""tests/live/test_seviye2_pilot.py — Duzey 2 PILOT kabul testi (8x8=64).

Yalniz --live ile kosar (gercek model + kota):
    python -m pytest tests/live/test_seviye2_pilot.py --live -q

Kapsam: 8 saglayici x 8 temsilci arac (2 kontrol + 6 temsilci).
Tam 416'ya gecis ancak pilot YESIL iken olur (kabul plani sirasi).
"""
import pytest


def test_seviye2_pilot_64hucre(rapor):
    from tests.live import matris_kosucu
    ozet = matris_kosucu.kos_tumu(pilot=True)
    rapor("seviye2_pilot", ozet)

    # SKIP yalniz anahtarsiz saglayici icin meşru (cloudflare, cohere).
    kirmizi = [s for s, k in ozet["saglayicilar"].items()
               if k.get("KIRMIZI")]
    assert not kirmizi, (
        "Duzey 2 pilot KIRMIZI saglayicilar: %s — kabul planina gore "
        "pilot YESIL olmadan tam 416'ya gecilmez" % ", ".join(kirmizi))

    # Anahtari olan saglayicinin hucreleri SKIP olamaz — SKIP tahmin
    # doldurmak icin degil, anahtar yokluğu icindir.
    from tests.live import kosucu
    sahte_skip = [s for s, k in ozet["saglayicilar"].items()
                  if k.get("SKIP") and kosucu._anahtarlar(s) is not None]
    assert not sahte_skip, (
        "Anahtari olan saglayici SKIP yazmis (tahmin doldurma yasaği): %s"
        % ", ".join(sahte_skip))
