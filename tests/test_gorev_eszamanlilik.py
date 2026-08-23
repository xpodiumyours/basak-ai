"""tests/test_gorev_eszamanlilik.py — Gorev dosyasinda eszamanli yazma.

2026-08-24'te Casper'in buldugu yarisa karsi koruma testleri:
Api.mesaj() her mesaji ayri thread'de kosturur; add_task/complete_task
oku-degitir-yaz yaptigindan ayni ID uretimi veya yazma ezilmesi
mumkundu. Artik _KILIT + max(id)+1 + atomik yazma var.
"""

import json
import os
import sys
import threading
from concurrent.futures import ThreadPoolExecutor

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.tasks import add_task, complete_task, list_tasks


def oku(yol):
    with open(yol, encoding="utf-8-sig") as f:
        return json.load(f)


class TestEsZamanliEkleme:
    def test_10_thread_paralel_ekleme_kayip_yok(self, tmp_path):
        yol = str(tmp_path / "gorevler.json")
        bariyer = threading.Barrier(10)

        def ekle(i):
            bariyer.wait()
            return add_task("gorev %d" % i, yol)

        with ThreadPoolExecutor(max_workers=10) as havuz:
            sonuclar = list(havuz.map(ekle, range(10)))

        assert all("result" in r for r in sonuclar)
        gorevler = oku(yol)
        assert len(gorevler) == 10                      # hicbir kayit kaybolmadi
        idler = sorted(g["id"] for g in gorevler)
        assert idler == list(range(1, 11))              # ID'ler benzersiz ve sirali

    def test_ekleme_ve_tamamlama_yarisi_temiz_biter(self, tmp_path):
        yol = str(tmp_path / "g.json")
        add_task("ilk is", yol)                          # id=1
        hatalar = []

        def karisik(i):
            try:
                if i % 2 == 0:
                    add_task("is %d" % i, yol)
                else:
                    # var olan ilk gorevi tekrar tekrar tamamla (id=1)
                    complete_task(1, yol)
            except Exception as e:                       # bozuk JSON vb. olmamali
                hatalar.append(str(e))

        with ThreadPoolExecutor(max_workers=8) as havuz:
            list(havuz.map(karisik, range(16)))

        assert hatalar == []
        gorevler = oku(yol)                              # dosya gecerli JSON
        idler = [g["id"] for g in gorevler]
        assert len(idler) == len(set(idler))             # mukerrer ID yok

    def test_tmp_artigi_birakilmaz(self, tmp_path):
        yol = str(tmp_path / "g.json")
        add_task("a", yol)
        add_task("b", yol)
        assert not os.path.exists(yol + ".tmp")
