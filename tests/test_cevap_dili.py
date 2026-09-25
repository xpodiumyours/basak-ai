"""tests/test_cevap_dili.py — cevap dili sistem talimatinda acikca soylenir.

Dayanak: Anthropic cok dilli destek belgesi (hedef dil sistem talimatinda
acikca belirtilir). Satir yalniz dili soyler; arac/niyet secmez.
"""

from chat.prompts import DIL_SATIRI, kisilik_blogu


def test_her_kisilik_bloğu_dil_satirini_tasir(monkeypatch):
    import chat.kimlik as kimlik
    monkeypatch.setattr(kimlik, "gorunur_ad", lambda kid: "Ayse")
    for blok in (
        kisilik_blogu(misafir=True),
        kisilik_blogu(kimlik.VARSAYILAN_KULLANICI),
        kisilik_blogu("u12"),
        kisilik_blogu("ayse"),
    ):
        assert DIL_SATIRI in blok


def test_dil_satiri_arac_veya_niyet_secmez():
    from tools.definitions import TANINMIS_TOOLLAR
    for ad in TANINMIS_TOOLLAR:
        assert ad not in DIL_SATIRI
    assert "Türkçe" in DIL_SATIRI
