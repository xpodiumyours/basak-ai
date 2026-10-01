"""tests/test_sirket_karti_yapisal.py — Şirket kartı: yapısal veri önce.

Ölçülmüş kusur (2026-10-01, canlı): tutkuelit.com.tr iletişim sayfası
adresi, telefonu ve vergi numarasını schema.org Organization +
PostalAddress içinde veriyor; eski akış yalnız düz metne baktığı için
adres alanı boş dönüyordu (`eksik=["adres"]`). Ayrıca sayfa metni tek
satıra indirildiği için satır bazlı adres sezgisi gerçek çalışmada
neredeyse hiç tetiklenemiyordu.

Bu testler çevrimdışıdır: ağ çağrısı yapılmaz, HTML/JSON-LD gömülüdür.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools import katalog, web_search as ws

# Canlı ölçümden alınan gerçek JSON-LD (tutkuelit.com.tr, 2026-10-01).
TUTKU_JSONLD = """
<script type="application/ld+json">
{"@context":"https://schema.org","@type":"Organization",
 "name":"Tutku & Tutku Elit","legalName":"Tutku Elit İç Giyim Ltd. Şti.",
 "vatID":"4550047841","telephone":"+90-542-326-98-63",
 "email":"tutkuelit.tr@gmail.com",
 "address":{"@type":"PostalAddress",
            "streetAddress":"Musalla Bağları Mahallesi Sesigür Sokak No 30",
            "addressLocality":"Selçuklu","addressRegion":"Konya",
            "addressCountry":"TR"}}
