"""tests/test_faz3b.py — Uyuyan organlar canli hatta (FAZ-3b).

Baglantilar: sohbetten is ac/liste/onayla araclari, zamanlayici
saatinde kuyrugu kosturur, gunluk karta Gundem + Isler satiri duser,
defter yokken baglama inanc gürültüsü enjekte edilmez, juri kapaliyken
kota yemez.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chat  # once tam paket (dairesel import onlemi)
import _chat_legacy as L


def _izole_kuyruk(monkeypatch, tmp_path):
    import tools.is_kuyrugu as _k
    dosya = str(tmp_path / "kuyruk.json")
    monkeypatch.setattr(_k, "KUYRUK_DOSYA", dosya)
    if hasattr(_k, "_tekil"):
        monkeypatch.delattr(_k, "_tekil")
    return dosya


class TestIsAraclari:
    def test_tanim_izin_taninmis(self):
        from tools.definitions import TOOLS, EXTENDED_TETIKLERI
        from tools.permissions import ETIKETLER, calistirilabilir_mi
        from chat.tools import TANINMIS_TOOLLAR
        adlar = {t["function"]["name"] for t in TOOLS}
        for ad in ("is_ac", "is_liste", "is_onayla"):
            assert ad in adlar
            assert ad in ETIKETLER
            assert ad in TANINMIS_TOOLLAR
            assert ad in EXTENDED_TETIKLERI
        assert calistirilabilir_mi("is_liste") is True

    def test_ac_liste_onayla(self, monkeypatch, tmp_path):
        _izole_kuyruk(monkeypatch, tmp_path)
        from tools.executor import calistir
        r = calistir("is_ac", {"baslik": "sabah bakimi",
                               "adimlar": "gorev_hatirlat, proje_yokla"},
                     knowledge_dir="kd", gorevler_file="gf")
        assert "result" in r and "is-" in r["result"]
        r = calistir("is_liste", {}, knowledge_dir="kd", gorevler_file="gf")
        assert "sabah bakimi" in r["result"]
        is_id = r["result"].split()[1]
        r = calistir("is_onayla", {"is_id": is_id},
                     knowledge_dir="kd", gorevler_file="gf")
        assert "result" in r
        r = calistir("is_onayla", {"is_id": "is-000999"},
                     knowledge_dir="kd", gorevler_file="gf")
        assert "error" in r

    def test_bilinmeyen_adim_reddedilir(self, monkeypatch, tmp_path):
        _izole_kuyruk(monkeypatch, tmp_path)
        from tools.is_kuyrugu import is_ac
        r = is_ac("x", "roket_ucur")
        assert "error" in r and "gorev_hatirlat" in r["error"]

    def test_kitaplik_adimlari_kosar(self, tmp_path):
        from tools.is_kuyrugu import IsKuyrugu, varsayilan_harita
        dosya = str(tmp_path / "k.json")
        k = IsKuyrugu(dosya)
        job = k.ekle("bakim", ["gorev_hatirlat", "proje_yokla"])
        rapor = k.kos_bekleyenleri(varsayilan_harita(), sure_butcesi=60)
        assert rapor["kosulan_is"][0]["sonuc"] == "bitti"
        assert k.al(job["id"])["durum"] == "bitti"


class TestKartEkleri:
    def test_bosken_satir_dusmez(self, tmp_path, monkeypatch):
        import tools.is_kuyrugu as _k

        class BosKuyruk:
            def liste(self):
                return []

        monkeypatch.setattr(_k, "IsKuyrugu", BosKuyruk)
        from tools.zamanlayici import _gunluk_ekler
        parcalar = ["selam"]
        assert _gunluk_ekler(parcalar,
                             kuyruk_dosya=str(tmp_path / "yok.json"),
                             defter_dir=str(tmp_path)) is False
        assert parcalar == ["selam"]

    def test_catlak_karta_duser(self, tmp_path, monkeypatch):
        import tools.is_kuyrugu as _k

        class BosKuyruk:
            def liste(self):
                return []

        monkeypatch.setattr(_k, "IsKuyrugu", BosKuyruk)
        from tools.gerilim import FayKuyrugu
        kyol = str(tmp_path / "fay.json")
        k = FayKuyrugu(kyol)
        k.catlak_ekle("deneme-konu", ("a", "b"), "deneme gerekce",
                       maliyet_seviyesi="yayinda", yayilma=1.0)
        defter = tmp_path / "defter"
        defter.mkdir()
        (defter / "cozum.md").write_text(
            "---\nkim: test\ntip: karar\nkonu: deneme-konu\n---\n"
            "deneme cozumu metni", encoding="utf-8")
        from tools.zamanlayici import _gunluk_ekler
        parcalar = ["selam"]
        assert _gunluk_ekler(parcalar, kuyruk_dosya=kyol,
                             defter_dir=str(defter)) is True
        metin = "\n".join(parcalar)
        assert "Gündem: deneme-konu" in metin
        assert "cozum.md" in metin


class TestBaglamVeJuri:
    def test_inanc_ozeti_defter_yokken_enjekte_edilmez(self, monkeypatch):
        # 2026-09-12 (P6, §11 kaydi): defter/ a359d8b ile kalkmisti;
        # dunya_ozet kalici "Dünya modeli boş" gürültüsü üretiyordu.
        # Davranis: defter yokken İnançlar bölümü modele GİTMEZ.
        monkeypatch.setattr(L, "_hafiza", False)
        monkeypatch.setattr(L, "_knowledge_cache", "kisa not")

        class Sahte:
            pass
        bilesenler = L.orkestra_bilesenleri(Sahte())
        blok = bilesenler["model_baglami"]()
        assert "İnançlar:" not in blok
        assert "kisa not" in blok

    def test_juri_kapaliyken_kota_yemez(self):
        import chat as _c

        class Sahte:
            def _bulut_zinciri(self):
                raise AssertionError("zincire dokunulmamali")

        bilesenler = L.orkestra_bilesenleri(Sahte())
        assert bilesenler["ek_adaylar"]("groq", [], arac_var=False) == []
