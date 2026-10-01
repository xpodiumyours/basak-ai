"""tests/test_url_kodlama.py — URL kodlama hataları (2026-10-01, P1.4 ölçümü).

Kök neden gecikme ölçümünde çıktı, tahminle bulunmadı:

1. **Çift kodlama.** `urllib.parse.quote()` varsayılan olarak `%` işaretini
   de kodlar. Zaten kodlanmış bir URL gelince ikinci kez kodlanıyordu:
   `/wiki/Ba%C5%9Fak` → `/wiki/Ba%25C5%259Fak` → **HTTP 404**.
   Gerçek ölçüm: `sayfa_oku("https://tr.wikipedia.org/wiki/Ba%C5%9Fak")`
   404 döndürüyordu, `.../çilek` çalışıyordu.

2. **Ham Türkçe karakter.** Yalnız PATH kodlanıyordu; QUERY ve NETLOC
   ham kalıyordu. Türkçe karakter içeren bir adresteki
   `UnicodeEncodeError` ("'ascii' codec can't encode character '\\xe7'")
   **tüm sayfa okumayı** hata verdiriyordu. Gerçek ölçüm:
   `sirket_ara("Trendyol")` aday sayfalardan birinde bu yüzden düşüyordu.

Sözleşme:
- Zaten kodlanmış karakterlere dokunulmaz (`%` güvenli).
- Ham Türkçe karakter yolda, sorguda ve alan adında kodlanır.
- **SSRF denetimi bozulmaz** — kodlama sonrası denetim aynı yerde çalışır.

Ağ yok: yalnız URL dönüşümü ve güvenlik engeli ölçülür.
"""

import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import web_search as ws


@pytest.fixture
def yakalanan(monkeypatch):
    """Gerçek ağ yerine, Request'e giden son URL'i yakalar."""
    tutulan = {}

    class _Yalanci:
        def __init__(self, url, headers=None):
            tutulan["url"] = url
            raise _YalgiDurdur()

    monkeypatch.setattr(ws.urllib.request, "Request", _Yalanci)
    return tutulan


class _YalgiDurdur(Exception):
    """Ağa cikmadan once URL kaydedildi; simdi dur."""


def _yola_giden_url(url):
    """sayfa_oku'ya giren URL'i ağ olmadan cikar."""
    tutulan = {}
    gercek = ws.urllib.request.Request

    class _Yalanci:
        def __init__(self, u, headers=None):
            tutulan["url"] = u
            raise _YalgiDurdur()

    ws.urllib.request.Request = _Yalanci
    try:
        ws.sayfa_oku(url)
    except _YalgiDurdur:
        pass
    except Exception:
        pass
    finally:
        ws.urllib.request.Request = gercek
    return tutulan.get("url")


class TestCiftKodlamaYok:
    def test_kodlanmis_yol_bozulmaz(self):
        """Zaten kodlanmış %XX dokunulmaz (404 kok nedeni)."""
        giden = _yola_giden_url("https://tr.wikipedia.org/wiki/Ba%C5%9Fak")
        assert giden is not None, "ağa cikamadi"
        assert "%25" not in giden, "cift kodlama var: %s" % giden
        assert "Ba%C5%9Fak" in giden, giden

    def test_yuzde_isareti_ayni_kalir(self):
        giden = _yola_giden_url("https://example.com/a%20b")
        assert giden.endswith("/a%20b"), giden

    def test_yuzdesiz_url_de_ayni_kalir(self):
        giden = _yola_giden_url("https://example.com/normal")
        assert giden.endswith("/normal"), giden


class TestTurkceKodlanir:
    def test_yoldaki_turkce_karakter_kodlanir(self):
        giden = _yola_giden_url("https://tr.wikipedia.org/wiki/çilek")
        assert "ç" not in giden, "kodlanmadi: %s" % giden
        assert "%C3%A7" in giden, giden

    def test_sorgudaki_turkce_karakter_kodlanir(self):
        giden = _yola_giden_url("https://example.com/a?q=iletişim")
        assert giden is not None
        assert "ş" not in giden, "sorgu kodlanmadi: %s" % giden

    def test_sorgudaki_kodlanmis_deger_bozulmaz(self):
        giden = _yola_giden_url("https://example.com/a?k=%C3%A7")
        assert giden.endswith("?k=%C3%A7"), giden

    def test_unicode_hatasi_yok(self):
        """'ascii' codec hatasinin kaynagi giderilmis olmali."""
        giden = _yola_giden_url("https://tr.wikipedia.org/wiki/Türkçe")
        try:
            giden.encode("ascii")
        except UnicodeEncodeError as e:
            pytest.fail("yol hala ASCII disi: %s (%s)" % (giden, e))
        assert giden is not None


