"""tests/test_faz3_arac_sayfalari.py — Faz 3 kabul testleri.

3.1 /araclar/<kategori>/<arac> acilir (baslik, aciklama, JSON-LD, arac calisir)
3.2 sitemap.xml guncel (katalogdaki tum araclar listelenir)
3.3 onaysiz ucuncu taraf kod yok (cerez onayi -> sonra reklam alani)
3.4 destek/bagis sayfasi baglantilari
3.5 hukuki 4 sayfa yayinda taslak
"""

import json
import os
import re
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient

import app
from araclar_sayfa import YEREL_ARACLAR, baslik_uret
from rehberler import REHBERLER
from tools.freetools_katalog import ARACLAR

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"

KATEGORI, ARAC = "security-tools", "sha-hash-generator"
ORNEK = "/araclar/%s/%s" % (KATEGORI, ARAC)


def _istemci():
    return TestClient(app.app, base_url="https://ornek.test")


class TestAracSayfasi:
    def test_ornek_sayfa_acilir_ve_etiketleri_tam(self):
        with _istemci() as c:
            r = c.get(ORNEK)
        assert r.status_code == 200
        h = r.text
        assert "<title>" in h and "ücretsiz çevrimiçi araç" in h
        assert '<meta name="description"' in h
        assert 'rel="canonical" href="https://ornek.test%s"' % ORNEK in h
        assert '<meta name="robots" content="index,follow"' in h
        assert "og:title" in h and "og:url" in h

    def test_jsonld_gecerli_ve_bagli(self):
        with _istemci() as c:
            h = c.get(ORNEK).text
        ham = re.search(
            r'<script type="application/ld\+json">(.*?)</script>', h,
            re.DOTALL).group(1)
        veri = json.loads(ham)
        assert veri["@type"] == "WebApplication"
        assert veri["isAccessibleForFree"] is True
        assert veri["name"] == baslik_uret(ARAC, KATEGORI)
        assert veri["url"] == "https://ornek.test" + ORNEK
        assert veri["breadcrumb"]["@type"] == "BreadcrumbList"
        assert veri["offers"]["price"] == "0"

    def test_sayfada_harici_kod_yok_atif_var(self):
        with _istemci() as c:
            h = c.get(ORNEK).text
        # Kanonik adres / etiket baglantisi kod yuklemez; onemli olan
        # <script>/<img>/<iframe> ve harici stil dosyasi olmamasi.
        assert not re.search(
            r"<(?:script|img|iframe|source|embed)\b[^>]*?"
            r"(?:src)\s*=\s*[\"']https?://", h)
        assert not re.search(
            r"<link\b[^>]*rel=[\"']stylesheet[\"'][^>]*"
            r"href=[\"']https?://", h)
        assert "/araclar.js" in h and "/araclar.css" in h
        assert "freetools.org" in h            # atif baglantisi
        assert 'rel="noopener noreferrer nofollow"' in h
        assert "ortaklık yoktur" in h

    def test_tarayicida_calisan_arac_formu_var(self):
        with _istemci() as c:
            h = c.get(ORNEK).text
        assert 'window.ARAC_SLUG="sha-hash-generator"' in h
        assert 'id="hesapla"' in h and 'id="sonuc"' in h
        assert 'id="g0"' in h and 'id="g1"' in h

    def test_desteklenmeyen_arac_bilgi_verir_uydurma_sonuc_vermez(self):
        yol = "/araclar/code-tools/sql-formatter"
        with _istemci() as c:
            r = c.get(yol)
            assert r.status_code == 200
            h = r.text
        assert 'id="hesapla"' not in h
        assert "Basak sohbetinde" in h
        assert "freetools.org" in h

    def test_bilinmeyen_sayfa_404(self):
        with _istemci() as c:
            assert c.get("/araclar/olmayan-kategori/olmayan-arac").status_code == 404
            assert c.get("/araclar/security-tools/olmayan").status_code == 404

    def test_tum_katalog_sayfalari_acilir(self):
        """3.1: katalogdaki her arac sayfasi acilir (404 yok)."""
        with _istemci() as c:
            for kat, slug in ARACLAR:
                r = c.get("/araclar/%s/%s" % (kat, slug))
                assert r.status_code == 200, (kat, slug, r.status_code)
                assert "application/ld+json" in r.text

    def test_arac_listesi_sayfasi(self):
        with _istemci() as c:
            h = c.get("/araclar").text
        assert c.get("/araclar").status_code == 200
        assert "Ücretsiz araçlar" in h
        assert h.count('href="/araclar/') >= len(ARACLAR)


