"""tests/test_memory.py — Hafiza motoru testleri (P2).

Embedding fonksiyonu sahte (deterministik) verilir — Ollama gerekmez.
Testler: ekleme, BM25 arama, vektor arama, hibrit birlesik arama,
parcalama, dosya indeksleme, gecmis aktarimi.
"""

import json
import os
import sys
import time

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory.engine import HafizaMotoru, parcalara_bol, indeksle_klasor


def _sahte_embed(metin):
    """Deterministik sahte embedding: kelime hash'lerinden vektor uretir.

    Ayni kelimeyi iceren metinler benzer vektor alir — boylece
    anlam aramasi test edilebilir.
    """
    import hashlib
    import numpy as np

    v = np.zeros(768, dtype=np.float32)
    for kelime in metin.lower().split():
        h = int(hashlib.md5(kelime.encode()).hexdigest(), 16)
        v[h % 768] += 1.0
    norm = np.linalg.norm(v)
    if norm > 0:
        v /= norm
    return v.tolist()


@pytest.fixture
def motor(tmp_path):
    m = HafizaMotoru(db_yolu=str(tmp_path / "test.db"), embed_fn=_sahte_embed)
    yield m
    m.kapat()


class TestParcalaraBol:
    def test_bos_metin(self):
        assert parcalara_bol("") == []
        assert parcalara_bol(None) == []

    def test_kisa_metin_tek_parca(self):
        parcalar = parcalara_bol("Merhaba dunya")
        assert len(parcalar) == 1
        assert parcalar[0] == "Merhaba dunya"

    def test_uzun_metin_bolunur(self):
        metin = "\n\n".join("Paragraf %d " % i + "x" * 100 for i in range(20))
        parcalar = parcalara_bol(metin, boyut=300)
        assert len(parcalar) > 1
        assert all(len(p) <= 400 for p in parcalar)


class TestEkleVeAra:
    def test_bos_ekleme(self, motor):
        assert motor.ekle("   ") is False
        assert motor.ekle(None) is False

    def test_bm25_kelime_arama(self, motor):
        motor.ekle("Furkanın doğum günü 14 Mart'tır", kind="semantic")
        motor.ekle("Başak projesi Python ile yazıldı", kind="semantic")
        sonuclar = motor.ara("doğum günü", limit=2)
        assert len(sonuclar) >= 1
        assert "doğum" in sonuclar[0]["text"]

    def test_vektor_anlam_aramasi(self, motor):
        motor.ekle("kedi evde uyuyor", kind="semantic")
        motor.ekle("Furkan futbol oynar", kind="semantic")
        # Sahte embedding kelime bazli: ayni kelime benzerlik verir
        sonuclar = motor.ara("futbol", limit=1)
        assert sonuclar and "futbol" in sonuclar[0]["text"]

    def test_hibrit_siralama(self, motor):
        motor.ekle("Ankara başkenttir", kind="semantic", kaynak="a")
        motor.ekle("İzmir Ege'dedir", kind="semantic", kaynak="b")
        for _ in range(3):
            motor.ara("ankara")
        sonuclar = motor.ara("Ankara nerededir", limit=5)
        assert any("Ankara" in s["text"] for s in sonuclar)
        assert all(s["score"] > 0 for s in sonuclar)

    def test_episodik_kayit_formati(self, motor):
        motor.episodik_kaydet("Bugün hava nasıl?", "Güneşli.")
        sonuclar = motor.ara("hava", limit=1)
        assert sonuclar
        assert "Furkan (" in sonuclar[0]["text"]
        assert "Başak:" in sonuclar[0]["text"]

    def test_say(self, motor):
        assert motor.say() == 0
        motor.ekle("bir")
        motor.ekle("iki")
        assert motor.say() == 2


