"""tests/test_cohere_icerik.py — Cohere karisik icerik bloklari.

2026-09-10 canli sinavda yakalandi: bazi saglayicilar icerik
parcalarinda sayi/None doner; cohere.py'deki ""join patliyordu
("sequence item N: expected str instance"). message_utils.py'deki
kural burada da gecerli: hepsi zorla stringe cevrilir.
"""

import os
import sys
import types

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _istemci(parcalar):
    from brain import cohere as _cohere

    class SahteMesaj:
        def __init__(self):
            self.content = parcalar
            self.tool_calls = None

    class SahteResp:
        def __init__(self):
            self.message = SahteMesaj()

    class SahteClient:
        def chat(self, **kwargs):
            return SahteResp()

    istemci = _cohere.CohereClient.__new__(_cohere.CohereClient)
    istemci.client = SahteClient()
    istemci.model = "command-a-03-2025"
    return istemci


class TestCohereIcerik:
    def test_karisik_bloklar_patlamaz(self):
        blok1 = types.SimpleNamespace(text="merhaba ")
        blok2 = types.SimpleNamespace(text=42)
        blok3 = types.SimpleNamespace(text=None)
        blok4 = types.SimpleNamespace(baska="yok")
        sonuc = _istemci([blok1, blok2, blok3, blok4]).cevapla(
            [{"role": "user", "content": "selam"}])
        assert sonuc["content"] == "merhaba 42"

    def test_duz_metin_aynen_gecer(self):
        sonuc = _istemci("duz yazi").cevapla(
            [{"role": "user", "content": "selam"}])
        assert sonuc["content"] == "duz yazi"

    def test_bos_icerik_bos_doner(self):
        from brain import cohere as _cohere

        class SahteMesaj:
            content = ""
            tool_calls = None

        class SahteResp:
            message = SahteMesaj()

        class SahteClient:
            def chat(self, **kwargs):
                return SahteResp()

        istemci = _cohere.CohereClient.__new__(_cohere.CohereClient)
        istemci.client = SahteClient()
        istemci.model = "command-a-03-2025"
        sonuc = istemci.cevapla([{"role": "user", "content": "selam"}])
        assert sonuc["content"] == ""
