"""tests/test_saglik.py — Hat saglik raporu guvencesi.

Sozlesme: uc yerde bagli; ag yok; gercek istatistik/gunluge
DOKUNULMAZ (yollar enjekte edilir).
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import calistir, saglik
from tools.definitions import TANINMIS_TOOLLAR


class SahteIstat:
    def ozet(self, son_saat=None):
        return [{"model": "glm", "toplam": 10, "basari_orani": 80.0,
                 "ortalama_ms": 5200}]

    def token_bugun(self, model):
        return (50000, 1000)


class TestUcYer:
    def test_beyaz_listede(self):
        assert "saglik_raporu" in TANINMIS_TOOLLAR

    def test_durum_etiketi_var(self):
        from chat.tools import DURUM_METNI
        assert "saglik_raporu" in DURUM_METNI


class TestRapor:
    def test_tablo_uretilir(self, tmp_path, monkeypatch):
        import brain.stats as stats_mod
        monkeypatch.setattr(stats_mod, "model_stats_al",
                            lambda: SahteIstat())
        audit = tmp_path / "audit.log"
        audit.write_text("2026-09-13 | HATA kaynak=groq (0.2 sn): 429 limit\n"
                         "2026-09-13 | OK kaynak=glm | 5.0 sn\n",
                         encoding="utf-8")
        r = saglik.saglik_raporu(audit_yolu=str(audit))
        assert "result" in r, r
        assert "glm" in r["result"] and "10 cagri" in r["result"]
        assert "kota-doldu=1" in r["result"]
        assert "groq bugun" in r["result"]

    def test_gunluk_yoksa_da_kosar(self, tmp_path, monkeypatch):
        import brain.stats as stats_mod
        monkeypatch.setattr(stats_mod, "model_stats_al",
                            lambda: SahteIstat())
        r = saglik.saglik_raporu(audit_yolu=str(tmp_path / "yok.log"))
        assert "result" in r

    def test_calistir_hatti(self):
        r = calistir("saglik_raporu", {})
        assert isinstance(r, dict)
        assert "result" in r or "error" in r
