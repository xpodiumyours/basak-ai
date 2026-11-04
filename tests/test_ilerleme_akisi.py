"""Akis ilerleme gostergesi testleri.

Muhakeme modelleri (Groq gpt-oss: reasoning varsayilan acik) cevap
metninden once dusunme jetonu uretir. Bu jetonlar `content`e girmez;
akis onlari UI'ya `durum` olayi olarak bildirir. Cevap metni DEGISMEZ.
"""

from types import SimpleNamespace

from brain.yayin import AracIstegi, akit
from chat.output_control import (
    durum_gozlemcisi,
    ilerleme_gozlemcisi,
    ilerleme_kw,
)


class SahteAkis:
    def __init__(self, parcalar):
        self.parcalar = parcalar

    def __iter__(self):
        return iter(self.parcalar)


class SahteIstemci:
    def __init__(self, parcalar):
        self._parcalar = parcalar
        self.chat = SimpleNamespace(
            completions=SimpleNamespace(create=self._create))

    def _create(self, **kwargs):
        return SahteAkis(self._parcalar)


def _parca(muhakeme=None, metin=None, arac=None, bitis=None):
    delta = SimpleNamespace(
        reasoning_content=muhakeme, content=metin, tool_calls=arac)
    return SimpleNamespace(
        choices=[SimpleNamespace(delta=delta, finish_reason=bitis)])


def test_muhakeme_ilerleme_olarak_bildirilir_metin_degismez():
    olaylar = []
    istemci = SahteIstemci([
        _parca(muhakeme="once dusun"),
        _parca(metin="Mer"),
        _parca(metin="haba"),
    ])
    parcalar = list(akit(
        istemci, "model", [{"role": "user", "content": "selam"}],
        ilerleme=olaylar.append))

    assert "".join(parcalar) == "Merhaba"
    turler = [o["tur"] for o in olaylar]
    assert turler[0] == "muhakeme"
    assert turler[-1] == "metin"
    assert all(isinstance(o["saniye"], float) for o in olaylar)


def test_ilerleme_yoksa_akis_aynen_calisir():
    istemci = SahteIstemci([_parca(metin="tamam")])
    assert list(akit(istemci, "model", [])) == ["tamam"]


def test_arac_istegi_ilerleme_varken_de_korunur():
    arac = [SimpleNamespace(
        index=0, id="c1",
        function=SimpleNamespace(name="saat", arguments='{"x":1}'))]
    istemci = SahteIstemci([_parca(muhakeme="dusun", arac=arac)])
    try:
        list(akit(istemci, "model", [], tools=[{"a": 1}],
                  ilerleme=lambda v: None))
    except AracIstegi as istek:
        assert istek.tool_calls[0]["function"]["name"] == "saat"
    else:  # pragma: no cover - regresyon korumasi
        raise AssertionError("AracIstegi bekleniyordu")


def test_ilerleme_durum_olayina_duz_metin_olarak_duser():
    olaylar = []
    cb = SimpleNamespace(olay=lambda ad, **kw: olaylar.append((ad, kw)))
    cevir = ilerleme_gozlemcisi(cb)

    cevir({"tur": "saglayici", "saglayici": "groq"})
    cevir({"tur": "muhakeme", "saniye": 21.4})
    cevir({"tur": "metin", "saniye": 22.0})

    assert [o[0] for o in olaylar] == ["durum", "durum"]
    assert "groq" in olaylar[0][1]["metin"]
    assert "21 sn" in olaylar[1][1]["metin"]


def test_eski_imzali_akis_ilerleme_almaz_ve_kirilmaz():
    def eski(mesajlar, model, tools=None, durum=None):
        return iter(())

    def yeni(mesajlar, model, ilerleme=None, **kw):
        return iter(())

    cb = lambda veri: None
    assert ilerleme_kw(eski, cb) == {}
    assert ilerleme_kw(yeni, cb) == {"ilerleme": cb}
    assert ilerleme_kw(yeni, None) == {}


def test_olay_desteklemeyen_callback_sessiz_kalir():
    assert durum_gozlemcisi(lambda kod: None) is None
    assert ilerleme_gozlemcisi(lambda kod: None) is None
