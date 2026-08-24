"""tests/test_e2e_beyin.py — Beyin organları ZİNCİR entegrasyonu (E2E).

Kilitli hedefin organlarının tek bir senaryoda birlikte çalıştığını
kanıtlar — her biri ayrı ayrı değil, ZİNCİRDE:

    FAY tanıkları iddia üretir (ölçüm)
        -> çarpıştırıcı çatlağı yakalar
            -> çatlak gerilim kuyruğuna düşer
                -> DENEY motoru hipotezi sınar
                    -> sonuç EVRİM arşivine puan olarak girer
                        -> DÜNYA modeli güveni yansıtır
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from datetime import datetime

from tools.deney import deney_yurut
from tools.dunya import dunya_sorgu
from tools.evrim import Arsiv, evrim_turu
from tools.fay import carpistir, tanik_iddialari
from tools.gerilim import FayKuyrugu


def sahte_calistir(yanitlar):
    def calistir(ad, args, *a, **kw):
        return yanitlar[ad]
    return calistir


class TestZincir:
    def test_tanikdan_celiskiye_kuyruktan_deneye_arşive_dunyaya(
            self, tmp_path):

        # 1) Üç tanık ölçer — belge "bitti" der, git "commit yok" diyor
        calistir = sahte_calistir({
            "git_durum": {"result": "Dal: main | 12 dosya "
                                    "commit edilmemis"},
            "belge_ara": {"result": "GOREV_LISTESI.md:84: plan "
                                    "tamamlandi"},
            "dosya_bilgi": {"result": "app.py | 12 KB | bugun"},
        })
        iddialar = tanik_iddialari("vixrex", "vitrin", "app.py",
                                   calistir)
        assert len(iddialar) == 3

        # 2) Çarpıştırıcı (yerel model) çelişen ikiliyi işaretler
        beyin = lambda m: {"content":
                           "[CELISIYOR] belge vs git: bitti diyor ama "
                           "commit edilmemis dosya var"}
        catisma = carpistir(iddialar, beyin)
        assert catisma and set(catisma["cift"]) == {"belge", "git"}

        # 3) Çatlak gerilim kuyruğuna girer
        kuyruk = FayKuyrugu(str(tmp_path / "kuyruk.json"))
        simdi = datetime.now()
        cid = kuyruk.catlak_ekle(
            "vixrex-vitrin", catisma["cift"], catisma["gerekce"],
            maliyet_seviyesi="commit", yayilma=0.6, simdi=simdi)

        # 4) DENEY motoru hipotezi sınamaya çevirir:
        #    hipotez "plan bitmişse commit edilmemiş dosya OLMAMALI"
        #    ölçüm aksini gösterir -> hipotez ELENİR (gerçekçi senaryo)
        deneyler = [{
            "iddia": "plan tamamlanmis olsa commit edilmemis dosya "
                     "olmamali",
            "arac": "git_durum", "arguman": {"proje": "vixrex"},
            "kural": "yok", "beklenen": "commit edilmemis",
        }]
        deney_raporu = deney_yurut(deneyler, calistir)
        assert deney_raporu[0]["durum"] == "elenmis"   # gerçekte VAR

        # 5) Ölçüm sonucu EVRİM arşivine girer: hipotez elendiği için
        #    puan 0 — ama ölçümün kendisi başarılıdır ve kayda geçer.
        arsiv = Arsiv(str(tmp_path / "arsiv.json"))
        hid = arsiv.hipotez_ekle(
            "vitrin plani tamamlandi iddiasinin dogrulanmasi")
        destek = 1.0 if deney_raporu[0]["durum"] == "desteklendi" else 0.0
        arsiv.puanla(hid, destek, "deney olcumu")

        # 6) Kaynak güveni karneyle beslenir -> dünya modeline yansır
        from tools import bayat
        bayat.karnayi_guncelle("git", "vixrex-vitrin", dogru=True)
        bugun = datetime.now().strftime("%Y-%m-%d")
        karar_yolu = tmp_path / "karar.md"
        with open(karar_yolu, "w", encoding="utf-8") as f:
            f.write("---\nkim: casper\ntarih: %s\nkonu: vixrex vitrin "
                    "celiskisi\ntip: karar\nomur: sonsuz\nkaynak: git\n"
                    "---\n\ncommit edilmemis dosyalar once islenecek\n"
                    % bugun)
        # dünya modeli defter dizinine bakar — kararı oraya taşıyoruz
        import shutil
        defter = tmp_path / "defter"
        defter.mkdir()
        shutil.move(str(karar_yolu), str(defter / "vixrex-karar.md"))
        inanclar = dunya_sorgu(defter, anahtar="vixrex")

        assert len(inanclar) == 1
        assert inanclar[0]["guven"] > 0.5   # karne desteği göründü

        # 7) Kuyrukta çatlak hâlâ AÇIK — çözüm kararı Casper'ın
        veri = __import__("json").load(open(tmp_path / "kuyruk.json",
                                            encoding="utf-8-sig"))
        assert veri["catlaklar"][0]["durum"] == "acik"

    def test_evrim_turu_deney_motoruyla_calisir(self, tmp_path):
        """EVRIM döngüsünün değerlendiricisi gerçek deney motorudur."""
        arsiv = Arsiv(str(tmp_path / "a.json"))
        calistir = sahte_calistir({
            "git_durum": {"result": "Dal: main Son commit: 20da1a7"},
        })

        adaylar = ['"main dalindadir" iddiasinin dogrulanmasi',
                   '"develop dalindadir" iddiasinin dogrulanmasi']

        def uretici():
            return adaylar

        def degerlendirici(hid, icerik):
            # Hipotezden BEKLENENI türet — böylece iki aday gerçekten
            # farklı önermeler olur ve ölçüm ayırt edebilir.
            beklenen = "develop" if "develop" in icerik else "main"
            rapor = deney_yurut(
                [{"iddia": icerik, "arac": "git_durum",
                  "arguman": {"proje": "vixrex"}, "kural": "icerir",
                  "beklenen": beklenen}],
                calistir)
            return (1.0 if rapor[0]["durum"] == "desteklendi" else 0.0,
                    rapor[0].get("kanit", ""))

        kalanlar = evrim_turu(arsiv, uretici, degerlendirici,
                              hayatta_limit=1)
        assert kalanlar and kalanlar[0]["id"].startswith("H00")
        # main hipotezi ölçümle desteklendi; develop hipotezi ölçümde elendi
        tum_puanlar = {h["id"]: h["puan"] for h in
                       arsiv._yukle()["hipotezler"]}
        assert tum_puanlar["H001"] == 1.0
        assert tum_puanlar["H002"] == 0.0