class TestSiteHaritasi:
    def test_sitemap_gecerli_ve_guncel(self):
        with _istemci() as c:
            r = c.get("/sitemap.xml")
        assert r.status_code == 200
        assert r.headers["content-type"].startswith("application/xml")
        kok = ET.fromstring(r.text)
        ns = "{http://www.sitemaps.org/schemas/sitemap/0.9}"
        loclar = [e.text for e in kok.findall("%surl/%sloc" % (ns, ns))]
        assert len(loclar) == len(ARACLAR) + 10 + len(REHBERLER)
        # arac + 10 sabit sayfa (rehber listesi dahil) + rehber sayfalari
        for kat, slug in ARACLAR:
            assert "https://ornek.test/araclar/%s/%s" % (kat, slug) in loclar
        for zorunlu in ("/", "/araclar", "/rehber", "/gizlilik.html",
                        "/cerez.html", "/sartlar.html", "/sorumluluk.html",
                        "/destek.html", "/reklam-ver.html",
                        "/bilgilendirme.html"):
            assert "https://ornek.test" + zorunlu in loclar

    def test_sitemap_katalogla_purussuz(self):
        """Yeni arac eklenince harita otomatik genisler (tek kaynak)."""
        with _istemci() as c:
            h = c.get("/sitemap.xml").text
        assert h.count("<loc>") == len(ARACLAR) + 10 + len(REHBERLER)


class TestRobots:
    def test_izin_var_yasak_yok(self):
        with _istemci() as c:
            r = c.get("/robots.txt")
        assert r.status_code == 200
        metin = r.text
        assert "User-agent: *" in metin
        assert "Allow: /" in metin
        assert "Disallow: /" not in metin        # otomatik erisim yasagi yok
        assert "Sitemap: https://ornek.test/sitemap.xml" in metin


class TestYerelAracKapsami:
    def test_python_ile_tarayici_js_eslesir(self):
        """Her yerel aracin sayfasi + JS hesaplayicisi vardir."""
        js = (WEB / "araclar.js").read_text(encoding="utf-8")
        for slug in YEREL_ARACLAR:
            assert '"%s":' % slug in js, slug
        assert "crypto.subtle" in js            # WebCrypto
        assert "BigInt" in js

    def test_js_freetools_kodunu_kopyalamaz(self):
        """Yerel hesap standart algoritmadir; ag cagrisi JS'te yoktur."""
        js = (WEB / "araclar.js").read_text(encoding="utf-8")
        assert "fetch(" not in js
        assert not re.search(r"XMLHttpRequest|importScripts", js)


