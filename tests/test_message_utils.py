"""tests/test_message_utils.py — Ileti temizleme gerileme testleri.

2026-09-10: cok aracli tur sonrasi "sequence item 60: expected str
instance, int found" hatasi alindi. Bazi saglayicilar content'i
karisik blok listesi doner (sayi/None icerebilir) — temizleyici
hepsini stringe cevirmelidir.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.message_utils import mesajlari_temizle


class TestKarisikBloklar:
    def test_sayili_blok_patlamaz(self):
        bloklar = [{"type": "text", "text": "parca %d" % i} for i in range(60)]
        bloklar.append({"type": "text", "text": 12345})
        bloklar.append({"type": "text"})
        out = mesajlari_temizle([{"role": "assistant", "content": bloklar}])
        assert isinstance(out[0]["content"], str)
        assert "parca 0" in out[0]["content"]
        assert "12345" in out[0]["content"]

    def test_duz_string_aynen_gecer(self):
        out = mesajlari_temizle([{"role": "user", "content": "selam"}])
        assert out[0]["content"] == "selam"

    def test_none_bos_string(self):
        out = mesajlari_temizle([{"role": "user", "content": None}])
        assert out[0]["content"] == ""

    def test_tool_alanlari_korunur(self):
        out = mesajlari_temizle([{"role": "assistant", "content": "",
                                  "tool_calls": [{"id": "1"}],
                                  "tool_call_id": "1"}])
        assert out[0]["tool_calls"] == [{"id": "1"}]
        assert out[0]["tool_call_id"] == "1"
