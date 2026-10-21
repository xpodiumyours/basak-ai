"""tests/test_tarayici_ws.py — yerel WS koprusu bekcileri.

Gercek WebSocket sunucusu acilir, sahte bir eklenti istemcisi baglanir ve
cekirdegin `sayfa_bakis` cagrisi uctan uca olculur. Tarayici YOK, ag YOK
(yalniz 127.0.0.1), dis servis YOK.

Olculenler:
1. Bagli eklenti -> sayfa gozlemi cekirdege ulasir.
2. Anahtar yanlissa baglanti reddedilir, istemci defterine HIC girmez.
3. Uzanti disi kaynak (Origin) reddedilir.
4. Cevap vermeyen eklenti zaman asimina duser; sohbet kilitlenmez.
5. Eklenti kopunca defter temizlenir ve arac acik hata doner.
"""

import json
import threading
import time

import pytest
from websockets.exceptions import ConnectionClosed
from websockets.sync.client import connect

from tools import calistir
from tools.tarayici_kopru import KOPRU, sayfa_bakis
from tools.tarayici_ws import KopruSunucusu

SAYFA = {
    "url": "https://ornek.test/panel",
    "baslik": "Panel",
    "ogeler": [
        {"rol": "heading", "ad": "Gunluk ozet"},
        {"rol": "button", "ad": "Yenile"},
        {"rol": "textbox", "ad": "Ara", "deger": ""},
    ],
}


@pytest.fixture(autouse=True)
def _temiz_defter():
    for kimlik in KOPRU.kimlikler():
        KOPRU.ayir(kimlik)
    yield
    for kimlik in KOPRU.kimlikler():
        KOPRU.ayir(kimlik)


@pytest.fixture
def sunucu():
    s = KopruSunucusu(port=0).basla()
    yield s
    s.durdur()


def _bekle(kosul, sure=3.0):
    bitis = time.time() + sure
    while time.time() < bitis:
        if kosul():
            return True
        time.sleep(0.02)
    return False


def _eklenti(port, yol="/", cevapla=True, sayfa=None):
    """Sahte eklenti: gelen istege gozlemle cevap verir (ya da susar)."""
    hazir = threading.Event()
    govde = sayfa or SAYFA

    def kos():
        try:
            with connect("ws://127.0.0.1:%d%s" % (port, yol)) as ws:
                hazir.set()
                for ham in ws:
                    if not cevapla:
                        continue
                    mesaj = json.loads(ham)
                    ws.send(json.dumps(
                        {"id": mesaj["id"], "ok": True, "sonuc": govde}))
        except ConnectionClosed:
            hazir.set()

    threading.Thread(target=kos, daemon=True).start()
    return hazir


class TestUctanUca:
    def test_bagli_eklenti_gozlem_verir(self, sunucu):
        hazir = _eklenti(sunucu.port)
        assert hazir.wait(3)
        assert _bekle(KOPRU.var_mi)

        sonuc = sayfa_bakis(adet=2)
        assert sonuc["sayfa"]["baslik"] == "Panel"
        assert sonuc["sayfa"]["url"] == SAYFA["url"]
        assert len(sonuc["ogeler"]) == 2
        assert sonuc["sayfalama"]["toplam"] == 3
        assert sonuc["sayfalama"]["sonraki_baslangic"] == 2

    def test_arac_yolu_da_ayni_kanali_kullanir(self, sunucu):
        hazir = _eklenti(sunucu.port)
        assert hazir.wait(3)
        assert _bekle(KOPRU.var_mi)

        sonuc = calistir("sayfa_bakis", {"adet": 5})
        assert set(sonuc) == {"sayfa", "ogeler", "sayfalama"}
        assert sonuc["ogeler"][0]["rol"] == "heading"

    def test_eklenti_kopunca_defter_temizlenir(self, sunucu):
        hazir = _eklenti(sunucu.port)
        assert hazir.wait(3)
        assert _bekle(KOPRU.var_mi)

        sunucu.durdur()
        assert _bekle(lambda: not KOPRU.var_mi(), 5.0)
        assert "error" in sayfa_bakis()


