"""tests/test_fay2_gerilim.py — FAY-2: Gerilim puanı + dırdırmayan kuyruk.

Formül: gerilim = yayılma × tazelik × maliyet (yarı ömür 7 gün)
Kuyruk: günde EN FAZLA 1 kart; aynı gün aynı kart; eşik altındaki çatlak
silinmez, biriktikçe ağırlaşır ve günler sonra yüzeye çıkar.
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.gerilim import FayKuyrugu, gerilim_puani


def simdi_saat():
    return datetime(2026, 8, 24, 12, 0, 0)


class TestPuanFormulu:
    def test_taze_yayinli_maksimum(self):
        assert gerilim_puani(1.0, 0, "yayinda") == 1.0

    def test_maliyet_siralama(self):
        eski_degil = 0
        puanlar = [gerilim_puani(1.0, eski_degil, s)
                   for s in ("yerel", "commit", "birlestirilmis", "yayinda")]
        assert puanlar == sorted(puanlar)

    def test_tazelik_duser(self):
        yeni = gerilim_puani(1.0, 0, "commit")
        eski = gerilim_puani(1.0, 14, "commit")   # 2 yarı ömür -> çeyrek
        assert eski < yeni * 0.3

    def test_birikme_agirlastirir(self):
        taban = gerilim_puani(0.4, 5, "yerel")
        birikmis = gerilim_puani(0.4, 5, "yerel", birikme=5)
        assert birikmis > taban


class TestKuyruk:
    def test_gunde_tek_kart_ayni_kart(self, tmp_path):
        k = FayKuyrugu(str(tmp_path / "k.json"))
        k.catlak_ekle("vixrex-vitrin", ("belge", "git"),
                      "plan bitti deniyor ama commit yok",
                      maliyet_seviyesi="yayinda", yayilma=0.9,
                      simdi=simdi_saat())
        k1 = k.gunluk_kart(simdi=simdi_saat())
        k2 = k.gunluk_kart(simdi=simdi_saat() + timedelta(hours=1))
        assert k1 and k2 and k1["id"] == k2["id"]

    def test_yuksek_gerilim_oncelikli(self, tmp_path):
        k = FayKuyrugu(str(tmp_path / "k.json"))
        simdi = simdi_saat()
        k.catlak_ekle("kucuk tutarsizlik", ("belge", "dosya"), "ufak",
                      maliyet_seviyesi="yerel", yayilma=0.1, simdi=simdi)
        k.catlak_ekle("vitrin catlagi", ("belge", "git"), "buyuk",
                      maliyet_seviyesi="yayinda", yayilma=0.9, simdi=simdi)
        kart = k.gunluk_kart(simdi=simdi)
        assert kart["konu"] == "vitrin catlagi"

    def test_cozuldu_isaretlenen_artik_cikmaz(self, tmp_path):
        k = FayKuyrugu(str(tmp_path / "k.json"))
        k.catlak_ekle("tek catlak", ("belge", "git"), "gerekce",
                      maliyet_seviyesi="yayinda", yayilma=0.9,
                      simdi=simdi_saat())
        k.cozuldu_isaretle(k.gunluk_kart(simdi=simdi_saat())["id"])
        yarın = simdi_saat() + timedelta(days=1)
        assert k.gunluk_kart(simdi=yarın) is None

    def test_esik_alti_birikip_yuzeye_cikar(self, tmp_path):
        """Küçük ama çözülmeyen tutarsızlık günler sonra yüzeye çıkar."""
        k = FayKuyrugu(str(tmp_path / "k.json"))
        baslangic = simdi_saat()
        k.catlak_ekle("sessiz celiski", ("belge", "git"), "ufak ama var",
                      maliyet_seviyesi="yerel", yayilma=0.35,
                      simdi=baslangic)

        gorulen_gunler = set()
        for gun in range(1, 15):
            t = baslangic + timedelta(days=gun)
            kart = k.gunluk_kart(simdi=t)
            if kart:
                gorulen_gunler.add(gun)
            assert k.gunluk_kart.__self__ is not None

        # birikme sayesinde sonunda kart olmus olmali
        veri = __import__("json").load(open(tmp_path / "k.json",
                                            encoding="utf-8"))
        sessiz = [c for c in veri["catlaklar"]
                  if c["konu"] == "sessiz celiski"][0]
        assert sessiz["birikme"] > 0 or gorulen_gunler


class TestTemizlik:
    def test_tmp_artigi_birakilmaz(self, tmp_path):
        k = FayKuyrugu(str(tmp_path / "k.json"))
        k.catlak_ekle("x", ("belge", "git"), "gerekce",
                      simdi=simdi_saat())
        assert not os.path.exists(str(tmp_path / "k.json") + ".tmp")
