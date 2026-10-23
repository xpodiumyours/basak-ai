"""tests/test_kutu.py — P6b paylasimli kutu (web -> eklenti dogrudan surus).

Kural: ag/DB yok; depo bellek surumuyle degistirilir. Postgres dialekti
saf metindir, burada olculmez — olculen: birak/bekle/al/yaz akisi,
alinmayan isin cevrimdisi hatasi, atomik ustlenme, kopru geri dususu,
WS elci fonksiyonlari.
"""

import threading
import time

from tools import kutu
from tools import tarayici_kopru
from chat import eklenti_ws


def _bellek(monkeypatch):
    depo = kutu._BellekDeposu()
    monkeypatch.setattr(kutu, "_DEPO", depo)
    return depo


class TestAkis:
    def test_birak_al_yaz_bekle(self, monkeypatch):
        _bellek(monkeypatch)
        kimlik = kutu.birak("u1", "sayfa_gozlem", {"baslangic": 0})["id"]
        is_ = kutu.al("u1")
        assert is_["id"] == kimlik
        assert is_["islem"] == "sayfa_gozlem"
        assert kutu.yaz(kimlik, {"ok": True, "sonuc": {"sayfa": 1}}) == {
            "ok": True}
        assert kutu.sonucu_bekle(kimlik) == {
            "ok": True, "sonuc": {"sayfa": 1}}

    def test_ikinci_alma_bos(self, monkeypatch):
        _bellek(monkeypatch)
        kutu.birak("u1", "sayfa_gozlem", {})
        assert "id" in kutu.al("u1")
        assert kutu.al("u1") == {"bos": True}

    def test_baskasinin_isini_alamaz(self, monkeypatch):
        _bellek(monkeypatch)
        kutu.birak("u1", "sayfa_gozlem", {})
        assert kutu.al("u2") == {"bos": True}

    def test_alinmayan_is_cevrimdisi(self, monkeypatch):
        _bellek(monkeypatch)
        kimlik = kutu.birak("u1", "sayfa_gozlem", {})["id"]
        sonuc = kutu.sonucu_bekle(kimlik, alinma=0.1, sonuc=0.1)
        assert "error" in sonuc
        assert "bagli degil" in sonuc["error"]

    def test_sonuc_gelmezse_acik_hata(self, monkeypatch):
        _bellek(monkeypatch)
        kimlik = kutu.birak("u1", "sayfa_gozlem", {})["id"]
        kutu.al("u1")
        sonuc = kutu.sonucu_bekle(kimlik, alinma=0.1, sonuc=0.1)
        assert "error" in sonuc

    def test_dsn_yoksa_kutu_kapali(self, monkeypatch):
        monkeypatch.setattr(kutu, "_DEPO", None)
        monkeypatch.setattr(kutu, "_dsn", lambda: "")
        assert "Paylasilan kutu kapali" in kutu.birak("u", "x", {})["error"]
        assert "Paylasilan kutu kapali" in kutu.al("u")["error"]
        assert "Paylasilan kutu kapali" in kutu.yaz(1, {})["error"]


class TestKopruDususu:
    def test_yerel_yoksa_kutuya_duser(self, monkeypatch):
        _bellek(monkeypatch)
        monkeypatch.setattr(tarayici_kopru.KOPRU, "iste",
                            lambda *a, **k: {"error": "erisilemedi"})
        gozlem = {"url": "https://ornek.test/", "baslik": "O",
                  "ogeler": []}

        def uzanti():
            bitis = time.time() + 9
            while time.time() < bitis:
                is_ = kutu.al("u9")
                if "id" in is_:
                    break
                time.sleep(0.05)
            assert is_["islem"] == "sayfa_gozlem"
            kutu.yaz(is_["id"], {"ok": True, "sonuc": gozlem})

        t = threading.Thread(target=uzanti)
        t.start()
        sonuc = tarayici_kopru.sayfa_bakis(kullanici="u9")
        t.join(timeout=10)
        assert "sayfa" in sonuc
        assert sonuc["sayfa"]["url"] == "https://ornek.test/"

    def test_kutu_kapaliysa_yerel_hata_korunur(self, monkeypatch):
        monkeypatch.setattr(tarayici_kopru.KOPRU, "iste",
                            lambda *a, **k: {"error": "erisilemedi"})
        monkeypatch.setattr(kutu, "_DEPO", None)
        monkeypatch.setattr(kutu, "_dsn", lambda: "")
        sonuc = tarayici_kopru.sayfa_bakis(kullanici="u9")
        assert "error" in sonuc

    def test_eylem_kutuya_duser(self, monkeypatch):
        _bellek(monkeypatch)
        monkeypatch.setattr(tarayici_kopru.KOPRU, "iste",
                            lambda *a, **k: {"error": "erisilemedi"})
        with tarayici_kopru._SON_KILIT:
            tarayici_kopru._SON["u8"] = {
                "nesil": "n1", "url": "https://ornek.test/", "zaman": 0}
        monkeypatch.setattr(tarayici_kopru.tarayici_goz, "ref_coz",
                            lambda ref, nesil: ("0", 3))

        def uzanti():
            bitis = time.time() + 9
            while time.time() < bitis:
                is_ = kutu.al("u8")
                if "id" in is_:
                    break
                time.sleep(0.05)
            assert is_["islem"] == "sayfa_tikla"
            kutu.yaz(is_["id"], {"ok": True, "sonuc": {
                "yapildi": True, "url": "https://ornek.test/"}})

        t = threading.Thread(target=uzanti)
        t.start()
        sonuc = tarayici_kopru.sayfa_tikla("0-n1-3", kullanici="u8")
        t.join(timeout=10)
        assert sonuc.get("yapildi") is True


class TestWsElcileri:
    def test_kutu_al_bos(self, monkeypatch):
        _bellek(monkeypatch)
        assert eklenti_ws._kutu_al("u1") == {"bos": True}

    def test_kutu_al_yazar(self, monkeypatch):
        _bellek(monkeypatch)
        kimlik = kutu.birak("u1", "sayfa_gozlem", {"a": 1})["id"]
        is_ = eklenti_ws._kutu_al("u1")
        assert is_["id"] == kimlik
        assert eklenti_ws._kutu_yaz("u1", {"job": kimlik,
                                           "cevap": {"ok": True}}) == {
            "ok": True}

    def test_kutu_yaz_kotu_girdi(self, monkeypatch):
        _bellek(monkeypatch)
        assert "error" in eklenti_ws._kutu_yaz("u1", {})
        assert "error" in eklenti_ws._kutu_yaz("u1", {"job": "yok"})
        assert "error" in eklenti_ws._kutu_yaz("u1", {"job": 999,
                                                     "cevap": {}})
