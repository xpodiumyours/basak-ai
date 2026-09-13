"""tests/test_anlam_bulma.py — Anlamdan bulma (hibrit arama) guvencesi.

Sozlesme:
- Vektor varsa anlam benzeri bulunur (kelime tutmasa bile).
- Vektor yoksa/bozuksa kelime aramasi calismaya devam eder.
- Ag YOK — vektorler sahte (768 boyut, motor tablosuyla ayni).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.engine import HafizaMotoru


def _sahte_vektor(etiket):
    """Etikete gore yakin vektor uretir (768 boyut)."""
    v = [0.0] * 768
    v[0 if etiket == "elma" else 1] = 1.0
    return v


def _fn(metin):
    if "BOZUK" in metin:
        raise RuntimeError("servis yattı")
    return _sahte_vektor("elma" if metin.startswith("ELMA") else "armut")


def _motor(tmp_path):
    return HafizaMotoru(db_yolu=str(tmp_path / "a.db"), embed_fn=_fn)


class TestHibrit:
    def test_anlam_benzerini_kelimesiz_bulur(self, tmp_path):
        m = _motor(tmp_path)
        m.ekle("ELMA gunesli bahce duvari", kind="not", kaynak="t")
        m.ekle("ARMUT yagmurlu cadde lambasi", kind="not", kaynak="t")
        sonuc = m.ara("ELMA gece yarisi kosusu")
        assert sonuc and "ELMA" in sonuc[0]["text"]

    def test_vektor_hatasi_kelimeye_duser(self, tmp_path):
        m = _motor(tmp_path)
        m.ekle("ELMA gunesli bahce duvari", kind="not", kaynak="t")
        # Sorgu servisi bozar -> vektor yok; kelime yine bulur
        m2 = HafizaMotoru(db_yolu=str(tmp_path / "a.db"), embed_fn=_fn)
        sonuc = m2.ara("BOZUK gunesli bahce")
        assert any("ELMA" in s["text"] for s in sonuc)

    def test_yanlis_boyut_kayda_zarar_vermez(self, tmp_path):
        m = HafizaMotoru(db_yolu=str(tmp_path / "b.db"),
                         embed_fn=lambda t: [1.0, 2.0])
        m.ekle("kisa vektorlu not", kind="not", kaynak="t")
        satir = m.conn.execute(
            "SELECT has_vec FROM memories").fetchone()
        assert satir[0] == 0
        assert m.ara("kisa vektorlu") != []


class TestSaglayici:
    def test_anahtar_yoksa_none(self, monkeypatch):
        from brain import gemini_embed as ge
        monkeypatch.setattr(ge, "_anahtar_al", lambda: "")
        assert ge.vektor_al("merhaba") is None

    def test_bos_metin_none(self):
        from brain.gemini_embed import vektor_al
        assert vektor_al("   ") is None

    def test_anlam_fn_anahtarsiz_none(self, monkeypatch):
        from chat import context as cc
        from brain import gemini_embed as ge
        monkeypatch.setattr(ge, "_anahtar_al", lambda: "")
        assert cc._anlam_fn() is None


class TestUzayDamgasi:
    def test_temizleme_metni_korur(self, tmp_path):
        m = HafizaMotoru(db_yolu=str(tmp_path / "c.db"), embed_fn=_fn)
        m.ekle("ELMA saklanacak metin", kind="not", kaynak="t")
        assert m.conn.execute(
            "SELECT COUNT(*) FROM memories WHERE has_vec=1").fetchone()[0] == 1
        n = m.vektorleri_temizle()
        assert n == 1
        assert m.conn.execute(
            "SELECT COUNT(*) FROM memories").fetchone()[0] == 1
        assert m.conn.execute(
            "SELECT COUNT(*) FROM memories WHERE has_vec=1").fetchone()[0] == 0
        assert m.ara("saklanacak") != []  # kelime aramasi surer

    def test_damga_tutmazsa_doldurur(self, tmp_path, monkeypatch):
        from chat import context as cc
        m = HafizaMotoru(db_yolu=str(tmp_path / "d.db"), embed_fn=_fn)
        m.ekle("ELMA damgali metin", kind="not", kaynak="t")
        m.vektorleri_temizle()
        monkeypatch.setattr(cc, "VEKTOR_UZAYI", "test-uzay@1")
        temiz, doldu = cc._vektor_uzay_sagla(m)
        assert temiz == 0 and doldu == 1
        assert m.meta_al("embed_uzay", "") == "test-uzay@1"
        # Ikinci cagri: damga tutar, is yapmaz
        assert cc._vektor_uzay_sagla(m) == (0, 0)

    def test_fn_yoksa_elinmez(self, tmp_path):
        from chat import context as cc
        m = HafizaMotoru(db_yolu=str(tmp_path / "e.db"))
        assert cc._vektor_uzay_sagla(m) == (0, 0)