class TestGuvenlik:
    def test_yanlis_anahtar_reddedilir(self):
        sunucu = KopruSunucusu(port=0, token="gizli-anahtar").basla()
        try:
            with connect("ws://127.0.0.1:%d/" % sunucu.port) as ws:
                with pytest.raises(ConnectionClosed):
                    ws.recv()
            assert not KOPRU.var_mi()
        finally:
            sunucu.durdur()

    def test_dogru_anahtar_kabul_edilir(self):
        sunucu = KopruSunucusu(port=0, token="gizli-anahtar").basla()
        try:
            hazir = _eklenti(sunucu.port, "/?token=gizli-anahtar")
            assert hazir.wait(3)
            assert _bekle(KOPRU.var_mi)
            assert sayfa_bakis()["sayfa"]["baslik"] == "Panel"
        finally:
            sunucu.durdur()

    def test_uzanti_disi_kaynak_reddedilir(self, sunucu):
        with connect("ws://127.0.0.1:%d/" % sunucu.port,
                     additional_headers={"Origin": "https://kotu.test"}) as ws:
            with pytest.raises(ConnectionClosed):
                ws.recv()
        assert not KOPRU.var_mi()

    def test_uzanti_kaynagi_kabul_edilir(self, sunucu):
        hazir = threading.Event()

        def kos():
            try:
                with connect("ws://127.0.0.1:%d/" % sunucu.port,
                             additional_headers={
                                 "Origin": "chrome-extension://abcdef"}) as ws:
                    hazir.set()
                    ws.recv()  # sunucudan istek gelene kadar bekle
            except ConnectionClosed:
                hazir.set()
        threading.Thread(target=kos, daemon=True).start()
        assert hazir.wait(3)
        assert _bekle(KOPRU.var_mi)


class TestKullaniciAyrimi:
    """Cok kullanicili sunucuda sizinti olmamali."""

    def _sayfa(self, kim):
        return {"url": "https://ornek.test/%s" % kim,
                "baslik": kim.title(),
                "ogeler": [{"rol": "heading", "ad": kim}]}

    def test_her_kullanici_kendi_sekmesini_gorur(self):
        ayse = KopruSunucusu(port=0, kullanici="ayse").basla()
        mehmet = KopruSunucusu(port=0, kullanici="mehmet").basla()
        try:
            h1 = _eklenti(ayse.port, sayfa=self._sayfa("ayse"))
            h2 = _eklenti(mehmet.port, sayfa=self._sayfa("mehmet"))
            assert h1.wait(3) and h2.wait(3)
            assert _bekle(lambda: KOPRU.var_mi("ayse")
                          and KOPRU.var_mi("mehmet"))

            assert sayfa_bakis(kullanici="ayse")["sayfa"]["url"].endswith("/ayse")
            assert sayfa_bakis(kullanici="mehmet")["sayfa"]["url"].endswith("/mehmet")
        finally:
            ayse.durdur()
            mehmet.durdur()

    def test_bagli_olmayan_kullaniciya_baskasinin_sayfasi_verilmez(self):
        ayse = KopruSunucusu(port=0, kullanici="ayse").basla()
        try:
            hazir = _eklenti(ayse.port, sayfa=self._sayfa("ayse"))
            assert hazir.wait(3)
            assert _bekle(lambda: KOPRU.var_mi("ayse"))

            sonuc = sayfa_bakis(kullanici="zeynep")
            assert "error" in sonuc
            assert "Bu kullanici icin" in sonuc["error"]
            assert "sayfa" not in sonuc
        finally:
            ayse.durdur()