class TestGuvenlikAyakta:
    """Kodlama duzeltmesi SSRF denetimini zayiflatmamali."""

    def test_ice_adres_yine_engelli(self):
        r = ws.sayfa_oku("http://127.0.0.1/x")
        assert "Guvenlik engeli" in r.get("error", ""), r

    def test_kodlanmis_ice_adres_yine_engelli(self):
        """Kodlama sonrasi denetim ayni yerde calismali."""
        r = ws.sayfa_oku("http://127.0.0.1/%2Fx")
        assert "Guvenlik engeli" in r.get("error", ""), r

    def test_sayfa_bos_url_hata_verir(self):
        r = ws.sayfa_oku("")
        assert "error" in r


class TestOlcumDogrulugu:
    """Yol yardimcimiz gercekten test edilen kodu gosteriyor mu?"""

    def test_yardimci_sayfa_okunun_ayni_yolundan_gecer(self, monkeypatch):
        """`or True` yazan sahte bir dogrulama olmasin diye: yardimci
        gercekten sayfa_oku -> _sayfa_oku_genis zincirinden geciyor.
        Zincirin ikinci halkasi ulasilabilir degilse, kodlamanin
        kondugu yer degistiyse bu test kirmiziya doner."""
        gorulen = []
        gercek = ws._sayfa_oku_genis

        def izle(url, *a, **kw):
            gorulen.append(url)
            raise _YalgiDurdur()

        monkeypatch.setattr(ws, "_sayfa_oku_genis", izle)
        try:
            ws.sayfa_oku("https://tr.wikipedia.org/wiki/çilek")
        except _YalgiDurdur:
            pass
        assert gorulen == ["https://tr.wikipedia.org/wiki/çilek"], (
            "sayfa_oku _sayfa_oku_genis'i cagirmiyor — test yanlis yeri "
            "olcuyor olabilir: %s" % gorulen)

    def test_yardimci_somut_url_dondurur(self):
        giden = _yola_giden_url("https://tr.wikipedia.org/wiki/çilek")
        assert giden, "yardimci URL dondurmedi"
        assert giden.startswith("https://")


# ── 2026-10-01: aynı hata İKİNCİ kez, BAŞKA yolda ──────────────────
#
# Düzeltme `sayfa_oku` yoluna konmuştu. Üretim denetimindeki canlı
# `sirket_ara` koşusu bu satırı döndürdü:
#   "Sayfa okuma hatasi: 'ascii' codec can't encode character '\\xe7'"
# İzleme gösterdi adres `sayfa_oku`'ya değil `kurum_sayfasi_oku` →
# `_ham_sayfa_getir` hattına giriyor; orada kodlama HİÇ YOKTU.
# Düzeltme: yardımcı TEK yere toplandı ve her çağrı yolu onu çağırıyor.

_KURUM_UL = ("https://www.accio.com/supplier/tr/"
             "trendyol-tedarikçi-iletişim")


@pytest.fixture
def dns_kapali(monkeypatch):
    """Ağ/DNS bağımlılığını keser; IP denetimi `_guvenli_adres` içinde
    yine de çalışır, yalnız çözümleme sabitlenir."""
    monkeypatch.setattr(ws, "_engelli_ip_nedeni", lambda host: None)


def _kurum_yolundan_cikan_url():
    tutulan = {}

    def _acici(req, timeout=None):
        tutulan["url"] = req.full_url
        raise _YalgiDurdur()

    try:
        ws._ham_sayfa_getir(_KURUM_UL, _acici=_acici)
    except _YalgiDurdur:
        pass
    return tutulan.get("url")


