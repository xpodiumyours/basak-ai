"""tests/test_olcu2.py — [B] eylem iddiası denetimi testleri.

2026-08-23'te ölçülen gerçek arıza: model yapmadığı işi
"[B] Bu bilgi ... deftere kaydedildi" diyebiliyordu; [B] kapıdan
denetimsiz geçiyordu. Bu testler kuralı sabitler:
eylem iddiası taşıyan [B], ilgili araç O TURDA hatasız koşmadıysa ölür.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from olcu import YEDEK_CUMLE, _b_eylem_denetimi, cikis_kapisi

# Gerçek olay cümlesi (defter/basak-bekleyen-isler-sirasi.md)
OLAY_CUMLESI = "[B] Bu bilgi VixRex son commit başlığıyla deftere kaydedildi."


class TestOlayCumlesi:
    def test_olay_cumlesi_aracsiz_olur(self):
        """Araç hiç koşmadıysa 'deftere kaydedildi' yalanı elenir."""
        temiz, rapor = cikis_kapisi(OLAY_CUMLESI, olcumler=[])
        assert temiz == YEDEK_CUMLE
        assert len(rapor) == 1 and "eylem" in rapor[0]

    def test_olay_cumlesi_dogru_arac_yasar(self):
        """deftere_kaydet gerçekten koştuysa cümle yaşar."""
        temiz, rapor = cikis_kapisi(
            OLAY_CUMLESI,
            olcumler=[("deftere_kaydet", "Kayit eklendi: vixrex-commit")])
        assert "deftere kaydedildi" in temiz and rapor == []

    def test_hata_donduren_arac_kanit_sayilmaz(self):
        """Aracın çıktısı 'Hata: ...' ise iddia kanıtsızdır."""
        temiz, _ = cikis_kapisi(
            OLAY_CUMLESI,
            olcumler=[("deftere_kaydet", "Hata: klasor yazilamadi")])
        assert temiz == YEDEK_CUMLE


class TestAracEsleme:
    def test_defter_iddiasina_save_note_yeterli_degil(self):
        """'Deftere kaydedildi' yalnızca deftere_kaydet ile kanıtlanır."""
        engel = _b_eylem_denetimi(
            "[B] Not deftere yazildi.",
            [("save_note", "Not kaydedildi")])
        assert engel is True

    def test_not_iddiasi_save_note_ile_yasar(self):
        engel = _b_eylem_denetimi(
            "[B] Hatirlatman not olarak kaydedildi.",
            [("save_note", "Not kaydedildi")])
        assert engel is False

    def test_gorev_ekleme_add_task_gerekir(self):
        engel = _b_eylem_denetimi(
            "[B] Gorev listesine eklendi: sut al.",
            [])
        assert engel is True
        engel2 = _b_eylem_denetimi(
            "[B] Gorev listesine eklendi: sut al.",
            [("add_task", "Gorev eklendi")])
        assert engel2 is False

    def test_tamamlama_complete_task_gerekir(self):
        engel = _b_eylem_denetimi("[B] Gorevi tamamladim.", [])
        assert engel is True
        engel2 = _b_eylem_denetimi(
            "[B] Gorevi tamamladim.",
            [("complete_task", "Gorev tamamlandi")])
        assert engel2 is False

    def test_silme_ve_gonderme_hicbir_aracla_kanitlanamaz(self):
        """Silme/gönderme aracı yok — her koşulda elenir."""
        araclar = [("deftere_kaydet", "ok"), ("add_task", "ok"),
                   ("write_file_tool", "ok")]
        assert _b_eylem_denetimi("[B] Eski kaydi sildim.", araclar) is True
        assert _b_eylem_denetimi("[B] Mail gonderildi.", araclar) is True


class TestYanlissPozitifKorumasi:
    def test_olumsuz_eylem_iddia_degildir(self):
        """'Eklenmedi' doğru söyleyen elenmez."""
        engel = _b_eylem_denetimi(
            "[B] Boyle bir kayit daha once eklenmedi.",
            [("save_note", "ok")])
        assert engel is False
        engel2 = _b_eylem_denetimi(
            "[B] Gorev eklenmedi, boyle bir is yok.", [])
        assert engel2 is False

    def test_sohbet_b_cumlesi_etkilenmez(self):
        engel = _b_eylem_denetimi(
            "[B] Bunun olcumu su an yapilamiyor, gelecege donuk bir soru.",
            [])
        assert engel is False

    def test_isaretsiz_sohbet_oldugu_gibi_gecer(self):
        temiz, rapor = cikis_kapisi("Kaydedildi diye bir sey demiyorum, sohbet.")
        assert temiz == "Kaydedildi diye bir sey demiyorum, sohbet."
        assert rapor == []


class TestAkis:
    def test_elenince_kalan_cumleler_sagkalir(self):
        metin = ("[Y] VixRex son commit bugun yapildi.\n"
                 "[Ö1] git_durum \"Son commit: 20da1a7\"\n"
                 + OLAY_CUMLESI)
        temiz, rapor = cikis_kapisi(
            metin,
            olcumler=[("git_durum",
                       "Proje: vixrex Dal: main Son commit: 20da1a7")])
        assert "badge::Ö::" in temiz
        assert "badge::Y::" in temiz
        assert "deftere kaydedildi" not in temiz
        assert len(rapor) == 1 and temiz.endswith(YEDEK_CUMLE)

    def test_eski_b_davranisi_korundu(self):
        """Eylem iddiası taşımayan [B] eskisi gibi yaşar."""
        temiz, rapor = cikis_kapisi("[B] Bunu bilmiyorum.")
        assert "bilmiyorum" in temiz and rapor == []
