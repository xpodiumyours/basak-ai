"""tests/test_yazma_araci.py — ARAC-PLANI Is 1: knowledge/ alti yazma.

Sozlesme:
- write_file_tool YALNIZ knowledge/ altina yazar (diskte dogrulanir).
- knowledge disi, kara liste (.env), bos yol/icerik REDDEDILIR ve
  dosya OLUSMAZ.
- Onay kutusu yok; uc yer bagli (sema + calistir + DURUM_METNI).
"""

import os
import sys
import uuid

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import calistir
from tools.definitions import TANINMIS_TOOLLAR
from tools.file_ops import write_knowledge


class TestUcYer:
    def test_beyaz_listede(self):
        assert "write_file_tool" in TANINMIS_TOOLLAR

    def test_durum_etiketi_var(self):
        from chat.tools import DURUM_METNI
        assert "write_file_tool" in DURUM_METNI


class TestKnowledgeSiniri:
    def test_knowledge_altina_yazar(self, tmp_path):
        base = str(tmp_path)
        r = write_knowledge("knowledge/notlar/deneme.md", "merhaba", base)
        assert "result" in r
        hedef = tmp_path / "knowledge" / "notlar" / "deneme.md"
        assert hedef.read_text(encoding="utf-8") == "merhaba"

    def test_disari_cikis_reddedilir(self, tmp_path):
        base = str(tmp_path)
        for yol in ("../disari.md", "../../x.md", "knowledge/../../kacis.md"):
            r = write_knowledge(yol, "icerik", base)
            assert "error" in r, yol
        assert not (tmp_path / "disari.md").exists()
        assert not (tmp_path / "x.md").exists()
        assert not (tmp_path / "kacis.md").exists()

    def test_mutlak_dis_yol_reddedilir(self, tmp_path):
        dis = tmp_path / "baska" / "a.md"
        r = write_knowledge(str(dis), "icerik", str(tmp_path))
        assert "error" in r
        assert not dis.exists()

    def test_kara_liste_reddedilir(self, tmp_path):
        base = str(tmp_path)
        r = write_knowledge("knowledge/.env", "SECRET=x", base)
        assert "error" in r
        assert not (tmp_path / "knowledge" / ".env").exists()

    def test_bos_girdiler_reddedilir(self, tmp_path):
        assert "error" in write_knowledge("", "x", str(tmp_path))
        assert "error" in write_knowledge("knowledge/a.md", "", str(tmp_path))


class TestCalistirHatti:
    def test_calistir_yazar_ve_temizler(self):
        # Gercek knowledge/'a yazar; isim benzersiz, sonunda silinir.
        ad = "_test_arac_%s.md" % uuid.uuid4().hex[:8]
        kok = os.path.join(os.path.dirname(os.path.dirname(
            os.path.abspath(__file__))), "knowledge")
        hedef = os.path.join(kok, ad)
        try:
            r = calistir("write_file_tool",
                         {"path": "knowledge/" + ad, "content": "arac hatti"})
            assert "result" in r, r
            with open(hedef, encoding="utf-8") as f:
                assert f.read() == "arac hatti"
        finally:
            try:
                os.remove(hedef)
            except OSError:
                pass
        assert not os.path.exists(hedef)

    def test_calistir_disari_yazmaz(self):
        r = calistir("write_file_tool",
                     {"path": "../disari_test.md", "content": "x"})
        assert "error" in r
