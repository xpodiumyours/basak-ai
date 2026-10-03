"""tests/test_handoff_token_sismesi.py — akis parcasinda tekrar eden
handoff tokenini kapatir.

2026-10-03 CANLI OLCUM (basak-vercel, 3 cumlelik cevap):
    yanit toplam      675.073 bayt
    gercek cevap metni   551 bayt
    handoff_token      663.987 bayt  (%98,4) — 130 olaya gomulu

Kok neden: app.py `_OlayToplayici.__call__` her `parca` olayina biriken
tum gecmisin imzali tokenini koyuyordu. Token her parcada buyudugu icin
toplam maliyet karesel (O(n^2)) idi.

Duzeltme: olaylar yine biriktirilir, token yalniz terminal olaya konur.
Istemci (web/app.js) yalniz en son gordugu tokeni tutar.
"""
import json

import app


ANAHTAR = b"k" * 32


def _toplayici(anahtar=ANAHTAR, **kw):
    return app._OlayToplayici("r1", handoff_key=anahtar, **kw)


def test_parca_olayi_token_tasimaz():
    """Ara adimda token gonderilmez — istemci zaten kullanmiyor."""
    k = _toplayici()
    k("BasakUI.parca(\"Istanbul\")")
    assert k.olaylar[0]["tur"] == "parca"
    assert "handoff_token" not in k.olaylar[0]


def test_bitir_olayi_token_tasir():
    k = _toplayici()
    k("BasakUI.parca(\"Merhaba\")")
    k("BasakUI.bitir(\"Merhaba, nasilsin?\", \"groq\")")
    bitir = k.olaylar[-1]
    assert bitir["tur"] == "bitir"
    assert isinstance(bitir.get("handoff_token"), str)
    assert bitir["handoff_token"]


def test_token_gecmisin_tumunu_kapsar():
    """Token parca metinlerini ICERIR; devam zinciri bos kalmaz.

    AGENTS.md: 'Onceki surumun sessiz kesmeleri geri gelemez' —
    parca olaylari biriktirilmeden birakilirsa kullanici cevabinin
    yarisi kaybolur.
    """
    k = _toplayici()
    k("BasakUI.parca(\"bir \")")
    k("BasakUI.parca(\"iki \")")
    k("BasakUI.bitir(\"bir iki \", \"groq\")")
    coz = app._handoff_tokeni_coz(k.olaylar[-1]["handoff_token"], ANAHTAR)
    parcalar = [o for o in coz["olaylar"] if o.get("tur") == "parca"]
    assert [o["metin"] for o in parcalar] == ["bir ", "iki "]


def test_token_kaybi_yok_onceki_davranisla_ayni_gecmis():
    """Yeni surumun gecmisi eskinin UST KUMESI olmali.

    Eski surumde token yalniz `parca` olaylarindan kurulurdu. Yeni
    surumde `bitir` de imzaya dahil — yani gecmis kaybolmaz, bir olay
    daha kazanilir. Karsilastirma: ilk N olay birebir ayni olmali.
    """
    parcalar = ["bir ", "iki ", "uc "]

    yeni = _toplayici()
    for p in parcalar:
        yeni('BasakUI.parca("%s")' % p)
    yeni('BasakUI.bitir("bir iki uc ", "groq")')
    yeni_coz = app._handoff_tokeni_coz(yeni.olaylar[-1]["handoff_token"], ANAHTAR)

    eski = _toplayici()
    for p in parcalar:
        eski('BasakUI.parca("%s")' % p)
    eski_coz = app._handoff_tokeni_coz(
        app._handoff_tokeni(
            {"schema": app._HANDOFF_SCHEMA,
             "olaylar": list(eski.handoff_olaylar)},
            ANAHTAR,
        ),
        ANAHTAR,
    )

    # Onceki surumun gecmisi, yenisinin bir oneki olmali (kaybi yok).
    n = len(eski_coz["olaylar"])
    assert yeni_coz["olaylar"][:n] == eski_coz["olaylar"]
    # Yeni surum terminal olayi da tasir.
    assert yeni_coz["olaylar"][n]["tur"] == "bitir"


def test_yuz_yirmi_bes_parcada_yag_onceki_kadar_byte_gonderilir():
    """125 parcalik bir cevap: 663 KB -> tek terminal token.

    Canli olcumdeki 652.944 bayt tekrar, burada byte butcesiyle sabit.
    """
    k = _toplayici()
    for i in range(125):
        k('BasakUI.parca("parca-%d ")' % i)
    k('BasakUI.bitir("tamam", "groq")')

    ham = json.dumps(k.olaylar, ensure_ascii=False)
    token_bayt = sum(
        len(o.get("handoff_token") or "") for o in k.olaylar
    )
    # Eski surum: her parca kendi tokenini tasiyordu -> 125 * ~5.2 KB.
    assert token_bayt < 20_000, "token yine parcalara tasiniyor: %d bayt" % token_bayt
    assert len(ham) < 30_000
