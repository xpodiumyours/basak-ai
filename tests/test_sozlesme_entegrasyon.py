import json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import chat as c

def test_kapidan_passthrough():
    h = "hi"
    t, r = c._kapidan_gecir(h, [])
    assert t == h
    assert r == []

def test_yapi_bos():
    class F:
        def cevapla(self, *a, **kw):
            return ({}, "x")
    assert c._yapi_kwargi(F()) == {}

def test_mod_kapali():
    assert c._SOZLESME_MODU == "kapali"

def test_tool_terminal():
    from tools.definitions import TOOLS
    assert any(t["function"]["name"] == "terminal_exec" for t in TOOLS)
