"""tests/test_kisi_hafiza.py — Çok kullanıcılı hafıza ayrımı (2026-09-23).

Dal: feat/kisi-hafiza. Kod: chat/kimlik.py, kullanici.py, chat/oturum.py,
chat/context.py, memory/engine.py.

Kurallar:
- Her test tmp_path + monkeypatch ile izole; gerçek data/'ya yazılmaz.
- kimlik.BASE de yamalanır — taşıma testi asla repo kökündeki gerçek
  gecmis.json'a dokunmaz.
- conftest'e ve başka test dosyalarına dokunulmaz.
"""

import contextvars
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import kullanici as kullanici_modulu
from chat import context as ctx
from chat import kimlik, oturum


def _izole(monkeypatch, tmp_path):
    """Geçici state + kullanıcı tablosu; yollar dinamik (kimlikten)."""
    state = tmp_path / "state"
    monkeypatch.setenv("BASAK_STATE_DIR", str(state))
    # Taşıma asla gerçek repo köküne (BASE/gecmis.json) dokunmasın:
    monkeypatch.setattr(kimlik, "BASE", str(tmp_path / "proje"))
    monkeypatch.setattr(kimlik, "_MIGRASYON_YAPILDI", False)
    monkeypatch.setattr(kullanici_modulu, "KULLANICI_DOSYA",
                        str(tmp_path / "kullanicilar.json"))
    monkeypatch.setattr(oturum, "DIZIN", None)
    monkeypatch.setattr(oturum, "AKTIF_DOSYA", None)
    return state


@pytest.fixture
def hafiza_sifir(monkeypatch):
    """ctx hafıza önbelleği boş; anlam vektörü kapalı (ag yok, BM25-only)."""
    ctx.hafizalari_kapat()
    monkeypatch.setattr(ctx, "_hafiza", None)
    monkeypatch.setattr(ctx, "_anlam_fn", lambda: None)
    yield
    ctx.hafizalari_kapat()


# ── 1. İki kişinin hafızası ayrılır ─────────────────────────────────

def test_iki_kisi_hafizasi_ayrilir(monkeypatch, tmp_path, hafiza_sifir):
    _izole(monkeypatch, tmp_path)

    kimlik.kullanici_kur("casper")
    casper = ctx.hafiza_al()
    assert casper is not None
    assert casper.episodik_kaydet("X sırrım", "gizli cevap") is True
    assert casper.ara("X sırrım"), "casper kendi sırını bulamadı"

    kimlik.kullanici_kur("ayse")
    ayse = ctx.hafiza_al()
    assert ayse is not None and ayse is not casper
    assert ayse.ara("X sırrım") == [], "ayse casper'ın sırrını görmemeli"

    kimlik.kullanici_kur("casper")
    geri = ctx.hafiza_al()
    assert geri is casper
    assert geri.ara("X sırrım"), "casper'a dönünce sır yeniden bulunmalı"


# ── 2. Sohbet listesi ayrılır ───────────────────────────────────────

def test_sohbet_ayrilir(monkeypatch, tmp_path):
    _izole(monkeypatch, tmp_path)

    kimlik.kullanici_kur("casper")
    sid = oturum.kaydet_cift("casper sorusu", "casper cevabi")
    assert sid
    assert any(x["id"] == sid for x in oturum.liste())

    kimlik.kullanici_kur("ayse")
    ayse_idleri = [x["id"] for x in oturum.liste()]
    assert sid not in ayse_idleri, "ayse casper'ın sohbetini görmemeli"
    assert ayse_idleri == [], "ayse farklı dizinde, listesi boş olmalı"

    kimlik.kullanici_kur("casper")
    assert any(x["id"] == sid for x in oturum.liste()), \
        "casper'a dönünce sohbeti yerinde olmalı"


# ── 3. Oturum sahipliği ─────────────────────────────────────────────

def test_oturum_sahipligi(monkeypatch, tmp_path):
    state = _izole(monkeypatch, tmp_path)

    kimlik.kullanici_kur("casper")
    sid = oturum.kaydet_cift("soru", "cevap")

    yol = state / "casper" / "sohbetler" / ("%s.json" % sid)
    kayit = json.loads(yol.read_text(encoding="utf-8"))
    assert kayit["sahip"] == "casper", "oturum JSON'una sahip=casper damgası"

    assert oturum.sahip_mi(sid, "casper") is True
    assert oturum.sahip_mi(sid, "ayse") is False


