"""tests/test_orkestra_yol.py — meta-orkestra ana sohbet yolunda kapalıdır.

Eski ayar anahtarı dosyada bulunsa bile kullanıcı mesajı jüri/orkestra yoluna
yönlendirilmez. Modül yalnız geriye uyumluluk için kod tabanında kalabilir.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chat as c


def test_ayar_degeri_orkestrayi_acamaz(monkeypatch, tmp_path):
    import _chat_legacy as _cl
    ayarlar = tmp_path / "ayarlar.json"
    monkeypatch.setattr(_cl, "SETTINGS_FILE", str(ayarlar))

    for deger in (False, True):
        ayarlar.write_text(json.dumps({"orkestra_ana_yol": deger}),
                           encoding="utf-8")
        assert c.orkestra_aktif_mi() is False


def test_golge_ve_juri_de_kalici_kapali(monkeypatch, tmp_path):
    import _chat_legacy as _cl
    ayarlar = tmp_path / "ayarlar.json"
    ayarlar.write_text(json.dumps({
        "orkestra_ana_yol": True,
        "golge_mod": True,
        "juri": True,
    }), encoding="utf-8")
    monkeypatch.setattr(_cl, "SETTINGS_FILE", str(ayarlar))

    assert c.orkestra_aktif_mi() is False
    assert c.golge_mod_aktif_mi() is False
    assert c.juri_acik_mi() is False


def test_mesaj_isle_orkestra_yolunu_cagirmadan_normal_akisa_girer(monkeypatch):
    import _chat_legacy as legacy

    monkeypatch.setattr(legacy, "yukle", lambda *a, **k: {})
    monkeypatch.setattr(legacy, "kaydet", lambda *a, **k: None)
    monkeypatch.setattr(legacy, "_save_and_reply", lambda *a, **k: None)
    monkeypatch.setattr(legacy, "_hafiza_al", lambda: None)
    monkeypatch.setattr(legacy, "_ilgili_anilar", lambda *a, **k: [])

    def patlak(*a, **k):
        raise AssertionError("orkestra ana yolu çağrılmamalı")

    monkeypatch.setattr(legacy, "mesaj_isle_orkestra", patlak)

    class SahteBrain:
        def yerel_modeller(self):
            return []

        def bulut_musait(self):
            return True

        def _bulut_zinciri(self):
            return [("groq", object())]

        def cevapla(self, messages, model, tools=None, **kwargs):
            return {"content": "tamam"}, "groq"

    c.mesaj_isle("merhaba", SahteBrain(), "ESKI-PROMPT",
                 lambda code: None, None)
