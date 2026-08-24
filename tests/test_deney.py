"""tests/test_deney.py — DENEY-0 deney motoru tohumu testleri.

Kilitli hedefin "Deney Motoru" organinin ilk halkasi: hipotez
olculebilir deneye donusur; LLM karar vermez, cikti + kural karar verir.
Yalniz beyaz listeli salt-okunur araclar kosulabilir.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.deney import deney_yurut


def sahte_calistir(yanitlar):
    """arac adi -> sonuc sozlugu tablosuyla calistirici taklidi."""
    def calistir(ad, args, *a, **kw):
        return yanitlar[ad]
    return calistir


class TestIcerir:
    def test_desteklenir(self):
        rapor = deney_yurut(
            [{"iddia": "main dalindadir", "arac": "git_durum",
              "arguman": {"proje": "vixrex"},
              "kural": "icerir", "beklenen": "Dal: main"}],
            sahte_calistir({"git_durum": {"result":
                            "Proje: vixrex Dal: main"}}))
        assert rapor[0]["durum"] == "desteklendi"
        assert "Dal: main" in rapor[0]["kanit"]

    def test_elenir(self):
        rapor = deney_yurut(
            [{"iddia": "develop dalindadir", "arac": "git_durum",
              "arguman": {}, "kural": "icerir", "beklenen": "Dal: develop"}],
            sahte_calistir({"git_durum": {"result": "Dal: main"}}))
        assert rapor[0]["durum"] == "elenmis"


class TestEsik:
    def test_esik_ust_sayi_cikarir(self):
        rapor = deney_yurut(
            [{"iddia": "basari yuzde 80 ustu", "arac": "model_stats",
              "arguman": {}, "kural": "esik_ust", "beklenen": 80}],
            sahte_calistir({"model_stats": {"result":
                            "basari orani: %87.3 (42 cagri)"}}))
        assert rapor[0]["durum"] == "desteklendi"

    def test_esik_alt_elenir(self):
        rapor = deney_yurut(
            [{"iddia": "gecikme 100ms alti", "arac": "model_stats",
              "arguman": {}, "kural": "esik_alt", "beklenen": 100}],
            sahte_calistir({"model_stats": {"result":
                            "ortalama gecikme: 240 ms"}}))
        assert rapor[0]["durum"] == "elenmis"

    def test_sayi_yoksa_hata(self):
        rapor = deney_yurut(
            [{"iddia": "x", "arac": "list_tasks", "arguman": {},
              "kural": "esik_ust", "beklenen": 5}],
            sahte_calistir({"list_tasks": {"result": "sayisal veri yok"}}))
        assert rapor[0]["durum"] == "hata"


class TestGuvenlik:
    def test_beyaz_liste_disi_arac_reddedilir(self):
        cagrildi = []
        def calistir(ad, args, *a, **kw):
            cagrildi.append(ad)
            return {"result": "yazildi"}
        rapor = deney_yurut(
            [{"iddia": "dosya silindi", "arac": "write_file_tool",
              "arguman": {}, "kural": "yok", "beklenen": "x"}],
            calistir)
        assert rapor[0]["durum"] == "reddedildi"
        assert cagrildi == []   # araca HIC ulasilmadi

    def test_bilinmeyen_kural_hata(self):
        rapor = deney_yurut(
            [{"iddia": "x", "arac": "git_durum", "arguman": {},
              "kural": "uydurma", "beklenen": "x"}],
            sahte_calistir({}))
        assert rapor[0]["durum"] == "hata"


class TestAracHatasi:
    def test_arac_hatasi_rapora_hata_duser(self):
        rapor = deney_yurut(
            [{"iddia": "plan var mi", "arac": "belge_ara",
              "arguman": {"proje": "vixrex", "sorgu": "plan"},
              "kural": "icerir", "beklenen": "plan"}],
            sahte_calistir({"belge_ara": {"error": "belge bulunamadi"}}))
        assert rapor[0]["durum"] == "hata"
