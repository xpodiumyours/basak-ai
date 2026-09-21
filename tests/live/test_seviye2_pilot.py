"""tests/live/test_seviye2_pilot.py — Duzey 2 PILOT kabul testi (7x8=56).

Yalniz --live ile kosar (gercek model + kota):
    python -m pytest tests/live/test_seviye2_pilot.py --live -q

Kapsam: 7 saglayici x 8 temsilci arac (2 kontrol + 6 temsilci) = 56 hucre.
Kapsam = elde anahtari olan saglayicilar (matris_kosucu.KAPSAM).
Tam 364'e gecis ancak pilot YESIL iken olur (kabul plani sirasi).
"""
import pytest


def test_seviye2_pilot_56hucre(rapor):
    from tests.live import matris_kosucu
    ozet = matris_kosucu.kos_tumu(pilot=True)
    rapor("seviye2_pilot", ozet)

    # SKIP yalniz kapsam icindeki bir saglayici anahtarini kaybederse
    # mesrudur; kapsam disi saglayici zaten kosuma hic girmez.
    kirmizi = [s for s, k in ozet["saglayicilar"].items()
               if k.get("KIRMIZI")]
    assert not kirmizi, (
        "Duzey 2 pilot KIRMIZI saglayicilar: %s — kabul planina gore "
        "pilot YESIL olmadan tam 364'e gecilmez" % ", ".join(kirmizi))

    # Anahtari olan saglayicinin hucreleri SKIP olamaz — SKIP tahmin
    # doldurmak icin degil, anahtar yokluğu icindir.
    from tests.live import kosucu
    sahte_skip = [s for s, k in ozet["saglayicilar"].items()
                  if k.get("SKIP") and kosucu._anahtarlar(s) is not None]
    assert not sahte_skip, (
        "Anahtari olan saglayici SKIP yazmis (tahmin doldurma yasaği): %s"
        % ", ".join(sahte_skip))