class TestKaynakYonetimi:
    def test_kaynak_sil(self, motor):
        motor.ekle("parca bir", kind="semantic", kaynak="dosya.md")
        motor.ekle("parca iki", kind="semantic", kaynak="dosya.md")
        motor.ekle("baska dosya", kind="semantic", kaynak="baska.md")
        silinen = motor.kaynak_sil("dosya.md")
        assert silinen == 2
        assert motor.say() == 1
        # FTS kalintisi da temizlenmeli (vektor kNN yakin komsu dondurebilir,
        # bu yuzden BM25 katmanina dogrudan bakiyoruz)
        assert motor._bm25_ara("parca", 5) == []

    def test_meta_al_koy(self, motor):
        assert motor.meta_al("yok") is None
        motor.meta_koy("anahtar", {"deger": 5})
        assert motor.meta_al("anahtar") == {"deger": 5}


class TestDosyaIndeksleme:
    def test_indeksle_klasor(self, motor, tmp_path):
        klasor = tmp_path / "notlar"
        klasor.mkdir()
        (klasor / "ali.md").write_text(
            "Ali'nin favori rengi mavidir.\n\nAli Ankara'da yasar.", encoding="utf-8")
        (klasor / "README.md").write_text("okunmamali gizli", encoding="utf-8")

        # Iki kisa paragraf tek parcada birlesir (parca boyutu 700)
        sayi = indeksle_klasor(motor, str(klasor), "test")
        assert sayi == 1
        sonuclar = motor.ara("favori renk", limit=1)
        assert sonuclar
        assert sonuclar[0]["source"] == "test:ali.md"

        # README indekslenmemis olmali
        assert motor._bm25_ara("okunmamali", 5) == []

        # Tekrar cagirma: degisiklik yok → yeni ekleme yapilmaz
        sayi2 = indeksle_klasor(motor, str(klasor), "test")
        assert sayi2 == 0
        assert motor.say() == 1

    def test_degisen_dosya_yeniden_indekslenir(self, motor, tmp_path):
        klasor = tmp_path / "notlar"
        klasor.mkdir()
        dosya = klasor / "not.md"
        dosya.write_text("eski icerik", encoding="utf-8")
        indeksle_klasor(motor, str(klasor), "t")

        time.sleep(0.05)
        dosya.write_text("yeni icerik tamamlandi", encoding="utf-8")
        os.utime(str(dosya), (time.time() + 1, time.time() + 1))
        indeksle_klasor(motor, str(klasor), "t")

        eski = [s for s in motor.ara("eski icerik", limit=5)
                if "eski" in s["text"]]
        yeni = [s for s in motor.ara("yeni icerik", limit=5)
                if "yeni" in s["text"]]
        assert yeni and not eski

    def test_gizli_klasor_atlanir(self, motor, tmp_path):
        klasor = tmp_path / "defter"
        gizli = klasor / ".obsidian"
        gizli.mkdir(parents=True)
        (gizli / "ayar.md").write_text("config", encoding="utf-8")
        sayi = indeksle_klasor(motor, str(klasor), "obs")
        assert sayi == 0


class TestBozulmaDirenci:
    def test_embed_hatasi_bm25_devam(self, tmp_path):
        """Embedding fonksiyonu patlarsa bile kayit + BM25 calisir."""
        def bozuk_embed(_):
            raise RuntimeError("Ollama yok")

        m = HafizaMotoru(db_yolu=str(tmp_path / "bozuk.db"), embed_fn=bozuk_embed)
        try:
            assert m.ekle("hatirlanacak sey") is True
            sonuclar = m.ara("hatirlanacak", limit=1)
            assert sonuclar and "hatirlanacak" in sonuclar[0]["text"]
            assert sonuclar[0].get("score", 0) > 0
        finally:
            m.kapat()

    def test_sqlite_vec_yuklu_degilse_dagilir(self):
        """vec0 tablosuz da motor kurulabilir (vektor_var False zorlanamaz ama
        _vec_yukle hatada None dondurur)."""
        from memory.engine import _vec_yukle

        class SahteConn:
            def enable_load_extension(self, _):
                raise AttributeError("desteklenmiyor")

        assert _vec_yukle(SahteConn()) is False
