"""tests/test_gerceklik_kapisi.py — İşaretsiz serbest geçişin sınırlandırılması.

2026-08-23'te Casper'in buldugu acik: cevapta HIC isaret yoksa kapı metni
"sohbet" varsayimiyla denetimsiz geciriyordu; model isaretsiz uydurma olgu
yazabiliyordu.

Yeni kural:
- Araç koşan turda serbest geçiş YOK — tüm cümleler denetlenir.
- Araçsız turda düz sohbet yaşar; ama ölçü-alanı sinyali (proje adı,
  commit hash) veya eylem iddiası taşıyan işaretsiz cümle elenir.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from olcu import YEDEK_CUMLE, cikis_kapisi


class TestAracliTur:
    def test_olcum_turu_isaretsiz_gecemez(self):
        """Araç koştuysa işaretsiz cevap serbest geçmez."""
        temiz, rapor = cikis_kapisi(
            "Son is aksam tamamlandi, her sey yolunda.",
            olcumler=[("git_durum", "Proje: basak Dal: main")])
        assert temiz == YEDEK_CUMLE
        assert len(rapor) == 1 and "ölçüm turunda" in rapor[0]

    def test_karistik_cevapta_isaretli_yasar_isaretsiz_olur(self):
        temiz, rapor = cikis_kapisi(
            '[Ö1] git_durum "Dal: main"\nBu arada her sey harika gidiyor.',
            olcumler=[("git_durum", "Proje: vixrex Dal: main "
                                    "Son commit: 20da1a7")])
        assert "badge::Ö::" in temiz
        assert "harika" not in temiz
        assert len(rapor) == 1


class TestAraclsizTur:
    def test_duz_sohbet_yasar(self):
        metin = "Selam! Bugun cok yogun gecti, sen nasilsin?"
        temiz, rapor = cikis_kapisi(metin)
        assert rapor == []
        for parca in ("Selam!", "yogun gecti", "nasilsin?"):
            assert parca in temiz

    def test_proje_adlari_isaretsiz_gecemez(self):
        temiz, rapor = cikis_kapisi("VixRex su anda main dalinda, son commit dün.")
        assert temiz == YEDEK_CUMLE
        assert any("olcu/eylem" in r for r in rapor)

    def test_numera_match_ve_xses_da_yakalanir(self):
        for cumle in ("NumeraMatch'te iki modul kaldi.",
                      "Xses deposu temiz."):
            temiz, rapor = cikis_kapisi(cumle)
            assert temiz == YEDEK_CUMLE, cumle

    def test_commit_hash_isaretsiz_gecemez(self):
        temiz, _ = cikis_kapisi(
            "Son degisiklik 3ce42e3 hash'iyle geldi, stabil.")
        assert temiz == YEDEK_CUMLE

    def test_eylem_iddiasi_isaretsiz_gecemez(self):
        temiz, _ = cikis_kapisi("Bilgileri deftere kaydettim.")
        assert temiz == YEDEK_CUMLE

    def test_saat_ve_plan_sohbeti_yasar(self):
        """Yanlış pozitif koruması: sayı/saat/plan içeren sıradan konuşma
        ölçü sinyali değildir, yaşar."""
        metin = ("Yarin saat 15:00'te bulusaliriz, sonra aksam "
                 "beraber bakariz.")
        temiz, rapor = cikis_kapisi(metin)
        assert temiz == metin and rapor == []


class TestKaristikCevap:
    def test_tehlikeli_cumle_olur_sohbet_yasar(self):
        metin = ("Tabii hemen anlatayirim!\n"
                 "VixRex'in son commit'i dun aksham geldi.\n"
                 "Baska merak ettigin bir sey var mi?")
        temiz, rapor = cikis_kapisi(metin)
        assert "VixRex" not in temiz
        assert "merak ettigin" in temiz
        assert len(rapor) == 1 and temiz.endswith(YEDEK_CUMLE)
