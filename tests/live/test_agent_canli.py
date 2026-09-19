"""tests/live/test_agent_canli.py — gercek sohbet ajan kabul sinavi.

Bu dosya GERCEK model/kota kullanir. Normal CI'da atlanir; yalniz
`pytest tests/live/test_agent_canli.py --live -q` ile calisir.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))


def _ui_toplayici():
    olaylar = []

    def cb(code):
        olaylar.append(code)
    return olaylar, cb


def test_gercek_model_simdi_aracini_kendi_secer(monkeypatch, tmp_path, rapor):
    """Dogal Turkce istek -> LLM karari -> gercek simdi araci -> final."""
    from brain import Brain
    from chat.flow import mesaj_isle
    from chat import context as ctx
    from tools import TOOLS
    import tools as tools_mod

    monkeypatch.setattr(ctx, "HISTORY_FILE", str(tmp_path / "gecmis.json"))
    monkeypatch.setattr(ctx, "SETTINGS_FILE", str(tmp_path / "ayar.json"))
    monkeypatch.setattr(ctx, "_hafiza", False)

    b = Brain()
    if not b.ajan_musait():
        pytest.skip("Ajan protokolu destekli ucretsiz model bagli degil")

    gercek_calistir = tools_mod.calistir
    kosulan = []

    def kayitli_calistir(ad, args):
        kosulan.append(ad)
        return gercek_calistir(ad, args)

    monkeypatch.setattr(tools_mod, "calistir", kayitli_calistir)

    olaylar, cb = _ui_toplayici()
    mesaj_isle(
        "Şu an tarih ve saati kontrol et ve sonucu bana söyle.",
        b,
        "Sen Başak'sın. Türkçe konuş.",
        cb,
        TOOLS,
    )

    bitis = [x for x in olaylar if x.startswith("BasakUI.bitir(")]
    rapor("ajan_simdi", {
        "kosulan_araclar": kosulan,
        "bitis_var": bool(bitis),
        "olay_sayisi": len(olaylar),
    })
    assert "simdi" in kosulan, (
        "Model dis gercek gerektiren istekte simdi aracini kullanmadi")
    assert bitis, "Ajan gercek arac sonucunu final cevaba baglamadi"


def test_gercek_model_sohbette_gercek_arac_calistirmaz(
        monkeypatch, tmp_path, rapor):
    """Salt sohbet, gereksiz dunya araci calistirmadan son_cevap ile biter."""
    from brain import Brain
    from chat.flow import mesaj_isle
    from chat import context as ctx
    from tools import TOOLS
    import tools as tools_mod

    monkeypatch.setattr(ctx, "HISTORY_FILE", str(tmp_path / "gecmis2.json"))
    monkeypatch.setattr(ctx, "SETTINGS_FILE", str(tmp_path / "ayar2.json"))
    monkeypatch.setattr(ctx, "_hafiza", False)

    b = Brain()
    if not b.ajan_musait():
        pytest.skip("Ajan protokolu destekli ucretsiz model bagli degil")

    gercek_calistir = tools_mod.calistir
    kosulan = []

    def kayitli_calistir(ad, args):
        kosulan.append(ad)
        return gercek_calistir(ad, args)

    monkeypatch.setattr(tools_mod, "calistir", kayitli_calistir)

    olaylar, cb = _ui_toplayici()
    mesaj_isle(
        "Sadece kısa bir selam ver. Dış bilgiye veya bir işleme ihtiyacın yok.",
        b,
        "Sen Başak'sın. Türkçe konuş.",
        cb,
        TOOLS,
    )

    bitis = [x for x in olaylar if x.startswith("BasakUI.bitir(")]
    rapor("ajan_sohbet", {
        "kosulan_araclar": kosulan,
        "bitis_var": bool(bitis),
        "olay_sayisi": len(olaylar),
    })
    assert kosulan == [], "Salt sohbette gereksiz gercek arac calisti"
    assert bitis, "Salt sohbet son_cevap ile tamamlanmadi"
