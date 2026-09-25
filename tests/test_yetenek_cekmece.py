"""tests/test_yetenek_cekmece.py — yetenek alanlari (AGENTS.md §0).

Olculen davranis:
- ilk turda modele yalniz yetenek_ac sunulur;
- tek cagrida birden fazla alan acilabilir;
- acilan alan run boyunca acik kalir (yeni alan acmak oncekini kapatmaz);
- acilmamis alanin araci calismaz; bilinmeyen alan hicbir sey acmaz.
Resmi dayanak: OpenAI tool search/namespace ve Anthropic tool search
(yuklenen araclar sonraki turlarda tekrar yuklenmeden kullanilir).
"""

import json

from chat.agent_protocol import YETENEK_AC_ADI, YETENEK_ALANLARI
from tools.definitions import TOOLS


def _cagri(ad, args, cid):
    return {"id": cid, "type": "function",
            "function": {"name": ad, "arguments": json.dumps(args)}}


def _adlar(tools):
    return {(t.get("function") or {}).get("name") for t in (tools or [])}


class SenaryoBeyni:
    """Her turda sunulan araclari kaydeder, sirayla hazir kararlari doner."""

    def __init__(self, kararlar):
        self.kararlar = list(kararlar)
        self.gorulen_araclar = []

    def cevapla_yayin(self, *a, **k):
        from brain.yayin import SonHata
        raise SonHata("testte akis yok")
        yield  # pragma: no cover

    def cevapla(self, mesajlar, model, tools=None, **kwargs):
        self.gorulen_araclar.append(_adlar(tools))
        karar = self.kararlar.pop(0)
        if isinstance(karar, list):
            return {"content": "", "tool_calls": karar}, "groq"
        return {"content": karar}, "groq"


def _kos(ilk_cagrilar, kararlar):
    from chat.agent_protocol import baslangic_araclari
    from chat.tools import arac_dongusu

    calisan = []

    def calistir(ad, args):
        calisan.append(ad)
        return {"result": "tamam-%s" % ad}

    beyin = SenaryoBeyni(kararlar)
    cevap, kosan = arac_dongusu(
        ilk_cagrilar, [{"role": "user", "content": "x"}], beyin, None,
        lambda kod: None, calistir, tools=baslangic_araclari(),
        katalog=TOOLS)
    return cevap, kosan, calisan, beyin


def test_ilk_turda_yalniz_yetenek_ac_sunulur():
    from chat.agent_protocol import baslangic_araclari
    assert _adlar(baslangic_araclari()) == {YETENEK_AC_ADI}


def test_tek_cagrida_birden_fazla_alan_acilir():
    cevap, kosan, calisan, beyin = _kos(
        [_cagri(YETENEK_AC_ADI, {"alanlar": ["dosyalar", "internet_ara"]},
                "c1")],
        [[_cagri("read_file", {"path": "a.md"}, "c2"),
          _cagri("web_search", {"query": "q"}, "c3")],
         "bitti"],
    )
    ikinci_tur = beyin.gorulen_araclar[0]
    assert set(YETENEK_ALANLARI["dosyalar"]) <= ikinci_tur
    assert set(YETENEK_ALANLARI["internet_ara"]) <= ikinci_tur
    assert calisan == ["read_file", "web_search"]
    assert cevap == "bitti" and kosan == 2


def test_yeni_alan_acmak_oncekini_kapatmaz():
    cevap, kosan, calisan, beyin = _kos(
        [_cagri(YETENEK_AC_ADI, {"alanlar": ["dosyalar"]}, "c1")],
        [[_cagri("read_file", {"path": "a.md"}, "c2")],
         [_cagri(YETENEK_AC_ADI, {"alanlar": ["internet_ara"]}, "c3")],
         # internet acildiktan sonra dosyalar hala acik: read_file kosar.
         [_cagri("read_file", {"path": "b.md"}, "c4"),
          _cagri("web_search", {"query": "q"}, "c5")],
         "bitti"],
    )
    son_tur = beyin.gorulen_araclar[2]
    assert set(YETENEK_ALANLARI["dosyalar"]) <= son_tur
    assert set(YETENEK_ALANLARI["internet_ara"]) <= son_tur
    assert calisan == ["read_file", "read_file", "web_search"]
    assert cevap == "bitti" and kosan == 3


def test_acilmamis_alanin_araci_calismaz():
    cevap, kosan, calisan, beyin = _kos(
        [_cagri(YETENEK_AC_ADI, {"alanlar": ["dosyalar"]}, "c1")],
        [[_cagri("web_search", {"query": "q"}, "c2")], "bitti"],
    )
    assert calisan == []
    assert kosan == 0


def test_bilinmeyen_alan_hicbir_sey_acmaz():
    cevap, kosan, calisan, beyin = _kos(
        [_cagri(YETENEK_AC_ADI, {"alanlar": ["internet", "uydurma"]}, "c1")],
        ["bitti"],
    )
    assert beyin.gorulen_araclar[0] == {YETENEK_AC_ADI}
    assert calisan == []


def test_alan_acma_gercek_arac_kosusu_sayilmaz():
    cevap, kosan, calisan, beyin = _kos(
        [_cagri(YETENEK_AC_ADI, {"alanlar": ["hesap"]}, "c1")],
        ["bitti"],
    )
    assert kosan == 0 and calisan == []
