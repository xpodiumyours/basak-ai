"""tests/test_icerik_ara.py — ARAC-PLANI Is 4: ozyinelemeli icerik arama.

Sozlesme:
- Alt klasorlere iner (belge_ara'nin kor noktasi).
- Kara listedeki dosya HIC acilmaz; cikti maskelenir (_kirmala).
- Kabul kaniti: sir degeri ciktida GORUNMEZ.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import calistir, olcum
from tools.definitions import TANINMIS_TOOLLAR

GIZLI = "SUPABASE_KEY=sb-secret-ABC123XYZ"


def _proje(tmp_path):
    kok = tmp_path / "proj"
    (kok / "alt").mkdir(parents=True)
    (kok / "alt" / "not.md").write_text("matris karari burada\n", encoding="utf-8")
    (kok / ".env.local").write_text(GIZLI + "\n", encoding="utf-8")
    nm = kok / "node_modules" / "paket"
    nm.mkdir(parents=True)
    (nm / "kod.js").write_text("matris gomulu\n", encoding="utf-8")
    olcum.PROJELER["tmp-proje"] = str(kok)
    return kok


class TestUcYer:
    def test_beyaz_listede(self):
        assert "icerik_ara" in TANINMIS_TOOLLAR

    def test_durum_etiketi_var(self):
        from chat.tools import DURUM_METNI
        assert "icerik_ara" in DURUM_METNI


class TestArama:
    def test_alt_klasoru_bulur(self, tmp_path):
        _proje(tmp_path)
        try:
            r = olcum.icerik_ara("tmp-proje", "matris")
            assert "result" in r, r
            assert "alt" in r["result"] and "not.md" in r["result"]
        finally:
            del olcum.PROJELER["tmp-proje"]

    def test_node_modules_atlanir(self, tmp_path):
        _proje(tmp_path)
        try:
            r = olcum.icerik_ara("tmp-proje", "gomulu")
            assert "error" in r, r
        finally:
            del olcum.PROJELER["tmp-proje"]

    def test_sir_acilmaz_ve_gorunmez(self, tmp_path):
        # Kabul kaniti: .env.local'deki deger ciktida YOK.
        _proje(tmp_path)
        try:
            r = olcum.icerik_ara("tmp-proje", "sb-secret")
            metin = r.get("result", "")
            assert "sb-secret-ABC123XYZ" not in metin
            assert "SUPABASE_KEY" not in metin or "***" in metin
        finally:
            del olcum.PROJELER["tmp-proje"]

    def test_uzanti_suzgeci(self, tmp_path):
        _proje(tmp_path)
        try:
            r = olcum.icerik_ara("tmp-proje", "matris", uzanti=".js")
            assert "error" in r  # .js yalniz node_modules'te (atlanir)
            r = olcum.icerik_ara("tmp-proje", "matris", uzanti="md")
            assert "result" in r
        finally:
            del olcum.PROJELER["tmp-proje"]

    def test_bilinmeyen_proje(self):
        assert "error" in olcum.icerik_ara("yok-boyle-proje", "x")

    def test_calistir_hatti(self, tmp_path):
        _proje(tmp_path)
        try:
            r = calistir("icerik_ara", {"proje": "basak", "sorgu": "xyzzqy"})
            assert isinstance(r, dict)
        finally:
            del olcum.PROJELER["tmp-proje"]


class TestKirmala:
    def test_desenler_maskelenir(self):
        for ham in ("gsk_0AbwzAVVpXLpjBY2nqFi",
                    "nvapi-C5ugoHA6EJmTJbWRk",
                    "Bearer token123",
                    "eyJhbGciOiJIUzI1NiJ9",
                    'api_key = "gizli-deger"',
                    "parola: 12345"):
            maskeli = olcum._kirmala(ham)
            assert "gizli-deger" not in maskeli
            assert "***" in maskeli, ham
        assert "12345" not in olcum._kirmala("parola: 12345")
