"""tests/test_log_kirmalama.py — arac.log kırmalama testleri.

2026-08-24'te Casper'in bulgusu: tool_logger ilk 200 karakteri ham
yazıyordu; save_note içeriği, dosya okuma sonucu veya URL içindeki
anahtar loga düşebiliyordu. Kural: hassas alan değer yerine uzunluk;
anahtar/token desenleri her satırda kirmalanır.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.tool_logger import _kirmala, _ozet_args, _ozet_sonuc


def satir_yakala(monkeypatch, tmp_path, tool, args, sonuc):
    from tools import tool_logger as tl
    tl.log_tool_call(tool, args, sonuc, str(tmp_path))
    return open(tmp_path / "arac.log", encoding="utf-8").read()


class TestArgMaskesi:
    def test_save_note_icergi_loga_girmez(self, monkeypatch, tmp_path):
        satirlar = satir_yakala(
            monkeypatch, tmp_path,
            "save_note",
            {"title": "banka şifrem", "content": "kredi kartı 5555..."},
            {"result": "Not kaydedildi"})
        assert "banka" not in satirlar and "5555" not in satirlar
        import re as _re
        assert _re.search(r"<\d+ karakter>", satirlar)  # uzunluk bilgisi kalir

    def test_deftere_kaydet_icerigi_gizlenir(self, monkeypatch, tmp_path):
        satirlar = satir_yakala(
            monkeypatch, tmp_path,
            "deftere_kaydet",
            {"title": "ozel", "content": "kişisel sağlık bilgi"},
            {"result": "Kayit eklendi"})
        assert "sağlık" not in satirlar and "kişisel" not in satirlar

    def test_write_file_content_gizli_path_gorunur(self, monkeypatch, tmp_path):
        satirlar = satir_yakala(
            monkeypatch, tmp_path,
            "write_file_tool",
            {"path": "knowledge/not.md", "content": "gizli gövde"},
            {"result": "Dosya yazıldı"})
        assert "gizli gövde" not in satirlar
        assert "knowledge/not.md" in satirlar

    def test_duz_arac_argumani_okunur_kalir(self, monkeypatch, tmp_path):
        """Debug degeri: gizli olmayan argümanlar aynen görünür."""
        satirlar = satir_yakala(
            monkeypatch, tmp_path,
            "git_durum", {"proje": "vixrex"}, {"result": "Dal: main"})
        assert "'proje'" in satirlar and "Dal: main" in satirlar


class TestSonucMaskesi:
    def test_read_file_sonucu_govdesi_gizlenir(self, monkeypatch, tmp_path):
        satirlar = satir_yakala(
            monkeypatch, tmp_path,
            "read_file", {"path": "knowledge/x.md"},
            {"result": "MAHSUS IÇERIK 1234567890"})
        assert "MAHSUS" not in satirlar
        assert "karakter gizli" in satirlar

    def test_hata_mesaji_halen_gorunur(self, monkeypatch, tmp_path):
        satirlar = satir_yakala(
            monkeypatch, tmp_path,
            "read_file", {"path": "knowledge/yok.md"},
            {"error": "Dosya bulunamadı"})
        assert "Dosya bulunamadı" in satirlar


class TestDesenKirmalama:
    def test_api_key_deseni_maskelenir(self):
        temiz = _kirmala('sorgu: api_key=abcd1234efgh hava')
        assert "abcd1234efgh" not in temiz and "***" in temiz

    def test_sk_anahtari_maskelenir(self):
        assert "sk-abc123def456" not in _kirmala("key sk-abc123def456")

    def test_bearer_maskelenir(self):
        temiz = _kirmala("Authorization: Bearer abc.def.ghi")
        assert "abc.def.ghi" not in temiz

    def test_normal_metin_degismez(self):
        metin = "VixRex main dalinda, son commit dun"
        assert _kirmala(metin) == metin
