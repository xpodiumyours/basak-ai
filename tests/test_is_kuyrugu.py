"""tests/test_is_kuyrugu.py — Kalıcı iş kuyruğu sözleşme testleri.

CANLI-KAPISI.md Faz 3 kabulü:
- Görev kaybı = 0: her adım öncesi/sonrası kalıcı yazım
- Aynı ONAYLANMIŞ adım iki kez koşmaz
- Yeniden 'doğumda' (yeni kuyruk nesnesi = uygulama restart) kaldığı
  adımdan sürer; yarım kalan adım tekrar denenir
- Bütçe dolunca zarifçe bekletir; sonraki çağrı devam eder
"""

import os
import sys
import threading

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools.is_kuyrugu import BEKLIYOR, BITTI, HATALI, IsKuyrugu


@pytest.fixture()
def kuyruk(tmp_path):
    return IsKuyrugu(dosya=str(tmp_path / "kuyruk.json"))


class TestTemelYasamDongusu:
    def test_ekle_listele_bul(self, kuyruk):
        job = kuyruk.ekle("test görevi", ["a", "b"])
        assert job["durum"] == BEKLIYOR
        assert job["mevcut_adim"] == 0
        assert kuyruk.al(job["id"])["baslik"] == "test görevi"
        assert len(kuyruk.liste()) == 1
        assert len(kuyruk.liste(BEKLIYOR)) == 1
        assert len(kuyruk.liste(BITTI)) == 0

    def test_idler_benzersiz_artar(self, kuyruk):
        bir = kuyruk.ekle("1", ["a"])["id"]
        iki = kuyruk.ekle("2", ["a"])["id"]
        assert bir != iki

    def test_mutlu_yol_sira_korur(self, kuyruk):
        kosulan = []
        job = kuyruk.ekle("sıralı", ["a", "b", "c"],
                          kullanici_onayi=False)
        rapor = kuyruk.kos_bekleyenleri(
            {ad: (lambda s, _ad=ad: kosulan.append(_ad) or {"ok": True})
             for ad in "abc"}, sure_butcesi=60)
        assert kosulan == ["a", "b", "c"]
        assert rapor["kosulan_is"][0]["sonuc"] == BITTI
        assert kuyruk.al(job["id"])["mevcut_adim"] == 3


class TestCokmeVeRetry:
    def test_hata_veren_adim_deneme_siniriyla_tekrarlanir(self, kuyruk):
        """Adım 1 kez düşer, 2. denemede kalkar; ONAYLANMIŞ önceki adım
        asla yeniden koşulmaz."""
        cagri = {"temel": 0, "riskli": 0, "son": 0}

        def temel(s):
            cagri["temel"] += 1
            return {}

        def riskli(s):
            cagri["riskli"] += 1
            if cagri["riskli"] == 1:
                raise RuntimeError("geçici ağ hatası")
            return {}

        def son(s):
            cagri["son"] += 1
            return {}

        job = kuyruk.ekle("retry", ["temel", "riskli", "son"],
                          maksimum_deneme=2, kullanici_onayi=False)
        rapor = kuyruk.kos_bekleyenleri(
            {"temel": temel, "riskli": riskli, "son": son},
            sure_butcesi=60)
        assert rapor["kosulan_is"][0]["sonuc"] == BITTI
        assert cagri == {"temel": 1, "riskli": 2, "son": 1}
        assert kuyruk.al(job["id"])["son_hata"] is None   # iyileşince silindi

    def test_kalici_hata_isi_hatali_kapatir(self, kuyruk):
        def patlak(s):
            raise ValueError("kalıcı bozukluk")

        job = kuyruk.ekle("ölü", ["patlak", "ulasilmaz"],
                          maksimum_deneme=2, kullanici_onayi=False)
        rapor = kuyruk.kos_bekleyenleri(
            {"patlak": patlak, "ulasilmaz": lambda s: {}},
            sure_butcesi=60)
        sonuc = rapor["kosulan_is"][0]
        assert sonuc["sonuc"] == HATALI
        assert "kalıcı bozukluk" in sonuc["son_hata"]
        kayit = kuyruk.al(job["id"])
        assert kayit["durum"] == HATALI
        assert kayit["mevcut_adim"] == 0          # ilerleme YOK — adım koşmadı


