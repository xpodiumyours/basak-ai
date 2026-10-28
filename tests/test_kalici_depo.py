"""Kalici depo (Postgres) testleri.

Bu testler gercek bir Postgres ister ve `BASAK_TEST_DSN` tanimli degilse
ATLANIR. Sebep: sema/`ON CONFLICT`/`SKIP LOCKED` davranisi taklit
edilerek degil, gercek sunucuda dogrulanmalidir.

    BASAK_TEST_DSN='postgresql://kullanici@/veritabani?host=/tmp' \
        python -m pytest tests/test_kalici_depo.py
"""

import os
import threading
import time
import uuid

import pytest

DSN = os.environ.get("BASAK_TEST_DSN", "").strip()

pytestmark = pytest.mark.skipif(
    not DSN, reason="BASAK_TEST_DSN tanimli degil (gercek Postgres gerekir)")


@pytest.fixture()
def depo(monkeypatch, tmp_path):
    monkeypatch.setenv("DATABASE_URL", DSN)
    monkeypatch.setenv("BASAK_STATE_DIR", str(tmp_path))
    from chat import kosu_deposu, veritabani
    # Onceki testler SQLite defterini onbellege almis olabilir; gercek
    # Postgres'e gecmeden bu onbellek temizlenmeli.
    monkeypatch.setattr(kosu_deposu, "_DEPO", None)
    monkeypatch.setattr(kosu_deposu, "_UYARI_VERILDI", False)
    monkeypatch.setattr(veritabani, "_HAZIR", False)
    monkeypatch.setattr(veritabani, "_SON_HATA", 0.0)
    assert veritabani.hazirla(zorla=True) is True
    yield veritabani


@pytest.fixture()
def kid():
    return "u" + uuid.uuid4().hex[:16]


def test_sema_surumlu_ve_idempotent(depo):
    bilgi = depo.surum_bilgisi()
    assert bilgi["hazir"] is True
    assert 1 in bilgi["uygulanan"]
    assert depo.hazirla(zorla=True) is True
    assert depo.surum_bilgisi()["uygulanan"].count(1) == 1


def test_gecmis_ekle_oku_temizle(depo, kid):
    from chat import gecmis
    assert gecmis.ekle(kid, [
        {"role": "user", "content": "selam"},
        {"role": "assistant", "content": "merhaba", "oturum": "abc"},
    ]) == 2
    satirlar = gecmis.oku(kid)
    assert [m["role"] for m in satirlar] == ["user", "assistant"]
    assert satirlar[1]["content"] == "merhaba"
    assert gecmis.temizle(kid) is True
    assert gecmis.oku(kid) == []


def test_eszamanli_yazim_mesaj_kaybetmez(depo, kid):
    from chat import gecmis

    def yaz(i):
        gecmis.ekle(kid, [{"role": "user", "content": "m%d-%d" % (i, j)}
                          for j in range(5)])

    kollar = [threading.Thread(target=yaz, args=(i,)) for i in range(6)]
    for kol in kollar:
        kol.start()
    for kol in kollar:
        kol.join()
    assert len(gecmis.oku(kid, limit=100)) == 30


def test_hatirlatma_yasam_dongusu(depo, kid):
    from chat import hatirlatma
    kayit = hatirlatma.ekle(kid, "su ic", time.time() + 120)
    bekleyen = hatirlatma.listele(kid)["bekleyen"]
    assert [k["id"] for k in bekleyen] == [kayit["id"]]

    gecmis_kayit = hatirlatma.ekle(kid, "gecmis is", time.time() - 60)
    tetik = hatirlatma.tetikle()
    assert any(t["id"] == gecmis_kayit["id"] for t in tetik)
    # Ayni kayit ikinci kez tetiklenmez.
    assert not any(t["id"] == gecmis_kayit["id"] for t in hatirlatma.tetikle())
    assert hatirlatma.goruldu(kid, gecmis_kayit["id"]) is True
    assert hatirlatma.listele(kid)["gelen"] == []

    assert hatirlatma.sil(kid, kayit["id"]) is True
    assert hatirlatma.sil(kid, kayit["id"]) is False


def test_kuyruk_tablolari_web_tarafindan_da_acilir(depo):
    from chat import kosu_deposu
    from worker.kuyruk import Kuyruk
    kuyruk = Kuyruk()
    assert kuyruk.ad == "postgres"
    durum = kosu_deposu.isci_durumu()
    assert durum["hazir"] is True
    assert durum["neden"] == ""


def test_isci_gorevi_alir_ve_tamamlar(depo):
    from chat.platform_runtime import RuntimeStore, Worker
    store = RuntimeStore()
    sahip = "u" + uuid.uuid4().hex[:16]
    run = store.create(sahip, "personal", "selam", require_worker=False,
                       kind="chat")

    def isleyici(job, control, brain=None):
        control.artifact("answer", title="x", content="merhaba",
                         media_type="text/markdown")
        control.record_check("response_recorded", True, {"ok": True})
        return {"status": "completed", "answer": "merhaba"}

    worker = Worker(store, isleyici, worker_id="test-" + uuid.uuid4().hex[:8])
    assert worker.tick() is True
    son = store.get(sahip, run["id"])
    assert son["durum"] == "completed"
    assert son["answer"] == "merhaba"
