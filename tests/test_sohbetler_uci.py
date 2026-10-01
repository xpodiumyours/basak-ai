"""tests/test_sohbetler_uci.py — /api/sohbetler gercegi soyler (2026-10-01).

Denetim bulgusu: app.py ucu her zaman {"liste": []} donuyordu; oysa
kayitlar chat/oturum.py'de yazilip okunuyor ve yerel kopru (basak_web.py)
ayni sozlesmeyle gercek listeyi donduruyordu. Artik iki sunucu da ayni
sozlesmede: {ok: true, liste: [{id, baslik, guncellendi, adet}, ...]}.

Kilitler:
1. uc bos listeyi SABIT yazmaz — bosken gercekten bostur,
2. kayit sonrasi ayni kisi listede gorunur (gercek veri akisi),
3. sozlesme koprulle ayni anahtarlari tasiyar (ok + liste).
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient

import app as app_modulu
import chat.kimlik as kimlik
from chat import oturum

KIMLIK = "sohbetler-probe"


def _yerel_kur(monkeypatch, tmp_path):
    """Uretim DEGIL + kimlik sabit: yerel dal her istekte ayni kisiye duser."""
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("VERCEL_ENV", raising=False)
    monkeypatch.delenv("BASAK_URETIM", raising=False)
    monkeypatch.setenv("BASAK_YEREL_KIMLIK", KIMLIK)
    monkeypatch.setenv("BASAK_STATE_DIR", str(tmp_path / "state"))
    monkeypatch.delenv("BASAK_OTURUM_ANAHTARI", raising=False)
    monkeypatch.delenv("BASAK_WEB_TOKEN", raising=False)


def test_bosken_gercekten_bos_ama_sozlesme_dogru(monkeypatch, tmp_path):
    _yerel_kur(monkeypatch, tmp_path)
    with TestClient(app_modulu.app) as c:
        r = c.get("/api/sohbetler")
    assert r.status_code == 200
    d = r.json()
    assert d["ok"] is True
    assert d["liste"] == []


def test_kayit_sonrasi_listede_gorunur(monkeypatch, tmp_path):
    _yerel_kur(monkeypatch, tmp_path)
    with TestClient(app_modulu.app) as c:
        r1 = c.get("/api/sohbetler")
        assert r1.json()["liste"] == []

        # Aynı kişiye (BASAK_YEREL_KIMLIK) gerçek bir çift kaydet.
        kimlik.kullanici_kur(KIMLIK)
        try:
            sid = oturum.kaydet_cift("matris projesi ne durumda", "olcumde")
        finally:
            kimlik.kullanici_kur(kimlik.VARSAYILAN_KULLANICI)

        r2 = c.get("/api/sohbetler")
    d = r2.json()
    assert d["ok"] is True
    assert len(d["liste"]) == 1
    kayit = d["liste"][0]
    assert kayit["id"] == sid
    assert kayit["adet"] == 2
    assert "matris" in kayit["baslik"]
    assert isinstance(kayit["guncellendi"], (int, float))


def test_yabanci_kisi_kaydi_listeye_sizmaz(monkeypatch, tmp_path):
    """Sahip filtresi: baskasinin kaydi bu kisinin listesinde gorunmez."""
    _yerel_kur(monkeypatch, tmp_path)
    kimlik.kullanici_kur("baska-kisi")
    try:
        oturum.kaydet_cift("yabanci soru", "yabanci cevap")
    finally:
        kimlik.kullanici_kur(kimlik.VARSAYILAN_KULLANICI)

    with TestClient(app_modulu.app) as c:
        d = c.get("/api/sohbetler").json()
    assert d["ok"] is True
    assert d["liste"] == []


def test_api_yeni_aktif_oturumu_rotate_eder(monkeypatch, tmp_path):
    """/api/yeni bos OK degil: eski oturumu arsivler, yenisini baslatir.

    Sozlesme koprulle ayni: {ok: true, oturum: <yeni sid>}. Onceki test
    durumunda bu uc no-op'tu — tum kayitlar tek dosyada birikiyordu
    (denetim bulgusu: /api/sohbetler hep bos liste donuyordu).
    """
    _yerel_kur(monkeypatch, tmp_path)
    with TestClient(app_modulu.app) as c:
        assert c.get("/api/sohbetler").json()["liste"] == []

        kimlik.kullanici_kur(KIMLIK)
        try:
            eski_sid = oturum.kaydet_cift("ilk soru", "ilk cevap")
        finally:
            kimlik.kullanici_kur(kimlik.VARSAYILAN_KULLANICI)

        r = c.post("/api/yeni")
        assert r.status_code == 200
        d = r.json()
        assert d["ok"] is True
        yeni_sid = d["oturum"]
        assert re.fullmatch(r"[0-9a-f]{8}", yeni_sid)
        assert yeni_sid != eski_sid

        kimlik.kullanici_kur(KIMLIK)
        try:
            ikinci_sid = oturum.kaydet_cift("ikinci soru", "ikinci cevap")
        finally:
            kimlik.kullanici_kur(kimlik.VARSAYILAN_KULLANICI)
        assert ikinci_sid == yeni_sid

        liste = c.get("/api/sohbetler").json()["liste"]
        # Eski oturum arsivde, yeni oturum listede: iki ayri kayit.
        assert len(liste) == 2
        ids = {k["id"] for k in liste}
        assert ids == {eski_sid, yeni_sid}