class TestYeniMetinKodAraclari:
    """8 yeni arac: sayfa acilir, form var, ipucu var, JS hesabi var."""

    YENILER = (
        ("text-tools", "character-remover", "Karakter Silici"),
        ("text-tools", "character-replacer", "Karakter Değiştirici"),
        ("text-tools", "tabs-to-space", "Sekme Boşluk Çevirici"),
        ("text-tools", "text-splitter", "Metin Bölücü"),
        ("text-tools", "space-remover", "Fazla Boşluk Temizleyici"),
        ("text-tools", "comma-inserter", "Virgül Ekleyici"),
        ("code-tools", "json-formatter", "JSON Biçimlendirici"),
        ("code-tools", "html-entities", "HTML Entity Kodlayıcı"),
    )

    def test_yeni_sayfalar_acilir_form_var(self):
        with _istemci() as c:
            for kat, slug, baslik in self.YENILER:
                r = c.get("/araclar/%s/%s" % (kat, slug))
                assert r.status_code == 200, (kat, slug)
                h = r.text
                assert baslik in h, (slug, "baslik yok")
                assert 'id="hesapla"' in h, (slug, "form yok")
                assert 'id="sonuc"' in h, (slug, "sonuc alani yok")
                assert 'window.ARAC_SLUG="%s"' % slug in h, (slug,)
                assert "freetools.org" in h            # atif baglantisi
                assert "ortaklık yoktur" in h

    def test_yeni_araclar_js_hesabinda(self):
        js = (WEB / "araclar.js").read_text(encoding="utf-8")
        for _kat, slug, _baslik in self.YENILER:
            assert '"%s":' % slug in js, slug
        # yeni hesaplar aga cikmaz (standart algoritma)
        assert "fetch(" not in js

    def test_yeni_araclar_jsonld_gecerli(self):
        with _istemci() as c:
            for kat, slug, _baslik in self.YENILER:
                h = c.get("/araclar/%s/%s" % (kat, slug)).text
                ham = re.search(
                    r'<script type="application/ld\+json">(.*?)</script>', h,
                    re.DOTALL).group(1)
                veri = json.loads(ham)
                assert veri["@type"] == "WebApplication"
                assert veri["isAccessibleForFree"] is True
                assert veri["offers"]["price"] == "0"


class TestCerezOnayiVeReklam:
    """3.3: onay VERILMEDEN reklam kodu yuklenmez."""

    def test_arac_sayfasinda_onay_bandi_ve_gizli_reklam_alani(self):
        with _istemci() as c:
            h = c.get(ORNEK).text
        assert 'id="cerezBandi"' in h and 'hidden' in h
        assert 'id="reklamAlani"' in h
        # reklam alani HTML'de gizli baslar (hidden), JS acar
        alan = re.search(r'<div class="reklam" id="reklamAlani"[^>]*>', h)
        assert "hidden" in alan.group(0)

    def test_onaydan_once_kod_yuklenmez(self):
        js = (WEB / "araclar.js").read_text(encoding="utf-8")
        assert 'if (!onay || !onay.reklam) { alan.hidden = true; return; }' in js
        # reklam etiketi yalnizca onay sonrasi olusturulur
        onay_i = js.find("onay.reklam")
        etiket_i = js.find('document.createElement("script")')
        assert onay_i != -1 and etiket_i != -1 and onay_i < etiket_i
        # adres dosyada sabit degil, sayfadaki meta etiketinden gelir
        assert 'meta[name="reklam-yerlesimi"]' in js
        assert not re.search(r"reklam[^=]*=\s*[\"']https?://", js)

    def test_onay_kaydi_sadece_tarayicida(self):
        js = (WEB / "araclar.js").read_text(encoding="utf-8")
        assert "localStorage" in js
        assert "basak_cerez_onay_v1" in js