# ── 4. Şifre düz metin saklanmaz ────────────────────────────────────

def test_sifre_duz_metin_degil(monkeypatch, tmp_path):
    _izole(monkeypatch, tmp_path)
    sifre = "S3ifre!"

    assert kullanici_modulu.kullanici_ekle("ayse", sifre) == "ayse"

    ham = Path(kullanici_modulu.kullanici_dosyasi()).read_text(
        encoding="utf-8")
    assert sifre not in ham, "şifre JSON'da düz metin geçmemeli"

    kayit = kullanici_modulu.kullanici_listesi()["ayse"]
    assert kullanici_modulu.dogrula(sifre, kayit["hash"]) is True
    assert kullanici_modulu.dogrula("yanlis-sifre", kayit["hash"]) is False


# ── 5. Taşıma tek sefer ─────────────────────────────────────────────

def test_tasima_tek_sefer(monkeypatch, tmp_path):
    state = _izole(monkeypatch, tmp_path)

    # Eski tek kişilik yapı: data/sohbetler + data/memory + data/gecmis
    (state / "sohbetler").mkdir(parents=True)
    (state / "sohbetler" / "eski.json").write_text('{"id": "eski"}',
                                                   encoding="utf-8")
    (state / "memory").mkdir(parents=True)
    (state / "memory" / "basak.db").write_bytes(b"eski-db")
    (state / "gecmis.json").write_text("[]", encoding="utf-8")

    say = kimlik.migrasyon_yap()
    assert say == 3, "sohbetler + basak.db + gecmis taşınmalı"

    hedef = state / "casper"
    assert (hedef / "sohbetler" / "eski.json").exists()
    assert (hedef / "memory" / "basak.db").exists()
    assert (hedef / "gecmis.json").exists()

    # Eski yerlerde dosya kalmaz:
    assert not (state / "sohbetler").exists()
    assert not (state / "memory" / "basak.db").exists()
    assert not (state / "gecmis.json").exists()

    # Bayrak yazıldı; ikinci çağrı 0 taşır, hedefe dokunmaz:
    assert kimlik.migrasyon_gerekli_mi() is False
    assert kimlik.migrasyon_yap() == 0
    assert (hedef / "sohbetler" / "eski.json").exists()
    assert (hedef / "memory" / "basak.db").exists()


# ── 6. Yerel varsayılan ─────────────────────────────────────────────

def test_yerel_varsayilan_casper(monkeypatch, tmp_path):
    _izole(monkeypatch, tmp_path)
    # Bu testte kullanici_kur ÇAĞRILMAZ. Boş Context, hiç set
    # edilmemiş fabrika değerini gösterir (yerel/CLI davranışı).
    bos = contextvars.Context()
    assert bos.run(kimlik.aktif_kullanici) == "casper"


# ── 7. Giriş zorunluluğu ────────────────────────────────────────────

def test_giris_zorunlu_mu(monkeypatch, tmp_path):
    _izole(monkeypatch, tmp_path)

    assert kullanici_modulu.giris_zorunlu_mu() is False, \
        "tablo boşken tek-kullanıcı modu"
    assert kullanici_modulu.kullanici_ekle("ayse", "S3ifre!") == "ayse"
    assert kullanici_modulu.giris_zorunlu_mu() is True, \
        "ilk kullanıcı eklenince giriş zorunlu"


# ── 9. ASCII dışı çerez sunucuyu çökertmez ──────────────────────────

def test_bozuk_cerez_cokmez(monkeypatch, tmp_path):
    """İmzası Türkçe harf içeren çerez 500 değil, geçersiz sayılmalı.

    Ölçüm (2026-09-23, canlı): X-Basak-Token: "Başak123" → HTTP 500.
    Sebep: hmac.compare_digest ASCII dışı str'de TypeError fırlatır.
    """
    _izole(monkeypatch, tmp_path)

    assert kullanici_modulu.oturum_coz("YWJj.şşş") is None
    assert kullanici_modulu.oturum_coz("YWJj.Başak123") is None

    # Geçerli yol bozulmadı.
    kullanici_modulu.kullanici_ekle("ayse", "S3ifre!")
    token = kullanici_modulu.oturum_tokeni_uret("ayse")
    assert kullanici_modulu.oturum_coz(token) == "ayse"
