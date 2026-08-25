"""write_file_ops beyaz liste gerileme testi.

IZINLI_KOKLER'e yeni bir kok eklendiginde yazma izni
kendiliginden acilmamali -- yazma yalnizca knowledge/ ve
research-engine/ icin serbest olmali.
"""

import os
import sys
import tempfile
import shutil

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'tools'))


def test_yazma_sadece_knowledge_research():
    from file_ops import write_file_ops, YAZMA_IZINLI_KOKLER
    base = os.path.join(tempfile.mkdtemp(), 'proje')
    os.makedirs(os.path.join(base, 'knowledge'))
    os.makedirs(os.path.join(base, 'research-engine'))
    os.makedirs(os.path.join(base, 'diger'))
    try:
        r1 = write_file_ops(os.path.join(base, 'knowledge', 'test.md'), 'icerik', base)
        assert 'result' in r1, f"knowledge/ yazma izni verilmeli: {r1}"
        r2 = write_file_ops(os.path.join(base, 'research-engine', 'test.md'), 'icerik', base)
        assert 'result' in r2, f"research-engine/ yazma izni verilmeli: {r2}"
        r3 = write_file_ops(os.path.join(base, 'diger', 'test.md'), 'icerik', base)
        assert 'error' in r3, f"diger/ yazma engellenmeli: {r3}"
        r4 = write_file_ops(os.path.join(base, 'test.md'), 'icerik', base)
        assert 'error' in r4, f"Proje koku yazma engellenmeli: {r4}"
        assert set(YAZMA_IZINLI_KOKLER) == {'knowledge', 'research-engine'}, \
            f"YAZMA_IZINLI_KOKLER beklenmeyen deger: {YAZMA_IZINLI_KOKLER}"
    finally:
        shutil.rmtree(os.path.dirname(base), ignore_errors=True)


def test_izinkokler_genisletilse_bile_yazma_kapali():
    from file_ops import _yazma_izni_var_mi
    base = os.path.join(tempfile.mkdtemp(), 'proje')
    os.makedirs(os.path.join(base, 'knowledge'))
    os.makedirs(os.path.join(base, 'yeni_kok'))
    try:
        yol_k = os.path.join(base, 'knowledge', 'test.md')
        assert _yazma_izni_var_mi(yol_k, base), "knowledge/ yazma izni olmali"
        yol_y = os.path.join(base, 'yeni_kok', 'test.md')
        assert not _yazma_izni_var_mi(yol_y, base), \
            "yeni_kok/ yazma izni OLMAMALI -- bu TUR2-1 gerilemesidir"
    finally:
        shutil.rmtree(os.path.dirname(base), ignore_errors=True)


if __name__ == '__main__':
    test_yazma_sadece_knowledge_research()
    test_izinkokler_genisletilse_bile_yazma_kapali()
    print("Tum yazma guvenlik testleri basarili!")
