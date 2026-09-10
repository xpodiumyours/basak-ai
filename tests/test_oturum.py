"""tests/test_oturum.py — Eski sohbet listesi testleri (2026-09-10)."""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chat import oturum


def _sifirla(monkeypatch, tmp_path):
    dizin = tmp_path / "sohbetler"
    aktif = tmp_path / "aktif"
    monkeypatch.setattr(oturum, "DIZIN", str(dizin))
    monkeypatch.setattr(oturum, "AKTIF_DOSYA", str(aktif))
    return dizin


class TestOturum:
    def test_kaydet_ve_listele(self, monkeypatch, tmp_path):
        _sifirla(monkeypatch, tmp_path)
        oturum.kaydet_cift("merhaba", "selam Casper")
        oturum.kaydet_cift("nasilsin", "iyiyim")
        liste = oturum.liste()
        assert len(liste) == 1
        assert liste[0]["baslik"].startswith("merhaba")
        assert liste[0]["adet"] == 4

    def test_yeni_arsivler(self, monkeypatch, tmp_path):
        _sifirla(monkeypatch, tmp_path)
        oturum.kaydet_cift("ilk soru", "ilk cevap")
        eski_id = oturum.aktif_id()
        oturum.yeni([{"role": "user", "content": "ilk soru"},
                     {"role": "assistant", "content": "ilk cevap"}])
        assert oturum.aktif_id() != eski_id
        assert len(oturum.liste()) == 1

    def test_bos_yenide_arsiv_yok(self, monkeypatch, tmp_path):
        _sifirla(monkeypatch, tmp_path)
        oturum.yeni([])
        assert oturum.liste() == []

    def test_ac_ve_sil(self, monkeypatch, tmp_path):
        _sifirla(monkeypatch, tmp_path)
        oturum.kaydet_cift("soru", "cevap")
        sid = oturum.liste()[0]["id"]
        assert oturum.ac(sid)[0]["content"] == "soru"
        assert oturum.sil(sid) is True
        assert oturum.liste() == []
        assert oturum.ac(sid) is None
