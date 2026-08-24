"""tests/live/test_boot.py — Açılış provası (GERÇEK ortam).

CANLI-KAPISI.md kabulü: Brain açılır, Ollama/bulut durumu ölçülür,
Api.boot() sözlüğü sağlıklı döner, hafıza DB'si düzgün kapanır ve
yeniden açılabilir.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))


def test_beyin_acilisi_ve_zincir(rapor):
    from brain import Brain
    b = Brain()
    yerel = b.yerel_modeller()
    bulutlar = [ad for ad, _ in b._bulut_zinciri()]
    rapor("acilis", {"yerel": yerel, "bulut": bulutlar})
    # Ortam sağlıklıysa en az bir beyin kaynağı olmalı
    assert yerel or bulutlar, "Ne Ollama ne bulut zinciri ayakta"


def test_api_boot_sozlugu(rapor):
    """UI olmadan Api katmanının açılış sözleşmesi."""
    import basak_app
    api = basak_app.Api()
    durum = api.boot()
    rapor("api_boot", {k: (v if isinstance(v, (bool, int, str, list))
                            else str(v)[:60])
                       for k, v in durum.items()})
    assert isinstance(durum, dict)
    assert "ok" in durum and "models" in durum and "cloud" in durum
    if durum["models"] or durum["cloud"]:
        assert durum["ok"] is True


def test_hafiza_db_ac_kapan_yeniden_ac(tmp_path, rapor):
    from memory.engine import HafizaMotoru
    yol = str(tmp_path / "canli.db")

    m1 = HafizaMotoru(db_yolu=yol, embed_fn=lambda t: None)
    m1.episodik_kaydet("acilis provasi sorusu", "cevap")
    ilk_sayi = m1.say()
    m1.kapat()

    # Kapatma gerçek mi?
    from sqlite3 import ProgrammingError
    with pytest.raises(ProgrammingError):
        m1.conn.execute("SELECT 1")

    m2 = HafizaMotoru(db_yolu=yol, embed_fn=lambda t: None)
    assert m2.say() == ilk_sayi, "kapat-aç arasında kayıt kayboldu"
    m2.kapat()
    rapor("db_yasam_dongusu", {"kayit": ilk_sayi, "db": yol})
