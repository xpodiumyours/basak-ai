"""tests/test_knowledge_kapsama.py - Knowledge onbellek kapsama testleri.

2026-09-12: AGENTS.md girdisi olu oldugu icin kalkti. Bu test kilitler:
- cikti, AGENTS.md icerigini TASIMAZ,
- beklenen knowledge parcalarini TASIR,
- butce asiminda kirpma + kuyruk Notu uretilir.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chat  # noqa: F401  (once tam paket: dairesel import onlemi)
import _chat_legacy as L  # noqa: E402


def _dosya_yaz(dizin, ad, icerik):
    with open(os.path.join(dizin, ad), "w", encoding="utf-8") as f:
        f.write(icerik)


class TestKnowledgeKapsama:
    def test_agents_icerigi_girmez(self, monkeypatch, tmp_path):
        _dosya_yaz(str(tmp_path), "INDEX.md", "I" * 100)
        _dosya_yaz(str(tmp_path), "not.md", "N" * 100)
        _dosya_yaz(str(tmp_path), "README.md", "R" * 50)
        monkeypatch.setattr(L, "KNOWLEDGE_DIR", str(tmp_path))
        monkeypatch.setattr(L, "_knowledge_cache", None)
        L._load_knowledge()
        cache = L._knowledge_cache or ""
        assert "### INDEX.md" in cache
        assert "### not.md" in cache
        assert "AGENTS" not in cache

    def test_butce_asiminda_kirpilir(self, monkeypatch, tmp_path):
        _dosya_yaz(str(tmp_path), "INDEX.md", "I" * 100)
        _dosya_yaz(str(tmp_path), "buyuk.md", "B" * 5000)
        _dosya_yaz(str(tmp_path), "README.md", "R" * 50)
        monkeypatch.setattr(L, "KNOWLEDGE_DIR", str(tmp_path))
        monkeypatch.setattr(L, "_knowledge_cache", None)
        L._load_knowledge()
        cache = L._knowledge_cache or ""
        assert "### buyuk.md" in cache
        # 2000 harf butce + kuyruk Notu; tum dosya giremez
        assert len(cache) < 5000
        assert "BM25" in cache
