"""tests/live/conftest.py — canlı hat ortak tesisatı."""

import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

BASE = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
RAPOR_KOK = os.path.join(BASE, "data", "canli-rapor")


@pytest.fixture(scope="session")
def rapor():
    """Her canlı test sonucunu data/canli-rapor/ altına JSON yazar."""
    def yaz(ad, veri):
        kayit = {"test": ad, "zaman": time.strftime("%Y-%m-%d %H:%M:%S"),
                 **veri}
        try:
            os.makedirs(RAPOR_KOK, exist_ok=True)
            dosya = os.path.join(
                RAPOR_KOK, "%s_%s.json"
                % (time.strftime("%Y%m%d-%H%M%S"), ad))
            with open(dosya, "w", encoding="utf-8") as f:
                json.dump(kayit, f, ensure_ascii=False, indent=2)
        except OSError:
            pass
        return kayit
    return yaz
