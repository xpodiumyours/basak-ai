"""tests/test_hafiza_olcum.py — Hafiza dogruluk olcumunun testleri.

Cevrimdisi: gercek embedding YOK, gercek hafiza DB'si ELLENMEZ.
Amac iki katmanli:
  1) Olcum duzenegi dogru mu (harness kendisi),
  2) Setler isini yapiyor mu — KELIME BM25'le bulunabilir, ANLAM yalniz
     anlam yoluyla bulunabilir olmali (yoksa set yaniltir).
"""

import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import hafiza_olcum as ho


def _sahte_embed(metin, gorev="RETRIEVAL_DOCUMENT"):
    """Deterministik sahte vektor: ayni kelime -> ayni boyut."""
    import numpy as np

    v = np.zeros(768, dtype=np.float32)
    for kelime in (metin or "").lower().split():
        h = int(hashlib.md5(kelime.encode()).hexdigest(), 16)
        v[h % 768] += 1.0
    norm = float(np.linalg.norm(v))
    if norm > 0:
        v /= norm
    return v.tolist()


def _kelimeler(metin):
    return {k for k in metin.lower().split() if len(k) > 2}


class TestSetler:
    def test_kelime_seti_bos_degil_ve_beklenen_kayitta_var(self):
        assert ho.KELIME_SETI
        for metin, sorgu, beklenen in ho.KELIME_SETI:
            assert sorgu.strip() and beklenen.strip()
            assert beklenen.lower() in metin.lower(), \
                "%r kaydinda %r yok" % (metin, beklenen)

    def test_kelime_sorusu_kayitla_ortak_kelime_tasir(self):
        """KELIME setinin isi bu: BM25 eslesmesi kurulabilir olmali."""
        for metin, sorgu, _ in ho.KELIME_SETI:
            assert _kelimeler(metin) & _kelimeler(sorgu), \
                "%r ile %r ortak kelime tasimiyor" % (metin, sorgu)

    def test_anlam_sorusu_kayitla_ortak_kelime_tasimaz(self):
        """ANLAM seti yalniz vektoru olcer; kelime ortakligi olursa yaniltir."""
        assert ho.ANLAM_SETI
        for metin, sorgu, beklenen in ho.ANLAM_SETI:
            assert beklenen.lower() in metin.lower()
            assert not (_kelimeler(metin) & _kelimeler(sorgu)), \
                "%r ile %r ortak kelime tasiyor (ANLAM seti bozuldu)" % (
                    metin, sorgu)


class TestKos:
    def test_cevrimdisi_kelime_tabani_tam(self, tmp_path):
        rapor = ho.kos(str(tmp_path / "a.db"))
        assert rapor["kelime_orani"] == 1.0
        assert rapor["vektor_olculdu"] is False
        assert rapor["anlam"] == []
        assert rapor["anlam_orani"] is None

    def test_vektor_varsa_anlam_seti_de_olculur(self, tmp_path):
        rapor = ho.kos(str(tmp_path / "b.db"), embed_fn=_sahte_embed)
        assert rapor["vektor_olculdu"] is True
        assert len(rapor["anlam"]) == len(ho.ANLAM_SETI)
        assert 0.0 <= rapor["anlam_orani"] <= 1.0

    def test_olcum_tekrarlanabilir(self, tmp_path):
        a = ho.kos(str(tmp_path / "a.db"))
        b = ho.kos(str(tmp_path / "b.db"))
        assert a["kelime_orani"] == b["kelime_orani"]
        assert a["kelime"] == b["kelime"]

    def test_k_butun_satirlari_dondurur(self, tmp_path):
        rapor = ho.kos(str(tmp_path / "c.db"), k=1)
        assert len(rapor["kelime"]) == len(ho.KELIME_SETI)
        assert 0.0 <= rapor["kelime_orani"] <= 1.0


class TestArgumanVeCikis:
    def test_k_ayristirma(self):
        assert ho._k_al(["--k", "7"], 4) == 7
        assert ho._k_al([], 4) == 4
        assert ho._k_al(["--k"], 4) == 4
        assert ho._k_al(["--k", "0"], 4) == 1

    def test_main_taban_tutunca_sifir_doner(self):
        assert ho.main([]) == 0

    def test_main_canli_bayraksiz_kota_harcamaz(self):
        """--canli yoksa embed_fn None kalir; cagri yapilmaz."""
        assert ho._canli_embed_fn is not None  # fonksiyon yerinde
        assert ho.main(["--k", "2"]) == 0
