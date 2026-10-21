"""tests/test_sayfa_eylem.py — açık sayfada tıklama ve yazma (yerel + bulut).

Sözleşme
--------
- Ref `<nesil>-<kimlik>` biçimindedir; sayı kısmı **öğenin kalıcı
  kimliğidir**, listedeki sırası değil. Süzme/sayfalama kaydırmaz.
- Eylem yalnız **son gözlemin** nesli geçerliyken yapılır (`ref_coz`).
  Gözlem yoksa ya da ref bayatsa eklentiye istek GİTMEZ.
- Sayfa adresi eylemden sonra değiştiyse nesil düşer: sonraki eylem
  yeni bir gözlem ister.
- Yazma metni olduğu gibi taşınır (kırpma yok).
- Bulut yolunda eylem de sohbetle AYNI WebSocket kanalından gider.

Model çağrılmaz; sahte istemci/kanal yeterlidir.
"""

import json
import os
import sys

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import app as app_modulu  # noqa: E402
from tools import tarayici_kopru  # noqa: E402

GOZLEM = {
    "url": "https://ornek.test/hesap",
    "baslik": "Hesap",
    "ogeler": [
        {"sira": 5, "rol": "textbox", "ad": "E-posta", "deger": ""},
        {"sira": 9, "rol": "button", "ad": "Kaydet", "deger": ""},
    ],
}


class SahteIstemci:
    """Yerel köprü istemcisi: istekleri kaydeder, sırayla cevap verir."""

    def __init__(self, cevaplar=None):
        self.istekler = []
        self.cevaplar = list(cevaplar or [])

    def __call__(self, islem, veri, sure):
        self.istekler.append((islem, dict(veri)))
        if self.cevaplar:
            return self.cevaplar.pop(0)
        return {"ok": True, "sonuc": GOZLEM}


@pytest.fixture
def istemci(monkeypatch):
    sahte = SahteIstemci()
    for kimlik in list(tarayici_kopru.KOPRU.kimlikler()):
        tarayici_kopru.KOPRU.ayir(kimlik)
    tarayici_kopru.KOPRU.bagla("test-istemci", sahte, kullanici="casper")
    tarayici_kopru._SON.clear()
    monkeypatch.setattr("chat.kimlik.aktif_kullanici", lambda: "casper")
    return sahte


def _gozlem_veya_hata():
    return tarayici_kopru.sayfa_bakis()


def test_ref_kalici_kimlik_tasir(istemci):
    """Ref'in sayı kısmı sıra değil, öğenin kendi kimliğidir."""
    sonuc = _gozlem_veya_hata()
    assert "error" not in sonuc, sonuc
    refs = [oge["ref"] for oge in sonuc["ogeler"]]
    nesil = sonuc["sayfa"]["nesil"]
    assert refs == ["%s-5" % nesil, "%s-9" % nesil], refs


def test_tikla_kimligi_geri_yollar(istemci):
    sonuc = _gozlem_veya_hata()
    ref = sonuc["ogeler"][1]["ref"]

    cevap = tarayici_kopru.sayfa_tikla(ref)

    assert "error" not in cevap, cevap
    islem, veri = istemci.istekler[-1]
    assert islem == "sayfa_tikla", islem
    assert veri == {"sira": 9}, veri


def test_yaz_metni_kirpmadan_tasir(istemci):
    sonuc = _gozlem_veya_hata()
    ref = sonuc["ogeler"][0]["ref"]
    metin = "  casper@ornek.test  "

    cevap = tarayici_kopru.sayfa_yaz(ref, metin)

    assert "error" not in cevap, cevap
    islem, veri = istemci.istekler[-1]
    assert islem == "sayfa_yaz", islem
    assert veri == {"sira": 5, "metin": metin}, veri


def test_gozlem_olmadan_eylem_yok(istemci):
    cevap = tarayici_kopru.sayfa_tikla("abc-1")
    assert "error" in cevap
    assert "sayfa_bakis" in cevap["error"]
    assert istemci.istekler == [], istemci.istekler


def test_bayat_ref_eklentiye_gitmez(istemci):
    sonuc = _gozlem_veya_hata()
    ref = sonuc["ogeler"][0]["ref"]
    istemci.istekler.clear()

    bayat = "0000000000-" + ref.rsplit("-", 1)[1]
    cevap = tarayici_kopru.sayfa_tikla(bayat)

    assert "error" in cevap
    assert "Bayat" in cevap["error"], cevap
    assert istemci.istekler == [], istemci.istekler


def test_adres_degisirse_sonraki_eylem_yeni_gozlem_ister(istemci):
    sonuc = _gozlem_veya_hata()
    ref = sonuc["ogeler"][1]["ref"]
    # Tıklama yeni sayfaya götürdü: cevap farklı adres döner.
    istemci.cevaplar = [{
        "ok": True,
        "sonuc": {"yapildi": "tikla", "sira": 9,
                  "url": "https://ornek.test/hesap/onay"},
    }]

    ilk = tarayici_kopru.sayfa_tikla(ref)
    assert "error" not in ilk, ilk

    ikinci = tarayici_kopru.sayfa_tikla(ref)
    assert "error" in ikinci
    assert "sayfa_bakis" in ikinci["error"]


