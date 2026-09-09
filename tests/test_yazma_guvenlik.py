"""write_file_ops beyaz liste gerileme testi.

2026-09-09 GUNCELLEME (Casper karari): yazma kurali genisletildi.
- knowledge/ ve research-engine/: ONAYSIZ serbest.
- ev + C:\\Projects: SERBEST ama ONLALI (chat/tools.py onay sorar).
- Kara liste (sistem/sifre) ve dis projeler: ASLA.

Bu dosya yeni kurali kilitler: knowledge serbestligi korunur,
kara liste ve dis-proje yasagi delinemez.
"""

import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))


def test_yazma_knowledge_serbest_digerleri_kuralli():
    from file_ops import (write_file_ops, YAZMA_IZINLI_KOKLER,
                          _yazma_izni_var_mi, _otomatik_yazma_mi)
    base = os.path.join(tempfile.mkdtemp(), 'proje')
    os.makedirs(os.path.join(base, 'knowledge'))
    os.makedirs(os.path.join(base, 'research-engine'))
    try:
        r1 = write_file_ops(os.path.join(base, 'knowledge', 'test.md'), 'icerik', base)
        assert 'result' in r1, f"knowledge/ yazma izni verilmeli: {r1}"
        r2 = write_file_ops(os.path.join(base, 'research-engine', 'test.md'), 'icerik', base)
        assert 'result' in r2, f"research-engine/ yazma izni verilmeli: {r2}"
        # Tmp dizini ev altinda oldugu icin izin VARDIR (yeni kural);
        # ama otomatik DEGILDIR (onay gerekir).
        yol = os.path.join(base, 'knowledge', 'test.md')
        assert _yazma_izni_var_mi(yol, base) is True
        assert _otomatik_yazma_mi(yol, base) is True
        assert set(YAZMA_IZINLI_KOKLER) == {'knowledge', 'research-engine'}, \
            f"YAZMA_IZINLI_KOKLER beklenmeyen deger: {YAZMA_IZINLI_KOKLER}"
    finally:
        shutil.rmtree(os.path.dirname(base), ignore_errors=True)


def test_kara_listeye_yazma_yasak():
    from file_ops import _yazma_izni_var_mi
    base = tempfile.mkdtemp()
    try:
        assert _yazma_izni_var_mi(
            r"C:\Windows\Temp\kotuluk.txt", base) is False
        assert _yazma_izni_var_mi(
            os.path.join(base, "sifre.env"), base) is False
    finally:
        shutil.rmtree(base, ignore_errors=True)


def test_dis_projeye_yazma_yasagi_korundu(monkeypatch):
    import file_ops
    from file_ops import _yazma_izni_var_mi
    base = tempfile.mkdtemp()
    dis = os.path.join(base, "vixrex")
    os.makedirs(dis)
    monkeypatch.setattr(file_ops, "DIS_PROJELER", {"vixrex": dis})
    try:
        assert _yazma_izni_var_mi(
            os.path.join(dis, "yeni.md"), base) is False
    finally:
        shutil.rmtree(base, ignore_errors=True)


if __name__ == '__main__':
    test_yazma_knowledge_serbest_digerleri_kuralli()
    test_kara_listeye_yazma_yasak()
    print("Tum yazma guvenlik testleri basarili!")
