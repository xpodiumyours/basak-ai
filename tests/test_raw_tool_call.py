"""tests/test_raw_tool_call.py — Raw tool call parser testleri (BUG #1 fix).

Kucuk modeller (qwen2.5:3b vb.) tool calling API'sini dogru kullanamaz,
fonksiyon cagrisini duz metin olarak dondurur. Bu testler parser'in
dogru yakaladigini ve false positive uretmedigini dogrular.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest
import chat as c


class TestRawToolCallParser:
    """_ham_tool_call_ayir() ve _raw_tool_call_var_mi() testleri."""

    def test_klasik_kose_parantezli(self):
        """[list_files](folder="belgeler") — en yaygin desen."""
        sonuc = c._ham_tool_call_ayir('[list_files](folder="belgeler")')
        assert len(sonuc) == 1
        assert sonuc[0][0] == "list_files"
        assert sonuc[0][1] == {"folder": "belgeler"}

    def test_kose_parantezsiz(self):
        """list_files(folder="belgeler") — model bazen parantez koymaz."""
        sonuc = c._ham_tool_call_ayir('list_files(folder="belgeler")')
        assert len(sonuc) == 1
        assert sonuc[0] == ("list_files", {"folder": "belgeler"})

    def test_tek_tirnakli(self):
        """list_files(folder='masaustu') — tek tirnak kullanimi."""
        sonuc = c._ham_tool_call_ayir("list_files(folder='masaustu')")
        assert sonuc[0] == ("list_files", {"folder": "masaustu"})

    def test_coklu_parametre(self):
        """save_note(title="baslik", content="icerik") — iki parametre."""
        sonuc = c._ham_tool_call_ayir(
            '[save_note](title="baslik", content="icerik")'
        )
        assert len(sonuc) == 1
        assert sonuc[0] == ("save_note", {"title": "baslik", "content": "icerik"})

    def test_parametresiz_tool(self):
        """[list_tasks]() — parametresiz cagri."""
        sonuc = c._ham_tool_call_ayir("[list_tasks]()")
        assert len(sonuc) == 1
        assert sonuc[0] == ("list_tasks", {})

    def test_coklu_tool_call(self):
        """Birden fazla tool call ayni metinde."""
        metin = '[read_file](path="test.md") sonra [list_files](folder="knowledge")'
        sonuc = c._ham_tool_call_ayir(metin)
        assert len(sonuc) == 2
        assert sonuc[0][0] == "read_file"
        assert sonuc[1][0] == "list_files"

    def test_ecran_gorusu_ornegi(self):
        """Ekran goruntusundeki ornek: buyuk model ciktisi ile karisik."""
        metin = (
            "2 gun sonra: Dogum: 26 Agustos 1995\n"
            '[list_files](folder="belgeler")'
        )
        sonuc = c._ham_tool_call_ayir(metin)
        assert len(sonuc) == 1
        assert sonuc[0] == ("list_files", {"folder": "belgeler"})

    def test_bilinmeyen_tool_yakalanmaz(self):
        """Bilinmeyen tool ismi yakalanmamali (false positive onlemi)."""
        sonuc = c._ham_tool_call_ayir('[bilinmeyen_tool](x="y")')
        assert len(sonuc) == 0

    def test_normal_sohbet_false_positive_yok(self):
        """Normal sohbet metninde false positive olmamali."""
        metin = "Merhaba, nasilsin? Bugun hava guzel."
        assert c._ham_tool_call_ayir(metin) == []

    def test_bos_metin(self):
        """Bos metin."""
        assert c._ham_tool_call_ayir("") == []
        assert c._ham_tool_call_ayir(None) == []

    def test_var_mi_dogrulama(self):
        """_raw_tool_call_var_mi hizli kontrol."""
        assert c._raw_tool_call_var_mi('[list_files](folder="belgeler")')
        assert c._raw_tool_call_var_mi('list_files(folder="belgeler")')
        assert not c._raw_tool_call_var_mi("normal metin")
        assert not c._raw_tool_call_var_mi("")
        assert not c._raw_tool_call_var_mi(None)

    def test_tum_taninmis_toollar(self):
        """Tum taninmis toollar yakalanabilmeli."""
        for tool in c._TANINMIS_TOOLLAR:
            metin = '[%s](x="y")' % tool
            sonuc = c._ham_tool_call_ayir(metin)
            assert len(sonuc) == 1, "%s yakalanamadi" % tool
            assert sonuc[0][0] == tool


class TestRawToolCallEntegrasyon:
    """Raw tool call'un mesaj_isle'de dogru calistirilmasi."""

    def test_raw_tool_call_calistirilir(self, monkeypatch, tmp_path):
        """Model text olarak list_files dondurse bile tool calistirilmali."""
        from memory.engine import HafizaMotoru

        motor = HafizaMotoru(
            db_yolu=str(tmp_path / "test.db"), embed_fn=lambda m: None
        )
        monkeypatch.setattr(c, "_hafiza", motor)

        gecmis = str(tmp_path / "gecmis.json")
        ayarlar = str(tmp_path / "ayarlar.json")
        monkeypatch.setattr(c, "HISTORY_FILE", gecmis)
        monkeypatch.setattr(c, "SETTINGS_FILE", ayarlar)

        kosanlar = []

        def sahte_calistir(ad, args, *a, **kw):
            kosanlar.append((ad, args))
            return {"result": "%s OK" % ad}

        monkeypatch.setattr("tools.calistir", sahte_calistir)

        # Brain: tool dondurmuyor, duz metin olarak raw tool call yaziyor
        class RawTextBrain:
            def yerel_modeller(self):
                return ["sahte"]

            def bulut_musait(self):
                return True

            def cevapla(self, messages, yerel_model, tools=None, **kw):
                # dict dondurmek zorundayiz (brain cevaplari dict)
                return ({
                    "content": '[list_files](folder="belgeler")',
                    "tool_calls": None,
                }, "sahte")

        cb_calls = []

        def cb(code):
            cb_calls.append(code)

        tools = [
            {
                "type": "function",
                "function": {
                    "name": "list_files",
                    "description": "test",
                    "parameters": {
                        "type": "object",
                        "properties": {"folder": {"type": "string"}},
                    },
                },
            }
        ]

        c.mesaj_isle("dosyalari listele", RawTextBrain(), "SYS", cb, tools)

        # Tool calistirilmis olmali
        assert len(kosanlar) == 1
        assert kosanlar[0][0] == "list_files"

        # Kullaniciya cevap gonderilmis olmali
        reply_calls = [x for x in cb_calls if x.startswith("BasakUI.reply")]
        assert len(reply_calls) == 1
