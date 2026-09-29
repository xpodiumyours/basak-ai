"""tests/test_rehber.py — Turkce rehber sayfalari (/rehber) bekcileri.

Sozlesme:
- /rehber listeler; her slug acilir; bilinmeyen 404 doner.
- Sayfa: baslik, aciklama, canonical, JSON-LD Article; harici kod yok.
- Ic baglantilar gercekten var olan sayfalara gider (uydurma adres yok);
  [[slug]] isareti cozumsuz kalmaz.
- IndexNow anahtar dosyasi yayina hazirdir (adi ve icerigi ayni).
- Gonderici betigi (scripts/indexnow.py) bilinen yollari eksiksiz toplar.
"""

import importlib.util
import json
import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

import app
from rehberler import REHBERLER
from tools.freetools_katalog import ARACLAR

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"


def _istemci():
    return TestClient(app.app, base_url="https://ornek.test")


class TestRehberSayfalari:
    def test_liste_acilir(self):
        with _istemci() as c:
            h = c.get("/rehber").text
        assert c.get("/rehber").status_code == 200
        assert "Rehberler" in h
        for r in REHBERLER:
            assert "/rehber/%s" % r["slug"] in h

    def test_her_rehber_acilir_ve_etiketleri_tam(self):
        for r in REHBERLER:
            with _istemci() as c:
                yanit = c.get("/rehber/%s" % r["slug"])
            assert yanit.status_code == 200, r["slug"]
            h = yanit.text
            assert r["baslik"] in h and r["aciklama"] in h
            assert ("rel=\"canonical\" href=\"https://ornek.test/rehber/%s\""
                    % r["slug"]) in h
            assert '<meta name="robots" content="index,follow"' in h
            assert "/olcum.js" in h

    def test_jsonld_gecerli(self):
        for r in REHBERLER:
            with _istemci() as c:
                h = c.get("/rehber/%s" % r["slug"]).text
            ham = re.search(
                r'<script type="application/ld\+json">(.*?)</script>', h,
                re.DOTALL).group(1)
            veri = json.loads(ham)
            assert veri["@type"] == "Article"
            assert veri["inLanguage"] == "tr"
            assert veri["headline"] == r["baslik"]

    def test_bilinmeyen_404(self):
        with _istemci() as c:
            assert c.get("/rehber/olmayan-rehber").status_code == 404

    def test_harici_kod_yok(self):
        for r in REHBERLER:
            with _istemci() as c:
                h = c.get("/rehber/%s" % r["slug"]).text
            assert not re.search(
                r"<(?:script|img|iframe|source|embed)\b[^>]*?"
                r"(?:src)\s*=\s*[\"']https?://", h)
            assert not re.search(
                r"<link\b[^>]*rel=[\"']stylesheet[\"'][^>]*"
                r"href=[\"']https?://", h)

    def test_baglanti_isaretleri_cozulmus_ve_gercek(self):
        katalog = {"/araclar/%s/%s" % (k, s) for k, s in ARACLAR}
        parcalar = {r["slug"] for r in REHBERLER}
        for r in REHBERLER:
            with _istemci() as c:
                h = c.get("/rehber/%s" % r["slug"]).text
            assert "[[" not in h and "]]" not in h, r["slug"]
            for b in re.findall(r'href="(/[^"]+)"', h):
                assert not b.startswith("//"), b
            for b in re.findall(
                    r'href="(/araclar/[^"]+)"', h):
                assert b in katalog, (r["slug"], b)
            for b in re.findall(
                    r'href="(/rehber/[^"]+)"', h):
                assert b[8:] in parcalar, (r["slug"], b)
            assert 'href="/?soru=' in h

    def test_sitemap_rehberleri_icerir(self):
        with _istemci() as c:
            h = c.get("/sitemap.xml").text
        assert "https://ornek.test/rehber" in h
        for r in REHBERLER:
            assert "https://ornek.test/rehber/%s" % r["slug"] in h


class TestIndexNowHazirligi:
    def _anahtar(self):
        adaylar = [y for y in WEB.glob("*.txt")
                   if re.fullmatch(r"[0-9a-f]{32}", y.stem)]
        assert adaylar, "web/ altinda IndexNow anahtar dosyasi yok"
        return adaylar[0]

    def test_anahtar_dosyasi_canli_ve_eslesiyor(self):
        dosya = self._anahtar()
        anahtar = dosya.read_text(encoding="utf-8").strip()
        assert anahtar == dosya.stem
        with _istemci() as c:
            r = c.get("/%s.txt" % anahtar)
        assert r.status_code == 200
        assert r.text.strip() == anahtar

    def test_gonderici_yollari_toplar(self):
        ozellik = importlib.util.spec_from_file_location(
            "indexnow_kilavuz", str(ROOT / "scripts" / "indexnow.py"))
        modul = importlib.util.module_from_spec(ozellik)
        ozellik.loader.exec_module(modul)
        assert modul.anahtar_bul() != ""
        yollar = modul.yollari_topla()
        assert yollar[0] == "/" and "/rehber" in yollar
        for r in REHBERLER:
            assert "/rehber/%s" % r["slug"] in yollar
        ornek = "/araclar/security-tools/sha-hash-generator"
        assert ornek in yollar
