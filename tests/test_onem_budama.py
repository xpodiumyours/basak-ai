"""tests/test_onem_budama.py — Anı önem puanı + puana göre budama.

2026-08-24, Kademe 1+2 (Casper onaylı). Kabul ölçütü:
"Önemli diye işaretlenmiş bilgi, ardından gelen onlarca önemsiz
sohbetten sonra HÂLÂ hafızadadır; önemsizler budanır."

Puanı KOD verir, model tahmin etmez:
- 3: kullanıcı "hatırla/not al/önemli/unutma/deftere yaz" dedi
     VEYA o turda bir yazma aracı gerçekten koştu
- 1: sıradan sohbet
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from chat import _onem_puanla
from memory.engine import EPISODIK_LIMIT, HafizaMotoru


@pytest.fixture
def motor(tmp_path):
    return HafizaMotoru(db_yolu=str(tmp_path / "t.db"),
                        embed_fn=lambda m: None)


class TestPuaniVeren:
    def test_acik_hatirlatma_3(self):
        assert _onem_puanla("Bunu hatırla: sunucu adresi x") == 3

    def test_onemli_kelimesi_3(self):
        assert _onem_puanla("Önemli: yarın toplantı var") == 3

    def test_yazma_araci_kostuysa_3(self):
        assert _onem_puanla(
            "tamamdır", [("deftere_kaydet", "Kayit eklendi")]) == 3

    def test_siradan_sohbet_1(self):
        assert _onem_puanla("bugün hava nasıl?") == 1

    def test_bos_girdi_1(self):
        assert _onem_puanla("") == 1


class TestOnemliHayattaKalir:
    def test_kabul_olcutu_onemli_gevezelikten_uzun_yasar(self, motor):
        """50 önemsiz sohbet önemli kaydı kovamaz."""
        motor.episodik_kaydet(
            "proje planını hatırla",
            "VixRex planı: önce vitrin, sonra ödeme modülü", onem=3)
        for i in range(EPISODIK_LIMIT):
            motor.episodik_kaydet("gevezelik %d" % i,
                                  "sıradan cevap %d" % i)
        motor._budu()
        kalan = [r[0] for r in motor.conn.execute(
            "SELECT text FROM memories")]
        assert any("VixRex planı" in t for t in kalan), \
            "ÖNEMLİ PLAN BUDANDI!"

    def test_dusuk_onemliler_once_gider(self, motor):
        # eski ama önemli vs yeni ama önemsiz
        motor.episodik_kaydet("eski önemli not", "A", onem=3)
        motor.episodik_kaydet("yeni gevezelik", "B", onem=1)
        motor._budu(limit=1)
        kalan = [r[0] for r in motor.conn.execute(
            "SELECT text FROM memories")]
        assert len(kalan) == 1 and "önemli" in kalan[0]

    def test_eski_dusuk_onem_yeniden_dusuk_onemden_once_gider(self, motor):
        motor.episodik_kaydet("eski sohbet", "E")
        motor.episodik_kaydet("yeni sohbet", "Y")
        motor._budu(limit=1)
        kalan = [r[0] for r in motor.conn.execute(
            "SELECT text FROM memories")]
        assert len(kalan) == 1 and "yeni" in kalan[0]


class TestUyumluKayit:
    def test_varsayilan_onem_1(self, motor):
        motor.episodik_kaydet("s", "c")
        row = motor.conn.execute(
            "SELECT onem FROM memories").fetchone()
        assert row[0] == 1

    def test_onem_3_yazilir(self, motor):
        motor.episodik_kaydet("s", "c", onem=3)
        assert motor.conn.execute(
            "SELECT onem FROM memories").fetchone()[0] == 3

    def test_sinir_disi_puan_kisilir(self, motor):
        motor.ekle("x", kind="episodic", onem=99)
        assert motor.conn.execute(
            "SELECT onem FROM memories").fetchone()[0] == 3

    def test_mevcut_db_migrasyonsuz_calisir(self, tmp_path):
        """Eski DB (onem kolonu yok) açılınca kolon otomatik eklenir."""
        import sqlite3
        yol = str(tmp_path / "eski.db")
        conn = sqlite3.connect(yol)
        conn.execute(
            "CREATE TABLE memories (id INTEGER PRIMARY KEY AUTOINCREMENT,"
            " kind TEXT NOT NULL, text TEXT NOT NULL,"
            " source TEXT NOT NULL DEFAULT '', created_at REAL NOT NULL,"
            " has_vec INTEGER NOT NULL DEFAULT 0)")
        conn.commit()
        conn.close()
        m = HafizaMotoru(db_yolu=yol, embed_fn=lambda x: None)
        m.episodik_kaydet("migrasyon sonrası", "çalışıyor")
        assert m.say() == 1