class TestHukukiSayfalar:
    TASLAKLAR = ("gizlilik.html", "cerez.html", "sartlar.html",
                 "sorumluluk.html")

    def test_dort_sayfa_taslak_ve_bagli(self):
        for ad in self.TASLAKLAR:
            with _istemci() as c:
                r = c.get("/" + ad)
            assert r.status_code == 200, ad
            assert "TASLAK" in r.text, ad
            assert 'rel="canonical" href="/%s"' % ad in r.text, ad

    def test_cerez_politikasi_guncel_olcum_modelini_yaziyor(self):
        metin = (WEB / "cerez.html").read_text(encoding="utf-8")
        assert "Çerezsiz anonim sayım (onay gerektirmez)" in metin
        assert "yalnız onaydan sonra yüklenir" in metin
        assert 'id="reklamAgiAdi"' in metin

    def test_rehber_sayfalari_sitemapte(self):
        with _istemci() as c:
            h = c.get("/sitemap.xml").text
        for r in REHBERLER:
            assert "https://ornek.test/rehber/%s" % r["slug"] in h

    def test_gizlilik_metni_envanterle_ayni_verileri_soyler(self):
        metin = (WEB / "gizlilik.html").read_text(encoding="utf-8").lower()
        for anahtar in ("başak id", "sohbet geçmişi", "kalıcı hafıza",
                        "görsel ek", "ip ve günlük", "kota sayacı",
                        "sağlayıcıya giden mesaj"):
            assert anahtar in metin, anahtar

    def test_cerez_politikasi_zorunlu_cerezleri_adiyla_yaziyor(self):
        metin = (WEB / "cerez.html").read_text(encoding="utf-8")
        assert "basak_oturum" in metin
        assert "basak_cerez_onay_v1" in metin
        assert "onay vermeden üçüncü taraf kod çalışmaz" in metin

    def test_destek_sayfasi_calisan_baglanti_var(self):
        with _istemci() as c:
            h = c.get("/destek.html").text
        assert c.get("/destek.html").status_code == 200
        assert "Bağış" in h and "Sponsorluk" in h
        assert 'href="https://github.com/xpodiumyours/basak-ai"' in h
        assert 'rel="noopener noreferrer"' in h

    def test_ana_sayfa_yeni_sayfalara_bagli(self):
        index = (WEB / "index.html").read_text(encoding="utf-8")
        for yol in ("/araclar", "/gizlilik.html", "/cerez.html",
                    "/sartlar.html", "/sorumluluk.html", "/destek.html"):
            assert 'href="%s"' % yol in index, yol


class TestAracKapsamiDurust:
    """Faz 0 (2026-10-02): liste sayfasi GERCEK kapsami soyler.

    Once "/araclar" sayfasi "162 aracin hepsi tarayicinizda calisir" diyordu;
    oysa tarayicida hesaplayan 22 arac var (YEREL_ARACLAR). Bu sinif o yanlis
    iddianin geri gelmesini engeller ve sayilarin tek kaynaktan geldigini
    dogrular.
    """

    ESKI_YANLIS = ("hepsi tarayıcınızda çalışır",
                   "hepsi tarayicinizda calisir")

    def test_liste_sayfasi_hepsi_tarayicida_demez(self):
        with _istemci() as c:
            h = c.get("/araclar").text
        for yanlis in self.ESKI_YANLIS:
            assert yanlis not in h, yanlis

    def test_liste_sayfasi_gercek_sayilari_soyler(self):
        from araclar_sayfa import tarayici_kapsami
        toplam, hesaplayan = tarayici_kapsami()
        assert toplam == len(ARACLAR)
        assert hesaplayan == len(YEREL_ARACLAR)
        assert hesaplayan < toplam          # "hepsi" iddiasi matematiksel olarak yanlis
        with _istemci() as c:
            h = c.get("/araclar").text
        assert "Bu listede %d ücretsiz araç var" % toplam in h
        assert "Bunlardan %d tanesi doğrudan" % hesaplayan in h
        assert "tarayıcınızda hesaplar" in h

    def test_kategori_basliklari_kapsami_yazar(self):
        from araclar_sayfa import kategori_kapsami
        kapsam = kategori_kapsami()
        with _istemci() as c:
            h = c.get("/araclar").text
        for kat, (toplam, tarayici) in kapsam.items():
            beklenen = "(%d araç · tarayıcıda %d)" % (toplam, tarayici)
            assert beklenen in h, (kat, beklenen)


class TestDerinBaglanti:
    def test_arac_sayfasi_sohbete_derin_baglanti_verir(self):
        with _istemci() as c:
            h = c.get(ORNEK).text
        es = re.search(r'href="/\?soru=([^"]+)"', h)
        assert es, "sohbete derin baglanti yok"
        from urllib.parse import unquote
        assert "sha" in unquote(es.group(1)).lower()

    def test_anasayfa_soru_parametresini_doldurur(self):
        ui = (WEB / "app.js").read_text(encoding="utf-8")
        assert 'get("soru")' in ui
        assert "URLSearchParams" in ui
