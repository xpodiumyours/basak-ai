"""tests/test_isdosya.py - Is dosyasi (gorev hafizasi) testleri.

A1 paketi: ac/oku/ekle/kapat, atomik yazim, butce, aktif takibi.
Tum testler tmp kok kullanir (uretim data/isler'e dokunulmaz).
"""

import os

from tools import isdosya as D


def _ac(kok, baslik="Musteri bul", hedef="Vixrex icin 10 isletme arastir"):
    r = D.is_ac_dosya(baslik, hedef, kok=kok)
    assert "is_id" in r, r
    return r["is_id"]


class TestAcma:
    def test_acar_ve_aktif_yapar(self, tmp_path):
        kok = str(tmp_path)
        sid = _ac(kok)
        assert D.aktif_id(kok=kok) == sid
        assert os.path.isfile(os.path.join(kok, sid + ".md"))

    def test_bos_baslik_hedef_reddedilir(self, tmp_path):
        kok = str(tmp_path)
        assert "error" in D.is_ac_dosya("", "hedef", kok=kok)
        assert "error" in D.is_ac_dosya("baslik", "", kok=kok)
        assert D.aktif_id(kok=kok) is None

    def test_hedef_sonradan_degismez(self, tmp_path):
        kok = str(tmp_path)
        sid = _ac(kok)
        r = D.is_notu_yaz(sid, "hedef", "yeni hedef", kok=kok)
        assert "error" in r


class TestYazma:
    def test_plan_bulgu_sonraki_karar(self, tmp_path):
        kok = str(tmp_path)
        sid = _ac(kok)
        assert D.is_notu_yaz(sid, "plan", "1. aday topla", kok=kok)["result"]
        assert D.is_notu_yaz(sid, "bulgu", "A firmasi uygun", kok=kok)["result"]
        assert D.is_notu_yaz(sid, "sonraki", "B firmasi aranacak",
                             kok=kok)["result"]
        assert D.is_notu_yaz(sid, "karar", "A ile devam", kok=kok)["result"]
        metin = D.is_oku(sid, kok=kok)
        assert "A firmasi uygun" in metin
        assert "B firmasi aranacak" in metin

    def test_bilinmeyen_bolum_reddedilir(self, tmp_path):
        kok = str(tmp_path)
        sid = _ac(kok)
        assert "error" in D.is_notu_yaz(sid, "sacma", "x", kok=kok)
        assert "error" in D.is_notu_yaz("yok-123", "plan", "x", kok=kok)

    def test_bulgular_tavanli_eski_duser(self, tmp_path):
        kok = str(tmp_path)
        sid = _ac(kok)
        for i in range(D.BULGU_ADET + 3):
            D.is_notu_yaz(sid, "bulgu", "bulgu-%d" % i, kok=kok)
        metin = D.is_oku(sid, butce=100000, kok=kok)
        assert "bulgu-0" not in metin
        assert "bulgu-%d" % (D.BULGU_ADET + 2) in metin


class TestButce:
    def test_okuma_butcesi_asılmaz(self, tmp_path):
        kok = str(tmp_path)
        sid = _ac(kok, hedef="H" * 400)
        for i in range(8):
            D.is_notu_yaz(sid, "plan", "adim-%d " % i + "x" * 150, kok=kok)
            D.is_notu_yaz(sid, "bulgu", "kanit-%d " % i + "y" * 250, kok=kok)
        D.is_notu_yaz(sid, "sonraki", "SIRADAKI ADIM", kok=kok)
        metin = D.is_oku(sid, kok=kok)
        assert len(metin) <= D.IS_BUTCESI + 3
        # Oncelik: SONRAKI ve HEDEF yasamali
        assert "SIRADAKI ADIM" in metin
        assert "## HEDEF" in metin

    def test_kapali_is_okunmaz(self, tmp_path):
        kok = str(tmp_path)
        sid = _ac(kok)
        D.is_kapat(sid, kok=kok)
        assert D.is_oku(sid, kok=kok) == ""
        assert D.aktif_id(kok=kok) is None


class TestListeKapat:
    def test_liste_ve_kapatma(self, tmp_path):
        kok = str(tmp_path)
        assert D.is_listele(kok=kok)["result"] == "İş yok"
        s1 = _ac(kok, baslik="Birinci")
        _ac(kok, baslik="Ikinci")
        assert D.aktif_id(kok=kok) is not None
        ozet = D.is_listele(kok=kok)["result"]
        assert "Birinci" in ozet and "Ikinci" in ozet
        D.is_kapat(s1, kok=kok)
        ozet2 = D.is_listele(kok=kok)["result"]
        assert "Birinci" not in ozet2 and "Ikinci" in ozet2

    def test_ac_komutu_tanima(self):
        assert D.ac_komutu_mu("Vixrex icin musteri bul, bunu takip et")
        assert D.ac_komutu_mu("su isi ac: temizlik")
        assert not D.ac_komutu_mu("masaüstünde ne var")
        assert not D.ac_komutu_mu("merhaba")
        assert not D.ac_komutu_mu("")