class TestKurumSayfasiYolu:
    """Ölçülen kusurun kendisi: `sirket_ara` aday yolu ASCII değil."""

    def test_ham_turkce_yol_kodlanir(self, dns_kapali):
        giden = _kurum_yolundan_cikan_url()
        assert giden is not None, "ağa cikamadi"
        assert giden.isascii(), "yol hala ASCII disi: %r" % giden
        assert "%C3%A7" in giden and "%C5%9F" in giden, giden

    def test_kurum_yolunda_guvenlik_denetimi_yine_var(self, monkeypatch):
        """Kodlama eklenirken SSRF denetimi atlanmamalı."""
        gorulen = []

        def _sahte(url, *a, **kw):
            gorulen.append(url)
            raise _YalgiDurdur()

        monkeypatch.setattr(ws, "_url_kodla", _sahte)
        try:
            ws._ham_sayfa_getir(_KURUM_UL, _acici=lambda *a, **kw: None)
        except _YalgiDurdur:
            pass
        assert gorulen == [_KURUM_UL], (
            "kurum yolu _url_kodla'yi cagirmiyor — test yanlis yeri "
            "olcuyor olabilir: %s" % gorulen)

    def test_kurum_yolunda_kodlama_guvenlikten_once(self, dns_kapali,
                                                     monkeypatch):
        """Sıra önemli: kodlanmamış adres denetime girmemeli."""
        sira = []
        gercek = ws._guvenli_adres

        def _izle(url):
            sira.append(url)
            return gercek(url)

        monkeypatch.setattr(ws, "_guvenli_adres", _izle)
        try:
            ws._ham_sayfa_getir(_KURUM_UL, _acici=lambda *a, **kw: None)
        except Exception:
            pass
        assert sira, "denetim hic cagrilmadi"
        assert sira[0].isascii(), "denetim kodlanmamis URL'yi gormus: %r" % sira[0]

    def test_kurum_yolunda_ice_adres_yine_engelli(self):
        r = ws._ham_sayfa_getir("http://127.0.0.1/ç")
        ham, _son, hata = r
        assert ham is None and hata, r
        assert "Guvenlik engeli" in hata["error"], hata


def _istek_tutan(monkeypatch):
    """Request'e giden URL'i yakalar, agi URLError ile keser."""
    tutulan = {}

    def _istek(url, headers=None, method=None):
        tutulan["url"] = url
        raise ws.urllib.error.URLError("ag kapali (test)")

    monkeypatch.setattr(ws.urllib.request, "Request", _istek)
    return tutulan


class TestDigerAracYollari:
    """Aynı hata iki araçta daha vardı; ikisi de kullanıcı/model
    URL'si doğrudan verir (arama sonuçları Türkçe yol içerir)."""

    def test_adres_kontrol_kodlar(self, monkeypatch, dns_kapali):
        tutulan = _istek_tutan(monkeypatch)
        ws.adres_kontrol("https://ornek.com/şirket/iletişim")
        giden = tutulan.get("url")
        assert giden is not None, "istek kurulmadi"
        assert giden.isascii(), giden
        assert "%C5%9F" in giden, giden
        assert giden.endswith("/ileti%C5%9Fim"), giden

    def test_sayfa_gorselleri_kodlar(self, monkeypatch, dns_kapali):
        tutulan = _istek_tutan(monkeypatch)
        ws.sayfa_gorseller("https://ornek.com/ürün/çilek")
        giden = tutulan.get("url")
        assert giden is not None, "istek kurulmadi"
        assert giden.isascii(), giden

    def test_ascii_url_degismez(self, monkeypatch, dns_kapali):
        """Zaten temiz URL'e dokunulmaz (yan etki yok)."""
        tutulan = _istek_tutan(monkeypatch)
        ws.adres_kontrol("https://ornek.com/a/b?c=d")
        assert tutulan["url"] == "https://ornek.com/a/b?c=d", tutulan


class TestYardimciTekNoktada:
    def test_kodlama_idempotent(self):
        """İki kez çağırmak URL'yi bozmaz (çift kodlama dönmez)."""
        bir = ws._url_kodla(_KURUM_UL)
        iki = ws._url_kodla(bir)
        assert bir == iki, "%s != %s" % (bir, iki)
        assert "%25" not in iki, iki

    def test_yalnizca_bir_kodlama_yolu_var(self):
        """Satır içi kopya kalmadı: `_GUVENLI` tek yerde tanımlı.

        Kopyalar kalsaydı sonraki bakımda biri unutulur ve aynı hata
        üçüncü kez çıkar (2026-10-01'de iki kopya vardı).
        """
        import inspect

        kaynak = inspect.getsource(ws)
        adet = kaynak.count("_GUVENLI = ")
        assert adet == 1, "kodlama kopyasi var: %d adet" % adet

    def test_yardimci_dort_yolu_da_kapsiyor(self):
        """Dört çağrı yolu da `_url_kodla`'dan geçiyor."""
        import inspect

        kaynak = inspect.getsource(ws)
        assert kaynak.count("_url_kodla(") == 5, (
            "1 tanim + 4 cagri bekleniyordu, bulunan: %d"
            % kaynak.count("_url_kodla("))