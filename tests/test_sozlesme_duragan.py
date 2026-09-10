"""tests/test_sozlesme_duragan.py — FAZ4-2 sozlesme karari kilidi.

2026-08-25 Casper karari + FAZ 1 A/B hukum + FAZ4-1 olcumu: guclu
model sarti saglanana kadar sozlesme kapisi DURAGAN kalir — yari
acik kapıdan beterdir (hem kota yer hem davranis degistirir).
Bu test duraganligi kilitler: kapı kimliktir, bayrak kapalidir.
Sart saglaninca bu dosya kaldirilip FAZ 1.4e A/B kosulur.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chat  # once tam paket (dairesel import onlemi)


class TestSozlesmeDuragan:
    def test_bayrak_kapali(self):
        import _chat_legacy as _L
        assert _L._SOZLESME_MODU == "kapali"

    def test_kapi_kimliktir(self):
        import chat as _c
        metin = "Merhaba Casper [B] olcum yok"
        temiz, rapor = _c._kapidan_gecir(metin, [])
        assert temiz == metin and rapor == []

    def test_yapi_zorlamasi_yok(self):
        import _chat_legacy as _L

        class Sahte:
            pass
        assert _L._yapi_kwargi(Sahte()) == {}
