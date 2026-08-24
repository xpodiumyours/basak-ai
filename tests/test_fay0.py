"""tests/test_fay0.py — FAY-0 testleri: üç ölçen tanık + uydurmaya kapalı
çarpıştırıcı + tek kart.

FAY-0 kabul ölçütünün kod karşılığı:
- tanık iddiaları YALNIZCA araç çıktısından gelir (model üretmez)
- modelin işaret ettiği tanık adı gerçek listede yoksa çatışma REDDEDİLİR
  (uydurma çelişki karta giremez)
- kart tek parça, kanıtlı, kaynak etiketli
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.fay import (_yanit_coz, carpistir, fay0_karti,
                       kart_olustur, tanik_iddialari)


def sahte_calistir(yanitlar):
    cagrilan = []

    def calistir(ad, args, *a, **kw):
        cagrilan.append(ad)
        return yanitlar[ad]
    return calistir, cagrilan


def uc_tanik():
    return {"git_durum": {"result": "Proje: vixrex Dal: main "
                                      "Son commit: dun"},
            "belge_ara": {"result": "GOREV_LISTESI.md:84: vitrin plani "
                                    "tamamlandi"},
            "dosya_bilgi": {"result": "app.py | 12 KB | bugun degisti"}}


class TestTaniklar:
    def test_uc_tanik_iddia_uretir(self):
        calistir, cagrilan = sahte_calistir(uc_tanik())
        iddialar = tanik_iddialari("vixrex", "vitrin", "app.py", calistir)
        assert [i["tanik"] for i in iddialar] == ["git", "belge", "dosya"]
        assert set(cagrilan) <= {"git_durum", "belge_ara", "dosya_bilgi"}

    def test_basarisiz_tanik_atlanir(self):
        yanitlar = uc_tanik()
        yanitlar["belge_ara"] = {"error": "bulunamadi"}
        calistir, _ = sahte_calistir(yanitlar)
        iddialar = tanik_iddialari("vixrex", "vitrin", "app.py", calistir)
        assert [i["tanik"] for i in iddialar] == ["git", "dosya"]


class TestCarpistirici:
    def test_celisen_cifti_bulunur(self):
        iddialar = [{"tanik": "belge", "iddia": "plani tamamlandi"},
                    {"tanik": "git", "iddia": "12 dosya commit edilmemis"}]
        beyin = lambda m: {"content":
                           "[CELISIYOR] belge vs git: plan bitti diyor ama "
                           "commit yok"}
        sonuc = carpistir(iddialar, beyin)
        assert sonuc["cift"] == ("belge", "git")
        assert "commit" in sonuc["gerekce"]

    def test_uydurma_tanik_adi_reddedilir(self):
        """Model var olmayan bir kaynagi isaret ederse catisma SAYILMAZ —
        FAY-0'in uydurma-sifir kabul olcutunun kod karsiligi."""
        iddialar = [{"tanik": "belge", "iddia": "x"},
                    {"tanik": "git", "iddia": "y"}]
        beyin = lambda m: {"content":
                           "[CELISIYOR] canli vs hafiza: tutarsiz gorunuyor"}
        assert carpistir(iddialar, beyin) is None

    def test_sorun_yok_none_doner(self):
        iddialar = [{"tanik": "belge", "iddia": "a"},
                    {"tanik": "git", "iddia": "b"}]
        beyin = lambda m: {"content": "[SORUN YOK]"}
        assert carpistir(iddialar, beyin) is None

    def test_anlasilmayan_yanit_none_doner(self):
        iddialar = [{"tanik": "belge", "iddia": "a"},
                    {"tanik": "git", "iddia": "b"}]
        beyin = lambda m: {"content": "bence bir tutarsizlik olabilir belki"}
        assert carpistir(iddialar, beyin) is None

    def test_beyin_hata_verirse_none_doner(self):
        def patlak(m):
            raise RuntimeError("yerel model down")
        iddialar = [{"tanik": "belge", "iddia": "a"},
                    {"tanik": "git", "iddia": "b"}]
        assert carpistir(iddialar, patlak) is None


class TestKart:
    def test_kart_kanitli_ve_etiketli(self):
        iddialar = [{"tanik": "git",
                     "iddia": "12 dosya commit edilmemis"}]
        kart = kart_olustur("vixrex durumu", iddialar,
                            {"cift": ("git", "belge"),
                             "gerekce": "plan bitti deniyor"})
        assert kart.startswith("FAY — vixrex")
        assert "git diyor" in kart
        assert "CATISMA" in kart and "Soru:" in kart

    def test_catisma_yoksa_sade_kart(self):
        kart = kart_olustur("konu", [{"tanik": "git", "iddia": "temiz"}])
        assert "Belirgin catisma bulunamadi" in kart


class TestFay0UcUcu:
    def test_uctan_uca_kart(self):
        calistir, cagrilan = sahte_calistir({
            "git_durum": {"result": "Dal: main, 12 dosya commit edilmemis"},
            "belge_ara": {"result": "GOREV_LISTESI.md:84: plan tamamlandi"},
            "dosya_bilgi": {"error": "Dosya bulunamadi: app.py"},
        })
        def beyin(m):
            return {"content": "[SORUN YOK]"}

        sonuc = fay0_karti("vixrex", "vitrin plani", "app.py",
                           calistir, beyin_cevapla=beyin,
                           konu="VixRex su an nerede")
        assert "FAY — VixRex su an nerede" in sonuc["kart"]
        assert sonuc["catisma"] is None
        # yalnizca salt-okunur olcum araclari kosuldu
        assert set(cagrilan) <= {"git_durum", "belge_ara", "dosya_bilgi"}
