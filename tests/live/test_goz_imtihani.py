"""tests/live/test_goz_imtihani.py — Gercek fis fotografi → katalog (GERCEK).

Kapi (2026-09-26, Casper hedefi): fis_4 (15.09.2026) fotografindan
GERCEK ajan dongusu (mesaj_isle) katalog kurar: 13 satir / 75 ad /
6.034,00 TL. Gercek model + gercek bulut gozu + kota harcar;
yalniz --live ile calisir:

    python -m pytest tests/live/test_goz_imtihani.py --live -q

Fotograf data/fatura-ornekleri/ altindadir (git disi); yoksa atlanir.
"""

import base64
import json
import os
import sys

import pytest

BASE = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
sys.path.insert(0, BASE)

FOTOGRAF = os.path.join(BASE, "data", "fatura-ornekleri",
                        "fis_4_15092026.png")
BEKLENEN_SATIR = 13
BEKLENEN_ADET = 75
BEKLENEN_TOPLAM = 6034.00


def test_gercek_fis_katalog_kurulur(tmp_path, monkeypatch, rapor):
    if not os.path.isfile(FOTOGRAF):
        pytest.skip("fis fotografi yok (data/fatura-ornekleri/ git disi)")

    from chat import context as ctx
    monkeypatch.setattr(ctx, "HISTORY_FILE", str(tmp_path / "gecmis.json"))
    monkeypatch.setattr(ctx, "SETTINGS_FILE", str(tmp_path / "ayar.json"))
    monkeypatch.setattr(ctx, "_hafiza", False)

    from brain import Brain
    b = Brain()
    if not b.ajan_musait():
        pytest.skip("ajan protokolu destekli ucretsiz model bagli degil")
    if not b.bulut_musait():
        pytest.skip("bulut zinciri kurulamadi")

    from chat.flow import mesaj_isle
    from tools import TOOLS
    import tools as tools_mod
    from tools import katalog

    ham = open(FOTOGRAF, "rb").read()
    kayit = katalog.fatura_kaydet_b64(
        base64.b64encode(ham).decode(), "fis_4_15092026.png")
    assert "result" in kayit, kayit
    fatura_id = json.loads(kayit["result"])["fatura_id"]

    gercek_calistir = tools_mod.calistir
    kosulan = []

    def kayitli_calistir(ad, args):
        kosulan.append(ad)
        return gercek_calistir(ad, args)

    monkeypatch.setattr(tools_mod, "calistir", kayitli_calistir)

    olaylar = []
    mesaj_isle(
        "Şu fatura fotoğrafını katalogla: %s" % fatura_id,
        b, "Sen Başak'sın. Türkçe konuş.",
        lambda kod: olaylar.append(kod), TOOLS)

    assert any(x.startswith("BasakUI.bitir(") for x in olaylar), (
        "ajan son cevaba ulasamadi")
    assert "fatura_oku" in kosulan, kosulan
    assert "katalog_kur" in kosulan, kosulan

    liste = json.loads(katalog.katalog_listele()["result"])
    is_id = None
    for is_ in liste:
        v = json.loads(katalog.katalog_getir(is_["is_id"])["result"])
        if v.get("fatura_id") == fatura_id:
            is_id = is_["is_id"]
            break
    assert is_id, "katalog isi olusturulmedi"

    isv = json.loads(katalog.katalog_getir(is_id)["result"])
    satirlar = isv.get("satirlar", [])
    adet = sum(int(s.get("adet") or 0) for s in satirlar)
    toplam = (isv.get("ustbilgi") or {}).get("toplam")
    rapor("goz_imtihani", {
        "fatura_id": fatura_id, "is_id": is_id,
        "satir": len(satirlar), "adet": adet, "toplam": toplam,
        "kart": len(isv.get("kartlar", [])),
        "kosulan": kosulan,
    })

    assert len(satirlar) == BEKLENEN_SATIR, (
        "satir sayisi %d (beklenen %d)" % (len(satirlar), BEKLENEN_SATIR))
    assert adet == BEKLENEN_ADET, (
        "adet toplami %d (beklenen %d)" % (adet, BEKLENEN_ADET))
    assert toplam is not None and abs(toplam - BEKLENEN_TOPLAM) < 0.01, (
        "ustbilgi toplami %s (beklenen %.2f)" % (toplam, BEKLENEN_TOPLAM))
