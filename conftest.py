"""conftest.py — canlı hat anahtarı (--live).

Kural (CANLI-KAPISI.md): tests/live/ altındaki testler GERÇEK modeller,
GERÇEK ağ ve kota kullanır. Normal `pytest` koşusunda ATLANIRLAR;
yalnız `pytest tests/live --live` ile çalışırlar.
"""

import os

import pytest


def pytest_addoption(parser):
    parser.addoption("--live", action="store_true", default=False,
                     help="Canlı hat testlerini koştur "
                          "(gerçek model/kota kullanır)")


def pytest_collection_modifyitems(config, items):
    if config.getoption("--live"):
        return
    skip = pytest.mark.skip(reason="canlı hat — --live gerekli")
    for item in items:
        yol = str(item.fspath).replace("\\", "/").lower()
        if "/tests/live/" in yol:
            item.add_marker(skip)