</script>
"""

TUTKU_ADRES = ("Musalla Bağları Mahallesi Sesigür Sokak No 30, "
               "Selçuklu, Konya, TR")


class TestKurumGercekleri:
    def test_postaladdress_tek_satira_cevrilir(self):
        g = ws._kurum_gercekleri(TUTKU_JSONLD)
        assert len(g) == 1
        assert g[0]["adres_metni"] == TUTKU_ADRES
        assert g[0]["adres"]["sokak"] == (
            "Musalla Bağları Mahallesi Sesigür Sokak No 30")

    def test_alanlar_sayfadaki_gibi_kalir(self):
        g = ws._kurum_gercekleri(TUTKU_JSONLD)[0]
        assert g["vergi_no"] == "4550047841"
        assert g["telefonlar"] == ["+90-542-326-98-63"]
        assert g["epostalar"] == ["tutkuelit.tr@gmail.com"]
        assert g["resmi_ad"] == "Tutku Elit İç Giyim Ltd. Şti."

    def test_graph_icindeki_kurum_bulunur(self):
        ham = """<script type="application/ld+json">
        {"@context":"https://schema.org","@graph":[
          {"@type":"WebSite","name":"Site"},
          {"@type":"LocalBusiness","name":"Dükkan",
           "address":{"@type":"PostalAddress","streetAddress":"Atatürk Cad. 5",
                      "addressLocality":"Tuzla","addressRegion":"İstanbul"}}]}
        </script>"""
        g = ws._kurum_gercekleri(ham)
        assert g[0]["ad"] == "Dükkan"
        assert g[0]["adres_metni"] == "Atatürk Cad. 5, Tuzla, İstanbul"

    def test_ulke_nesne_olarak_gelirse_ad_alinir(self):
        ham = """<script type="application/ld+json">
        {"@type":"Organization","name":"X",
         "address":{"streetAddress":"A Cad. 1","addressCountry":
                    {"@type":"Country","name":"Türkiye"}}}
        </script>"""
        assert ws._kurum_gercekleri(ham)[0]["adres_metni"] == "A Cad. 1, Türkiye"

    def test_telefon_listesi_ve_tekrarlar(self):
        ham = """<script type="application/ld+json">
        {"@type":"Organization","name":"X",
         "telephone":["0850 111 22 33","0850 111 22 33"]}
        </script>"""
        assert ws._kurum_gercekleri(ham)[0]["telefonlar"] == ["0850 111 22 33"]

    def test_bos_dugum_gercek_sayilmaz(self):
        ham = """<script type="application/ld+json">
        {"@type":"Organization"}</script>"""
        assert ws._kurum_gercekleri(ham) == []

    def test_bozuk_jsonld_cokme_yerine_atlanir(self):
        ham = """<script type="application/ld+json">{bozuk json</script>
        <script type="application/ld+json">
        {"@type":"Organization","name":"Sağlam"}</script>"""
        assert [g["ad"] for g in ws._kurum_gercekleri(ham)] == ["Sağlam"]

    def test_urun_bloku_kurum_sayilmaz(self):
        ham = """<script type="application/ld+json">
        {"@type":"Product","name":"Boxer","brand":{"name":"Tutku"}}
        </script>"""
        assert ws._kurum_gercekleri(ham) == []


class _Yanit:
    headers = {"Content-Type": "text/html; charset=utf-8"}

    def __init__(self, ham):
        self._ham = ham

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False

    def geturl(self):
        return "https://tutkuelit.com.tr/iletisim"

    def read(self, n=-1):
        return self._ham.encode("utf-8")


class TestKurumSayfasiOku:
    """SSRF denetimi ayrı sınanır; burada ayrıştırma/biçim ölçülür."""

    @pytest.fixture(autouse=True)
    def _denetim_acik(self, monkeypatch):
        monkeypatch.setattr(ws, "_guvenli_adres", lambda url: None)

    def test_metin_satir_yapisini_korur(self):
        """Adres satırı tek dev satıra yapışırsa sezgi onu göremez."""
        ham = ("<html><body><div>Adres: Musalla Bağları Mahallesi "
               "Sesigür Sokak No 30</div><div>Selçuklu / Konya</div>"
               "</body></html>")
        r = ws.kurum_sayfasi_oku("https://ornek.example/iletisim",
                                 _acici=lambda *a, **k: _Yanit(ham))
        veri = json.loads(r["result"])
        satirlar = veri["metin"].splitlines()
        # Satır yapısı korunur (eski akışta tüm sayfa tek satıra iniyordu);
        # adres kendi satırında kalır ve sezgi onu görebilir.
        assert len(satirlar) > 1
        assert any("Musalla Bağları Mahallesi Sesigür Sokak No 30" in s
                   for s in satirlar)
        assert katalog._sirket_adres_meti(satirlar[0])

    def test_gercekler_ve_metin_birlikte_doner(self):
        r = ws.kurum_sayfasi_oku(
            "https://ornek.example/iletisim",
            _acici=lambda *a, **k: _Yanit(
                "<html><body>Tutku</body>" + TUTKU_JSONLD))
        veri = json.loads(r["result"])
        assert veri["gercekler"][0]["adres_metni"] == TUTKU_ADRES
        assert "Tutku" in veri["metin"]

    def test_ssrf_engelli_adres_aga_cikmaz(self, monkeypatch):
        def patlat(*a, **k):
            raise AssertionError("engelli adres için ağa çıkıldı")
        monkeypatch.setattr(ws.urllib.request, "build_opener", patlat)
        assert "error" in ws.kurum_sayfasi_oku("http://127.0.0.1/ic")

    def test_ssrf_korumasi_sayfa_oku_ile_ortak(self, monkeypatch):
        cagrildi = {"n": 0}

        def engel(url):
            cagrildi["n"] += 1
            return "Guvenlik engeli: test"

        monkeypatch.setattr(ws, "_guvenli_adres", engel)
        assert "error" in ws.kurum_sayfasi_oku("https://example.com/x")
        assert cagrildi["n"] == 1

    def test_http_hatasi_metin_dondurmez(self):
        def acici(*a, **k):
            raise ws.urllib.error.HTTPError(
                "https://ornek.example/", 404, "yok", {}, None)
        r = ws.kurum_sayfasi_oku("https://ornek.example/yok", _acici=acici)
        assert "error" in r and "result" not in r

    def test_savunma_tekrar_yazilmadi(self):
        import inspect
        kaynak = inspect.getsource(ws.kurum_sayfasi_oku)
        assert "_ham_sayfa_getir" in kaynak
        assert "getaddrinfo" not in kaynak


class TestSirketAlanlari:
    def test_yapisal_alanlar_metinden_once_gelir(self):
        gercekler = [{"telefonlar": ["+90-542-326-98-63"],
                      "epostalar": ["jsonld@ornek.com"],
                      "adres_metni": TUTKU_ADRES,
                      "resmi_ad": "Tutku Elit Ltd.",
                      "vergi_no": "4550047841"}]
        metin = "Telefon: 0542 326 98 63\nE-posta: metin@ornek.com\n"
        tel, eposta, adres, unvan, vergi = katalog._sirket_alanlari(
            metin, gercekler)
        assert tel == ["+90-542-326-98-63", "0542 326 98 63"]
        assert eposta == ["jsonld@ornek.com", "metin@ornek.com"]
        assert adres == [TUTKU_ADRES]
        assert unvan == "Tutku Elit Ltd."
        assert vergi == "4550047841"

    def test_ulkeli_vatid_rakama_indirilir(self):
        _, _, _, _, vergi = katalog._sirket_alanlari(
            "", [{"vergi_no": "TR4550047841"}])
        assert vergi == "4550047841"

    def test_on_hane_disindaki_vatid_kabul_edilmez(self):
        metin = "Vergi No: 1234567890"
        _, _, _, _, vergi = katalog._sirket_alanlari(
            metin, [{"vergi_no": "123"}])
        assert vergi == "1234567890"

    def test_adres_uc_satirla_sinirli(self):
        metin = "\n".join("Adres: Mah. %d. Sk. No:%d" % (i, i)
                          for i in range(1, 6))
        _, _, adres, _, _ = katalog._sirket_alanlari(metin, [])
        assert len(adres) == 3

    def test_baslik_satiri_adres_sayilmaz(self):
        """Canlı ölçüm: menü/başlık satırı "Adres" adres sanılıyordu."""
        metin = ("İletişim\nAdres\nAdres Bilgilerimiz\n"
                 "Musalla Bağları Mahallesi Sesigür Sokak No 30\n")
        _, _, adres, _, _ = katalog._sirket_alanlari(metin, [])
        assert adres == ["Musalla Bağları Mahallesi Sesigür Sokak No 30"]

    def test_rakamsiz_adres_satiri_kabul_edilmez(self):
        _, _, adres, _, _ = katalog._sirket_alanlari(
            "Adres: Moda Mahallesi Sahil Sokak\n", [])
        assert adres == []

    def test_ayni_adres_iki_kaynaktan_tek_satira_iner(self):
        """JSON-LD adresi ile sayfadaki görünür adres aynı yeri farklı
        yazımla veriyor; ikisi de listeye girmemeli."""
        gercekler = [{"adres_metni": TUTKU_ADRES}]
        metin = ("Musalla Bağları Mahallesi Sesigür Sokak No 30 Selçuklu/ "
                 "KONYA\n")
        _, _, adres, _, _ = katalog._sirket_alanlari(metin, gercekler)
        assert adres == [TUTKU_ADRES]

    def test_farkli_adresler_birlesmez(self):
        gercekler = [{"adres_metni": "Atatürk Cad. No:5, Tuzla, İstanbul"}]
        metin = "Depo: Organize Sanayi Bölgesi 7. Cad. No:15, Kocaeli\n"
        _, _, adres, _, _ = katalog._sirket_alanlari(metin, gercekler)
        assert len(adres) == 2

    def test_yapisal_yoksa_metin_yedegi_calisir(self):
        metin = ("Adres: Deneme Mah. 1. Sk. No:2\n"
                 "Tel: 0212 111 22 33\na@yeni.com\n")
        tel, eposta, adres, unvan, _ = katalog._sirket_alanlari(metin, [])
        assert tel == ["0212 111 22 33"]
        assert eposta == ["a@yeni.com"]
        assert adres and "Deneme Mah." in adres[0]
        assert unvan == ""


class TestSirketAraUctanUca:
    """Kusurun gerçek hali: adres yalnız JSON-LD'de. Çevrimdışı taklit."""

    def _kos(self, monkeypatch, gercekler, cagrilar):
        def kurum_sayfasi_oku(url):
            cagrilar.append(url)
            if url.endswith("/iletisim"):
                return {"result": json.dumps({
                    "url": url,
                    "metin": "İletişim\nBize ulaşın\nMüşteri hizmetleri",
                    "gercekler": gercekler,
                }, ensure_ascii=False)}
            return {"error": "yok"}
        monkeypatch.setattr(ws, "kurum_sayfasi_oku", kurum_sayfasi_oku)
        return json.loads(katalog.sirket_ara("Tutku")["result"])

    def test_adres_yapisal_veriden_gelir(self, monkeypatch):
        cagrilar = []
        veri = self._kos(
            monkeypatch, ws._kurum_gercekleri(TUTKU_JSONLD), cagrilar)
        assert veri["adresler"] == [TUTKU_ADRES]
        assert veri["unvan"] == "Tutku Elit İç Giyim Ltd. Şti."
        assert veri["vergi_no"] == "4550047841"
        assert "adres" not in veri["eksik"]
        assert len(cagrilar) == len(set(cagrilar))

    def test_skor_sifir_olsa_da_sayfa_okunmus_sayilir(self, monkeypatch):
        """Eski akışta anahtar kelime yoksa \"iletişim sayfası okunamadı\"
        deniyordu; sayfa gerçekten okunmuşken bu yanlıştı."""
        cagrilar = []
        veri = self._kos(monkeypatch, [{"adres_metni": TUTKU_ADRES}], cagrilar)
        assert veri["adresler"] == [TUTKU_ADRES]

    def test_hicbir_aday_okunamazsa_hata(self, monkeypatch):
        monkeypatch.setattr(ws, "kurum_sayfasi_oku",
                            lambda url: {"error": "yok"})
        assert "error" in katalog.sirket_ara("Tutku")

    def test_adres_yoksa_eksikte_kalir(self, monkeypatch):
        cagrilar = []
        veri = self._kos(monkeypatch, [], cagrilar)
        assert veri["adresler"] == []
        assert "adres" in veri["eksik"]
