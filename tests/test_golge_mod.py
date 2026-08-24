"""tests/test_golge_mod.py — Gölge mod testleri.

İlke: gölge mod açıkken kullanıcıya dönen cevap ESKİ yoldan gelir;
orkestra yolu sessizce koşar ve benzerlik data/orkestra_golge.log'a
yazılır. Gölgede koşum geçmişe/hafızaya YAZMAZ.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

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
    def test_golge_mod_anahtari(self, monkeypatch, tmp_path):
        ayarlar = tmp_path / "a.json"
        ayarlar.write_text('{"golge_mod": true}', encoding="utf-8")
        monkeypatch.setattr(c, "SETTINGS_FILE", str(ayarlar))
        assert c.golge_mod_aktif_mi() is True

        ayarlar.write_text("{}", encoding="utf-8")
        assert c.golge_mod_aktif_mi() is False

        ayarlar.unlink()
        assert c.golge_mod_aktif_mi() is False


class TestSessizKosum:
    def test_golgede_gecmise_ve_hafizaya_yazilmaz(self, monkeypatch,
                                                  tmp_path):
        """GÖLGE MOD'un temizliği: yan yana ölçüm kalıcı iz bırakmamalı."""
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
        assert not gecmis.exists()   # geçmişe dokunulmadı


class TestEntegrasyon:
    def test_mesaj_sonrasi_golge_kosar(self, monkeypatch, tmp_path):
        """mesaj_isle sonrası golge açıksa golge_kos BİR KEZ çağrılır ve
        eski yolun cevabı ona taşınır."""
        import basak_app

        kosuldu = []

        def sahte_mesaj_isle(text, brain, sp, js, tools):
            with open(basak_app.HISTORY_FILE, "w", encoding="utf-8") as f:
                json.dump([
                    {"role": "user", "content": text},
                    {"role": "assistant", "content": "eski yol cevabi"},
                ], f, ensure_ascii=False)

        monkeypatch.setattr(basak_app, "HISTORY_FILE",
                            str(tmp_path / "g.json"))
        monkeypatch.setattr(basak_app, "mesaj_isle", sahte_mesaj_isle)

        import chat as cc
        monkeypatch.setattr(cc, "golge_mod_aktif_mi", lambda: True)
        monkeypatch.setattr(cc, "golge_kos",
                            lambda text, brain, eski:
                            kosuldu.append((text, eski)))

        api = basak_app.Api()
        api._chat("deneme mesaji")

        assert len(kosuldu) == 1
        assert kosuldu[0][0] == "deneme mesaji"
        assert kosuldu[0][1] == "eski yol cevabi"

    def test_kapaliyken_hicbir_sey_kosmaz(self, monkeypatch, tmp_path):
        import basak_app

        kosuldu = []
        monkeypatch.setattr(basak_app, "HISTORY_FILE",
                            str(tmp_path / "g.json"))

        import chat as cc
        monkeypatch.setattr(cc, "golge_mod_aktif_mi", lambda: False)
        monkeypatch.setattr(cc, "golge_kos",
                            lambda *a, **kw: kosuldu.append(1))

        api = basak_app.Api()
        api._chat("selam")
        assert kosuldu == []
