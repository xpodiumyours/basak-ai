"""tests/test_golge_mod.py — gölge model ana uygulamada devre dışıdır.

Eski yardımcı fonksiyonlar geriye uyumluluk için kalabilir; fakat normal Başak
çalışması kullanıcı cevabından sonra ikinci model/orkestra çağrısı yapmaz.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chat as c


class TestBenzerlik:
    def test_ayni_metin_1(self):
        assert c._benzerlik("ayni cevap metni", "AYNI CEVAP METNI") == 1.0

    def test_farkli_metin_0(self):
        assert c._benzerlik("kirmizi elma agaci",
                            "mavi araba yolda gidiyor") == 0.0

    def test_bos_taraf_0(self):
        assert c._benzerlik("", "bir sey") == 0.0


class TestAnahtar:
    def test_golge_mod_ayarla_acilamaz(self, monkeypatch, tmp_path):
        ayarlar = tmp_path / "a.json"
        ayarlar.write_text('{"golge_mod": true}', encoding="utf-8")
        import _chat_legacy as _cl
        monkeypatch.setattr(_cl, "SETTINGS_FILE", str(ayarlar))
        assert c.golge_mod_aktif_mi() is False


class TestSessizKosum:
    def test_legacy_orkestra_yazmasiz_cagrilabilse_de_ana_yola_bagli_degil(
            self, monkeypatch, tmp_path):
        gecmis = tmp_path / "gecmis.json"
        monkeypatch.setattr(c, "HISTORY_FILE", str(gecmis))
        monkeypatch.setattr(c, "_hafiza", False)

        class SahteBrain:
            def yerel_modeller(self):
                return []

            def bulut_musait(self):
                return True

            def cevapla(self, messages, model=None, tools=None):
                return {"content": "gölge cevap"}, "sahte"

        kutu = {"reply": []}

        def cb(code):
            if code.startswith("BasakUI.reply("):
                ic = code[code.index("(") + 1: code.rindex(")")]
                kutu["reply"].append(json.loads("[" + ic + "]")[0])

        c.mesaj_isle_orkestra("merhaba", SahteBrain(), "SYS", cb, None,
                              kaydet_acik=False)
        assert kutu["reply"] == ["gölge cevap"]
        assert not gecmis.exists()


class TestEntegrasyon:
    def test_normal_chat_golge_kosmaz(self, monkeypatch, tmp_path):
        import basak_app

        kosuldu = []

        def sahte_mesaj_isle(text, brain, sp, js, tools):
            with open(basak_app.HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump([
                    {"role": "user", "content": text},
                    {"role": "assistant", "content": "normal cevap"},
                ], f, ensure_ascii=False)

        monkeypatch.setattr(basak_app, "HISTORY_FILE",
                            str(tmp_path / "g.json"))
        monkeypatch.setattr(basak_app, "mesaj_isle", sahte_mesaj_isle)

        import chat as cc
        # Uygulama bu fonksiyonu çağırsa bile güncel sözleşme False döndürür.
        monkeypatch.setattr(cc, "golge_kos",
                            lambda *a, **kw: kosuldu.append(1))

        api = basak_app.Api()
        api._chat("selam")
        assert kosuldu == []
