"""tests/test_groq_uyumluluk.py — Groq mesaj uyumluluk kilidi.

2026-09-16 canli kanit: arac dongusu muhakemeyi assistant mesajinda
korur (P0); Groq `reasoning_content` alanini 400 ile reddeder
("for 'role:assistant' ... 'reasoning_content' is unsupported").
Groq'a giden kopyadan bu alanlar cikar; zincir/yant bozulmaz.
"""

import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _sahte_istemci(yakalanan):
    ileti = types.SimpleNamespace(tool_calls=None, content="tamam")
    secim = types.SimpleNamespace(message=ileti)
    yanit = types.SimpleNamespace(choices=[secim])

    class _Comp:
        def create(self, **kw):
            yakalanan.update(kw)
            return yanit

    return types.SimpleNamespace(
        chat=types.SimpleNamespace(completions=_Comp()))


class TestGroqUyumluluk:
    def test_muhakeme_alanlari_groqa_gitmez(self):
        from brain.groq import GroqClient
        istemci = GroqClient.__new__(GroqClient)
        istemci.model = "openai/gpt-oss-20b"
        yakalanan = {}
        istemci.client = _sahte_istemci(yakalanan)
        istemci.cevapla([
            {"role": "user", "content": "merhaba"},
            {"role": "assistant", "content": "",
             "tool_calls": [{"id": "c1", "type": "function",
                             "function": {"name": "list_files",
                                          "arguments": "{}"}}],
             "reasoning_content": "gizli dusunme",
             "thinking": "dusun"},
        ])
        giden = yakalanan["messages"]
        assert len(giden) == 2
        for m in giden:
            for alan in ("reasoning_content", "reasoning",
                         "reasoning_details", "reasoning_text",
                         "thinking"):
                assert alan not in m, "%s sizdi" % alan
        assert giden[1]["tool_calls"][0]["function"]["name"] == "list_files"

    def test_girilen_liste_degismez(self):
        from brain.groq import _groq_mesajlari
        ham = [{"role": "assistant", "content": "",
                "reasoning_content": "x"}]
        _groq_mesajlari(ham)
        assert ham[0]["reasoning_content"] == "x"