class TestPanelSohbeti:
    """Panelden gelen mesaj cekirdege gider; cevap ayni kanaldan doner."""

    def _konus(self, port, mesaj, sayfa=None, sure=10.0):
        """Mesaji yollar; cekirdek isteklerini yanitlar, sohbet cevabini doner."""
        govde = sayfa or SAYFA
        with connect("ws://127.0.0.1:%d/" % port) as ws:
            ws.send(json.dumps(mesaj))
            bitis = time.time() + sure
            while time.time() < bitis:
                kalan = bitis - time.time()
                if kalan <= 0:
                    break
                gelen = json.loads(ws.recv(timeout=kalan))
                if gelen.get("islem"):
                    ws.send(json.dumps(
                        {"id": gelen["id"], "ok": True, "sonuc": govde}))
                    continue
                return gelen
        raise AssertionError("sohbet cevabi gelmedi")

    def test_panel_mesaji_cekirdege_gider(self):
        gorulen = []

        def sohbet(metin, kullanici):
            gorulen.append((metin, kullanici))
            return {"cevap": "merhaba Casper"}

        sunucu = KopruSunucusu(port=0, kullanici="casper",
                               sohbet_isle=sohbet).basla()
        try:
            cevap = self._konus(sunucu.port, {
                "id": "p1", "islem": "sohbet",
                "veri": {"metin": "selam"}})
            assert cevap == {"id": "p1", "ok": True,
                             "sonuc": {"cevap": "merhaba Casper"}}
            assert gorulen == [("selam", "casper")]
        finally:
            sunucu.durdur()

    def test_sohbet_icinden_sayfa_okunabilir(self):
        """Kilitlenme testi: sohbet surerken gozlem istegi cevaplanabilmeli."""

        def sohbet(metin, kullanici):
            gozlem = sayfa_bakis(adet=5)
            if "error" in gozlem:
                return {"cevap": "HATA: " + gozlem["error"]}
            return {"cevap": "baslik=" + gozlem["sayfa"]["baslik"]}

        sunucu = KopruSunucusu(port=0, sohbet_isle=sohbet).basla()
        try:
            cevap = self._konus(sunucu.port, {
                "id": "p2", "islem": "sohbet",
                "veri": {"metin": "bu sayfada ne var"}})
            assert cevap["ok"] is True
            assert cevap["sonuc"]["cevap"] == "baslik=Panel"
        finally:
            sunucu.durdur()

    def test_sohbet_hatasi_acik_doner(self):
        def sohbet(metin, kullanici):
            raise RuntimeError("model yok")

        sunucu = KopruSunucusu(port=0, sohbet_isle=sohbet).basla()
        try:
            cevap = self._konus(sunucu.port, {
                "id": "p3", "islem": "sohbet", "veri": {"metin": "x"}})
            assert cevap["ok"] is False
            assert "model yok" in cevap["hata"]
        finally:
            sunucu.durdur()

    def test_bos_mesaj_reddedilir(self):
        sunucu = KopruSunucusu(
            port=0, sohbet_isle=lambda metin, k: {"cevap": "olmamali"}).basla()
        try:
            cevap = self._konus(sunucu.port, {
                "id": "p4", "islem": "sohbet", "veri": {"metin": "   "}})
            assert cevap["ok"] is False
            assert "mesaj bos" in cevap["hata"]
        finally:
            sunucu.durdur()

    def test_sohbet_kapaliysa_acik_hata(self):
        sunucu = KopruSunucusu(port=0).basla()
        try:
            cevap = self._konus(sunucu.port, {
                "id": "p5", "islem": "sohbet", "veri": {"metin": "x"}})
            assert cevap["ok"] is False
            assert "kapali" in cevap["hata"]
        finally:
            sunucu.durdur()


class TestZamanAsimi:
    def test_susan_eklenti_zaman_asimina_duser(self, sunucu):
        hazir = _eklenti(sunucu.port, cevapla=False)
        assert hazir.wait(3)
        assert _bekle(KOPRU.var_mi)

        sonuc = KOPRU.iste("sayfa_gozlem", {}, sure=0.3)
        assert "error" in sonuc
        assert "cevap vermedi" in sonuc["error"]
