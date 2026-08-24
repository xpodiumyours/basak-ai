"""tests/live/test_memory_lifecycle.py — Hafıza yaşam döngüsü (GERÇEK DB).

CANLI-KAPISI.md kabulü: kayıt restart sonrası doğru döner; temizlenen
episodic geri GELMEZ; semantic/derived kayıtlar temizlikten etkilenmez;
1000 kayıt tavanında önemli anılar korunur.
"""

import os
import sys

from memory.engine import EPISODIK_LIMIT, HafizaMotoru

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))


def _motor(tmp_path):
    # embed_fn=None zorlaması: BM25-only hızlı ve çevrimdışı güvenli
    return HafizaMotoru(db_yolu=str(tmp_path / "canli-hafiza.db"),
                        embed_fn=lambda t: None)


def test_kapat_ac_hatirla(tmp_path, rapor):
    m = _motor(tmp_path)
    m.episodik_kaydet("Cay tercihim adacayi, bunu hatirla",
                      "Tamam, not aldım.", onem=3)
    m.kapat()

    m2 = _motor(tmp_path)
    bulgular = m2.ara("cay tercihim", limit=5)
    metinler = " ".join(b.get("text", "") for b in bulgular)
    rapor("kapat_ac", {"bulgu": len(bulgular)})
    assert "adacayi" in metinler.lower(), "hatırlanan bilgi kayboldu"
    m2.kapat()


def test_temizlik_semantige_dokunmaz(tmp_path):
    m = _motor(tmp_path)
    m.episodik_kaydet("sifre: gecici-123", "tamam")
    m.ekle("Furkan'in plani: vixrex v2", kind="semantic",
           kaynak="test-plan")
    silinen = m.episodik_temizle()
    assert silinen >= 1
    assert m.ara("sifre gecici") == [], "temizlenen kayıt GERİ GELDİ"
    kalan = m.ara("vixrex v2", limit=5)
    assert any("plani" in b.get("text", "").lower() for b in kalan), \
        "semantic kayıt temizlikte zarar gördü"
    m.kapat()


def test_bin_kayit_tavani_onemliyi_korur(tmp_path, rapor):
    m = _motor(tmp_path)
    for i in range(EPISODIK_LIMIT + 20):        # tavan + taşma
        m.episodik_kaydet("gevezelik soru %d" % i,
                          "gevezilik cevap %d" % i, onem=1)
    for i in range(5):                           # kritik anılar EN SONDA
        m.episodik_kaydet("kritik plan %d: yedek al" % i,
                          "not edildi", onem=3)

    episodic_sayisi = m.conn.execute(
        "SELECT COUNT(*) FROM memories WHERE kind='episodic'"
    ).fetchone()[0]
    kritik = [r[0] for r in m.conn.execute(
        "SELECT text FROM memories WHERE kind='episodic' AND onem=3")]

    rapor("budama", {"tavan": EPISODIK_LIMIT,
                     "episodic_kalan": episodic_sayisi,
                     "kritik_kalan": len(kritik)})
    assert episodic_sayisi <= EPISODIK_LIMIT, "tavan aşıldı"
    assert len(kritik) == 5, "önemli anılar budamada gitti"
    m.kapat()


def test_tekrar_kayit_dedupe(tmp_path):
    m = _motor(tmp_path)
    ilk = m.episodik_kaydet("ayni soru", "ayni cevap")
    ikinci = m.episodik_kaydet("ayni soru", "ayni cevap")
    assert ilk is True and ikinci is False
    m.kapat()
