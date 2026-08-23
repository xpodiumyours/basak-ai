"""tests/test_hafiza_yasam_dongusu.py — Hafıza temizleme + budama testleri.

2026-08-24'te Casper'in buldugu bosluk: UI "hafiza temizlendi" diyordu ama
Api.clear() yalnizca gecmis.json siliyordu; episodic anilar basak.db'de
kaliyordu ve sonraki konusmalarda bulunabiliyordu.

Kurallar:
- clear() = gecmis.json + episodic anilar (sohbetten ogrenilenler)
- knowledge/defter/obsidian indekslerine DOKUNULMAZ (dosyalardan turetilir)
- episodic satir tavani EPISODIK_LIMIT — en eskiler budanir (sisme engeli)
- birebir ayni cift tekrar yazilmaz
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from memory.engine import HafizaMotoru


@pytest.fixture
def motor(tmp_path):
    return HafizaMotoru(
        db_yolu=str(tmp_path / "test.db"),
        embed_fn=lambda m: None,   # BM25-only, ag yok
    )


class TestDedup:
    def test_ayni_cift_ikinci_yazilmaz(self, motor):
        assert motor.episodik_kaydet("cay markam ne", "Caykur") is True
        assert motor.episodik_kaydet("cay markam ne", "Caykur") is False
        assert motor.say() == 1

    def test_farkli_ciftler_yazilir(self, motor):
        motor.episodik_kaydet("soru 1", "cevap 1")
        motor.episodik_kaydet("soru 2", "cevap 2")
        assert motor.say() == 2


class TestBudama:
    def test_tavan_asilinca_eski_duser(self, motor):
        for i in range(8):
            motor.episodik_kaydet("soru %d" % i, "cevap %d" % i)
        silinen = motor._budu(limit=5)
        assert silinen == 3
        assert motor.say() == 5
        # dogrudan DB icerigi: en yeniler kalmali, en eskiler gitmeli
        kalanlar = [r[0] for r in motor.conn.execute(
            "SELECT text FROM memories ORDER BY id")]
        assert any("soru 7" in t for t in kalanlar)
        assert any("soru 3" in t for t in kalanlar)
        assert not any("soru 0" in t for t in kalanlar)
        assert not any("soru 2" in t for t in kalanlar)

    def test_limit_altinda_buda_yok(self, motor):
        motor.episodik_kaydet("tek", "cift")
        assert motor._budu(limit=5) == 0


class TestTemizleme:
    def test_episodik_temizle_semantige_dokunmaz(self, motor):
        motor.episodik_kaydet("kişisel soru", "kişisel cevap")
        motor.ekle("defter INDEX satiri", kind="semantic",
                   kaynak="defter:INDEX.md")
        assert motor.episodik_temizle() == 1
        assert motor.say() == 1
        # semantic kayit hala bulunabilir
        bulunan = motor.ara("defter INDEX", limit=1)
        assert bulunan and "INDEX" in bulunan[0]["text"]

    def test_temiz_sonrasi_episodik_bulunamaz(self, motor):
        motor.episodik_kaydet("gizli plan", "plan detaylari")
        motor.episodik_temizle()
        assert motor.ara("gizli plan", limit=5) == []

    def test_cift_temizleme_guvenli(self, motor):
        assert motor.episodik_temizle() == 0
        assert motor.episodik_temizle() == 0


class TestApiClear:
    def test_clear_gecmis_ve_anilari_birlikte_unutur(
            self, monkeypatch, tmp_path):
        import basak_app
        import chat as c

        motor = HafizaMotoru(
            db_yolu=str(tmp_path / "api.db"),
            embed_fn=lambda m: None,
        )
        monkeypatch.setattr(c, "_hafiza", motor)
        gecmis = tmp_path / "gecmis.json"
        gecmis.write_text('[{"role": "user", "content": "x"}]',
                          encoding="utf-8")
        monkeypatch.setattr(basak_app, "HISTORY_FILE", str(gecmis))

        motor.episodik_kaydet("eski soru", "eski cevap")

        api = basak_app.Api()
        r = api.clear()

        assert r["ok"] is True
        assert r["unutulan_ani"] == 1
        assert not gecmis.exists()
        assert motor.say() == 0

    def test_clear_motorsuz_da_calisir(self, monkeypatch, tmp_path):
        import basak_app
        import chat as c

        monkeypatch.setattr(c, "_hafiza", False)   # motor kapali senaryosu
        gecmis = tmp_path / "gecmis.json"
        gecmis.write_text("[]", encoding="utf-8")
        monkeypatch.setattr(basak_app, "HISTORY_FILE", str(gecmis))

        api = basak_app.Api()
        r = api.clear()
        assert r["ok"] is True and r["unutulan_ani"] == 0