def test_eklenti_hatasi_acik_doner(istemci):
    sonuc = _gozlem_veya_hata()
    ref = sonuc["ogeler"][1]["ref"]
    istemci.cevaplar = [{"ok": False, "hata": "Oge kapali (disabled)"}]

    cevap = tarayici_kopru.sayfa_tikla(ref)

    assert cevap == {"error": "Oge kapali (disabled)"}, cevap


# ── Bulut yolu: eylem sohbetle aynı kanaldan ─────────────────────────


@pytest.fixture
def ws_istemci(monkeypatch):
    monkeypatch.setattr(app_modulu, "_cekirdek", lambda: (object(), []))
    return TestClient(app_modulu.app)


def test_bulut_kanalinda_tiklama_ve_yazma(ws_istemci, monkeypatch):
    """Çekirdek önce bakar, sonra yazar ve tıklar: ikisi de aynı soketten."""
    yakalanan = {}

    def sahte_mesaj_isle(metin, beyin, kisilik, ayikla, toollar,
                         misafir=False, **fazla):
        bakim = tarayici_kopru.sayfa_bakis()
        yakalanan["bakim"] = bakim
        alan = bakim["ogeler"][0]["ref"]
        dugme = bakim["ogeler"][1]["ref"]
        yakalanan["yaz"] = tarayici_kopru.sayfa_yaz(alan, "abc")
        yakalanan["tikla"] = tarayici_kopru.sayfa_tikla(dugme)
        ayikla("BasakUI.bitir(%s, %s)" % (json.dumps("tamam"), json.dumps("prova")))

    monkeypatch.setattr("chat.flow.mesaj_isle", sahte_mesaj_isle)

    with ws_istemci.websocket_connect("/api/eklenti") as ws:
        ws.send_json({"id": "p1", "islem": "sohbet",
                      "veri": {"metin": "formu doldur"}})

        gozlem_istegi = ws.receive_json()
        assert gozlem_istegi["islem"] == "sayfa_gozlem", gozlem_istegi
        ws.send_json({"id": gozlem_istegi["id"], "ok": True, "sonuc": GOZLEM})

        yaz_istegi = ws.receive_json()
        assert yaz_istegi["islem"] == "sayfa_yaz", yaz_istegi
        assert yaz_istegi["veri"] == {"sira": 5, "metin": "abc"}, yaz_istegi
        ws.send_json({"id": yaz_istegi["id"], "ok": True,
                      "sonuc": {"yapildi": "yaz", "sira": 5,
                                "url": GOZLEM["url"], "uzunluk": 3}})

        tik_istegi = ws.receive_json()
        assert tik_istegi["islem"] == "sayfa_tikla", tik_istegi
        assert tik_istegi["veri"] == {"sira": 9}, tik_istegi
        ws.send_json({"id": tik_istegi["id"], "ok": True,
                      "sonuc": {"yapildi": "tikla", "sira": 9,
                                "url": GOZLEM["url"]}})

        cevap = ws.receive_json()

    assert cevap["ok"] is True, cevap
    assert "error" not in yakalanan["yaz"], yakalanan["yaz"]
    assert "error" not in yakalanan["tikla"], yakalanan["tikla"]


# ── Panelden gelen geçmiş ────────────────────────────────────────────


def test_gecmis_yapisi_dogrulanir():
    from chat.eklenti_ws import _gecmis_coz

    assert _gecmis_coz(None) is None
    assert _gecmis_coz("metin") is None
    assert _gecmis_coz([]) is None
    assert _gecmis_coz([{"role": "system", "content": "x"}]) is None
    assert _gecmis_coz([{"role": "user", "content": "   "}]) is None
    assert _gecmis_coz([{"role": "user", "content": "selam"}]) == [
        {"role": "user", "content": "selam"}]


def test_gecmis_kirpilmadan_tasinir():
    from chat.eklenti_ws import _gecmis_coz

    uzun = "a" * 5000
    cozulen = _gecmis_coz([
        {"role": "user", "content": uzun},
        {"role": "assistant", "content": "kisa"},
    ])
    assert cozulen[0]["content"] == uzun
    assert len(cozulen) == 2


def test_panel_gecmisi_cekirdege_gecer(ws_istemci, monkeypatch):
    yakalanan = {}

    def sahte_mesaj_isle(metin, beyin, kisilik, ayikla, toollar,
                         misafir=False, **fazla):
        yakalanan.update(fazla)
        ayikla("BasakUI.bitir(%s, %s)" % (json.dumps("tamam"), json.dumps("prova")))

    monkeypatch.setattr("chat.flow.mesaj_isle", sahte_mesaj_isle)

    gecmis = [{"role": "user", "content": "benim adim Casper"},
              {"role": "assistant", "content": "not aldim"}]
    with ws_istemci.websocket_connect("/api/eklenti") as ws:
        ws.send_json({"id": "p1", "islem": "sohbet",
                      "veri": {"metin": "adim ne?", "gecmis": gecmis}})
        cevap = ws.receive_json()

    assert cevap["ok"] is True, cevap
    assert yakalanan.get("gecmis_override") == gecmis