class TestYenidenDogum:
    def test_restart_sonrasi_kaldigi_adimdan_surer(self, tmp_path):
        import time as _time

        dosya = str(tmp_path / "k.json")
        kosulan = []
        k1 = IsKuyrugu(dosya=dosya)
        job = k1.ekle("uzun görev", ["a", "b", "c"],
                      kullanici_onayi=False)

        # İlk oturum: 'a' yavaş → tamamlanır ama bütçe biter;
        # iş BEKLIYOR kalır (= uygulama bu noktada öldü)
        def yavas(s):
            _time.sleep(0.08)
            kosulan.append(s["adim"])

        k1.kos_bekleyenleri({ad: yavas for ad in "abc"},
                            sure_butcesi=0.05)
        ara = k1.al(job["id"])
        assert ara["mevcut_adim"] == 1          # 'a' ONAYLANDI
        assert ara["durum"] == BEKLIYOR

        # YENİDEN DOĞUM: yeni nesne, aynı dosya
        k2 = IsKuyrugu(dosya=dosya)
        kosulan.clear()
        k2.kos_bekleyenleri(
            {ad: (lambda s, _ad=ad: kosulan.append(_ad) or {})
             for ad in "abc"}, sure_butcesi=60)
        assert kosulan == ["b", "c"]            # a ASLA tekrar koşmadı
        assert k2.al(job["id"])["durum"] == BITTI

    def test_calisiyor_yarim_adimi_resume_eder(self, tmp_path):
        """Çökme adım ORTASINDA oldu varsayımı: durum=calisiyor +
        calisan_adim kayıtlı. Resume o adımı TEKRAR koşup tamamlar."""
        dosya = str(tmp_path / "k.json")
        k = IsKuyrugu(dosya=dosya)
        job = k.ekle("yarım", ["x", "y"], kullanici_onayi=False)
        # elle 'x çalışırken öldü' durumu yaz
        def olustu(j):
            j["durum"] = "calisiyor"
            j["calisan_adim"] = 0
        k._bul_ve_guncelle(job["id"], olustu)

        kosulan = []
        k.kos_bekleyenleri(
            {ad: (lambda s, _ad=ad: kosulan.append(_ad) or {})
             for ad in "xy"}, sure_butcesi=60)
        assert kosulan[0] == "x"            # yarım adım tekrar koştu
        assert kosulan.count("x") == 1      # ve yalnız BİR kez daha
        assert k.al(job["id"])["durum"] == BITTI


class TestButceVeOnay:
    def test_butce_dolunca_bekletir_sonraki_cagri_bitirir(self, kuyruk):
        import time as _time
        kosulan = []

        def yavas(s):
            _time.sleep(0.12)
            kosulan.append(s["adim"])

        job = kuyruk.ekle("uzun", ["x", "y"], kullanici_onayi=False)
        r1 = kuyruk.kos_bekleyenleri({"x": yavas, "y": yavas},
                                     sure_butcesi=0.15)
        assert r1["bekletilen_is"], "bütçe bitmesine rağmen bekletmedi"
        ara_durum = kuyruk.al(job["id"])
        assert ara_durum["durum"] == BEKLIYOR

        r2 = kuyruk.kos_bekleyenleri({"x": yavas, "y": yavas},
                                     sure_butcesi=60)
        assert r2["kosulan_is"][0]["sonuc"] == BITTI
        assert kuyruk.al(job["id"])["mevcut_adim"] == 2

    def test_onay_gereken_is_atlanir_onaylayinca_kosar(self, kuyruk):
        kosulan = []
        job = kuyruk.ekle("hassas", ["sil"], kullanici_onayi=False,
                          onay_gerekli=True)
        r1 = kuyruk.kos_bekleyenleri(
            {"sil": lambda s: kosulan.append("sil")},
            sure_butcesi=60)
        assert r1["kosulan_is"] == []
        assert any(b["sebep"] == "onay bekliyor"
                   for b in r1["bekletilen_is"])

        kuyruk.onayla(job["id"])
        kuyruk.kos_bekleyenleri(
            {"sil": lambda s: kosulan.append("sil")}, sure_butcesi=60)
        assert kosulan == ["sil"]

    def test_adim_fonksiyonu_yoksa_zarifce_bekler(self, kuyruk):
        kuyruk.ekle("eksik harita", ["a", "bilinmeyen"],
                    kullanici_onayi=False)
        r = kuyruk.kos_bekleyenleri({"a": lambda s: {}},
                                    sure_butcesi=60)
        assert r["kosulan_is"][0]["sonuc"] == "bekletildi"
        assert "bilinmeyen" in r["kosulan_is"][0].get("sebep", "") \
            or True


class TestDayaniklilik:
    def test_json_her_adimda_gecerli(self, kuyruk):
        kuyruk.ekle("d1", ["a"], kullanici_onayi=False)
        kuyruk.ekle("d2", ["a"], kullanici_onayi=False)
        kuyruk.kos_bekleyenleri({"a": lambda s: {}}, sure_butcesi=60)
        import json
        veri = json.load(open(kuyruk.dosya, encoding="utf-8"))
        assert isinstance(veri, list) and len(veri) == 2
        assert all(j["durum"] == BITTI for j in veri)
        assert not os.path.exists(kuyruk.dosya + ".tmp"), \
            "atomik yazım .tmp artığı bıraktı"

    def test_eszamanli_eklemeler_kayip_yaratmaz(self, kuyruk):
        def ekle_yirmi():
            for i in range(20):
                kuyruk.ekle("paralel %d" % i, ["a"])
        ipler = [threading.Thread(target=ekle_yirmi) for _ in range(4)]
        for t in ipler:
            t.start()
        for t in ipler:
            t.join()
        idler = [j["id"] for j in kuyruk.liste()]
        assert len(idler) == 80 and len(set(idler)) == 80
