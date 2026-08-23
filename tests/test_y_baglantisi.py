"""tests/test_y_baglantisi.py — [Y] kanıt bağlantısı (sözcük çapası) testleri.

2026-08-23'te Casper'in buldugu acik: [Y] cumlesi, cevapta HERHANGI bir
[Ö] ayakta kaldigi icin geciyordu; gercek git ciktisinin altina alakasiz
bir iddia "[Y]" rozetiyle sizabiliyordu.

Yeni kural: hayatta kalan [Ö] varsa, her [Y] o ölçüm alıntısıyla en az
bir içerik kökü paylaşmalıdır (Türkçe eklerine toleranslı). Paylaşmayan
[Y] elenir. Salt-[A] durumunda denetim uygulanmaz (alinti belgeyi
kanitlar, iddia baglamdaki genis notlardan gelebilir).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from olcu import YEDEK_CUMLE, _baglanti_var_mi, cikis_kapisi

OLCUMLER = [("git_durum", "Proje: vixrex Dal: main Son commit: 20da1a7")]


class TestBaglanti:
    def test_baglanti_yok_alakasiz_iddia_olur(self):
        """Gerçek ölçüm + alakasız [Y] → [Y] elenir."""
        metin = ('[Y] Istanbulda hava bugun yagmurlu.\n'
                 '[Ö1] git_durum "Dal: main"')
        temiz, rapor = cikis_kapisi(metin, olcumler=OLCUMLER)
        assert "badge::Y::" not in temiz
        assert any("baglantisi yok" in r for r in rapor)
        assert temiz.endswith(YEDEK_CUMLE)

    def test_kok_eslesmesi_yeterli(self):
        """dal ↔ dalinda gibi ek farkları bağlantı sayılır."""
        assert _baglanti_var_mi(
            "[Y] VixRex main dalinda calisiyor.",
            ["Dal: main"]) is True

    def test_baglantiyi_yasan_Y_gecer(self):
        metin = ('[Y] VixRex su an main dalinda.\n'
                 '[Ö1] git_durum "Dal: main"')
        temiz, rapor = cikis_kapisi(metin, olcumler=OLCUMLER)
        assert "badge::Y::" in temiz and rapor == []

    def test_hash_capasi_baglanti_sayar(self):
        assert _baglanti_var_mi(
            "[Y] Son degisiklik 20da1a7 numarali commit.",
            ["Son commit: 20da1a7"]) is True


class TestKarisik:
    def test_biri_bagli_biri_degilse_sadece_baglis_kalir(self):
        metin = ('[Y] VixRex main dalinda duruyor.\n'
                 '[Y] Ayrica borsada gun dususle kapandi.\n'
                 '[Ö1] git_durum "Dal: main"')
        temiz, rapor = cikis_kapisi(metin, olcumler=OLCUMLER)
        assert temiz.count("badge::Y::") == 1
        assert "borsa" not in temiz
        assert len(rapor) == 1

    def test_olcum_duserse_baglantisizlik_denetlenmez_hepsi_duser(self):
        """Hiç [Ö] ayakta kalmazsa eski kural işler: tüm [Y] düşer."""
        metin = ('[Y] Istanbulda hava yagmurlu.\n'
                 '[Ö1] git_durum "Dal: olmayan-dal"')
        temiz, rapor = cikis_kapisi(metin, olcumler=OLCUMLER)
        assert temiz == YEDEK_CUMLE and len(rapor) == 2


class TestSaltAlintiSerbesti:
    def test_a_alintisiyla_baglantisiz_Y_yasar(self):
        """[A] belgeyi kanıtlar; iddia bağlamdaki notlardan gelebilir —
        sözcük çapası ARA NM AZ (Çaykur vakası, test_olcu.py'deki sözleşme)."""
        metin = ('[Y] Notlarima gore favori cayim Caykur.\n'
                 '[A] AGENTS.md "Basak — tamamen yerel calisan"')
        temiz, rapor = cikis_kapisi(metin)
        assert "badge::Y::" in temiz and rapor == []
