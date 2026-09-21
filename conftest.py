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


# ── Gerçek veri koruması (2026-09-22) ─────────────────────────────────
# Ölçüm: `data/audit/audit.log`'daki 321 satırın 169'u test koşularından
# geliyordu (0.0 sn'lik satırlar). O günlük "hangi sağlayıcı iyi" ve
# "bugün kaç istek harcadım" kararının kaynağı; test gürültüsü kararı
# bozar. Bu yüzden her test KENDİ geçici dosyasına yazar.


@pytest.fixture(scope="session")
def _izole_olcum_dizini(tmp_path_factory):
    """Ölçüm dosyaları için TEK geçici dizin (test başına yeniden kurulmaz).

    İzolasyonun amacı gerçek veriyi korumak; testlerin birbirinden değil.
    Tek dizin kullanmak paketi gereksiz yavaşlatmaz.
    """
    return tmp_path_factory.mktemp("izole-olcum")


@pytest.fixture(scope="session")
def _izole_stats(_izole_olcum_dizini):
    import brain.stats as stats_modulu
    return stats_modulu.ModelIstatistik(
        db_yolu=str(_izole_olcum_dizini / "model_stats.db"))


@pytest.fixture(autouse=True)
def _gercek_veriyi_koru(_izole_olcum_dizini, _izole_stats, monkeypatch):
    """Testler gerçek denetim günlüğüne ve kota sayacına YAZMAZ."""
    import brain.brain as beyin_modulu
    import brain.stats as stats_modulu

    monkeypatch.setattr(beyin_modulu, "AUDIT_DOSYASI",
                        str(_izole_olcum_dizini / "audit.log"))
    # DİKKAT: ModelIstatistik varsayılan DB yolunu tanım anında sabitler;
    # bu yüzden DB_YOLU'yu yamamak yetmez — tekillik doğrudan geçici
    # veritabanıyla kurulur.
    monkeypatch.setattr(stats_modulu, "_stats", _izole_stats)
    yield
