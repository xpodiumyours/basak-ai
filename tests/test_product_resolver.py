import json

from tools import product_resolver as pr


class SahteWeb:
    def __init__(self, aramalar, sayfalar):
        self.aramalar = aramalar
        self.sayfalar = sayfalar

    def web_search(self, q, adet=10):
        for anahtar, sonuc in self.aramalar.items():
            if anahtar in q:
                return {"result": sonuc}
        return {"result": "Sonuc bulunamadi"}

    def urun_sayfasi_oku(self, url):
        veri = self.sayfalar.get(url)
        if veri is None:
            return {"error": "yok"}
        return {"result": json.dumps(veri, ensure_ascii=False)}


def blok(baslik, url, ozet):
    return "%s\n%s\n%s" % (baslik, url, ozet)


def test_gtin_check_digit():
    assert pr.gtin_gecerli("8680508918124")
    assert not pr.gtin_gecerli("8680508918125")
    assert not pr.gtin_gecerli("ABC")


def test_hardcode_olmayan_marka_resmi_domain_ve_sku_ile_cozulur():
    kart = {
        "marka": "Örnek Marka", "kod": "OM-42", "ad": "Fatura adi",
        "varyantlar": [{"barkod": "", "renk": "Siyah", "beden": "M"}],
    }
    url = "https://ornekmarka.com/urun/om-42"
    ws = SahteWeb(
        {
            "OM-42": blok("Örnek Marka OM-42", url,
                           "Örnek Marka üretici ürün sayfası"),
            "üretici resmi site": blok("Örnek Marka", url,
                                        "Örnek Marka üretim"),
        },
        {
            url: {
                "metin": "Örnek Marka kendi markamızdır; fabrikamızda "
                         "üretiyoruz. OM-42 Siyah M",
                "urunler": [{
                    "name": "Örnek Marka Siyah Ürün",
                    "brand": "Örnek Marka", "sku": "OM-42", "mpn": "",
                    "gtin": [], "color": "Siyah", "size": "M"}],
                "gorseller": ["https://ornekmarka.com/i/om42.jpg"],
            }
        })
    firmalar = pr.firma_bul(kart, ws=ws)
    assert firmalar
    sonuc = pr.urun_bul(kart, firmalar, ws=ws)
    assert sonuc["resmi_dogrulandi"] is True
    assert sonuc["guven"] == "yuksek"
    assert sonuc["sku"] == "OM-42"
    assert sonuc["urun_adi"] == "Örnek Marka Siyah Ürün"


def test_pazaryeri_resmi_kaynak_sayilmaz():
    kart = {"marka": "Örnek", "kod": "X1", "varyantlar": []}
    url = "https://www.trendyol.com/ornek/x1-p-1"
    ws = SahteWeb(
        {"X1": blok("Örnek X1", url, "ürün")},
        {url: {"metin": "Örnek X1", "urunler": [{"name": "X1",
          "brand": "Örnek", "sku": "X1", "gtin": []}], "gorseller": []}})
    sonuc = pr.urun_bul(kart, [], ws=ws)
    assert "error" in sonuc


def test_kanit_yoksa_uydurma_yok():
    kart = {"marka": "Belirsiz", "kod": "ZZ99", "varyantlar": []}
    url = "https://magaza.example/urun/baska"
    ws = SahteWeb(
        {"ZZ99": blok("Baska urun", url, "alakasiz")},
        {url: {"metin": "tamamen baska urun", "urunler": [],
               "gorseller": []}})
    sonuc = pr.urun_bul(kart, [], ws=ws)
    assert "error" in sonuc
    assert "doğrulanamadı" in sonuc["error"]


def test_reseller_domain_marka_adi_tasisa_da_resmi_sayilmaz():
    kart = {
        "marka": "Örnek Marka", "kod": "OM-42", "kategori": "İç Giyim",
        "varyantlar": []
    }
    url = "https://ornekmarkaonline.com/urun/om-42"
    ws = SahteWeb(
        {"OM-42": blok("Örnek Marka OM-42", url,
                        "Örnek Marka ürün satışı üretici kalitesi")},
        {url: {
            "metin": "Örnek Marka OM-42 üretici kalitesi hızlı kargo",
            "urunler": [{"name": "OM-42", "brand": "Örnek Marka",
                         "sku": "OM-42", "gtin": []}],
            "gorseller": []
        }})
    sonuc = pr.urun_bul(kart, [], ws=ws)
    assert sonuc["resmi_dogrulandi"] is False
    assert sonuc["dogrulama_seviyesi"] == "urun_kanitli"


def test_guclu_uretici_beyani_artik_genel_uretim_kelimesi_degil():
    tur, kanit = pr._kaynak_sinifi(
        "magaza.example", "Örnek Marka üretici kalitesi ürün", "Örnek Marka")
    assert tur == "ticari_kaynak"
    tur2, kanit2 = pr._kaynak_sinifi(
        "firma.example",
        "Örnek Marka kendi markamız; fabrikamızda üretim yapıyoruz",
        "Örnek Marka")
    assert tur2 == "uretici_adayi"
    assert "guclu_uretim_beyani" in kanit2


def test_sektor_baglami_firma_adayini_yukseltir():
    kimlik = pr.kart_kimligi({
        "marka": "Berrak", "kod": "BR-7", "kategori": "İç Giyim",
        "ad": "Kadın atlet", "varyantlar": []
    })
    a = {"url": "https://tekstil.example/urun",
         "baslik": "Berrak İç Giyim", "ozet": "Kadın atlet üretim tesisi"}
    b = {"url": "https://gida.example/urun",
         "baslik": "Berrak Gıda", "ozet": "makarna ve gıda"}
    sa, _ = pr._firma_ilk_skor(a, kimlik)
    sb, _ = pr._firma_ilk_skor(b, kimlik)
    assert sa > sb


def test_uretici_sitesi_schema_sku_vermezse_tam_sku_metin_kaniti_yeter():
    kimlik = pr.kart_kimligi({
        "marka": "Tutku", "kod": "TER0117", "kategori": "İç Giyim",
        "ad": "Tutku Erkek Penye Düz Boxer", "varyantlar": []
    })
    veri = {
        "metin": "TER0117 Tutku Erkek Penye Düz Boxer S M L XL",
        "urunler": [{
            "name": "TER0117 Tutku Erkek Penye Düz Boxer",
            "brand": "", "sku": "", "mpn": "", "gtin": []
        }],
        "gorseller": ["https://uretici.example/i/ter0117.webp"]
    }
    firma = {"kaynak_turu": "uretici_adayi",
             "kanitlar": ["guclu_uretim_beyani"]}
    skor, kimlik_kaniti, resmi, kanit = pr._sayfa_skor(
        kimlik, "https://uretici.example/urun/ter0117", veri, firma)
    assert kimlik_kaniti is True
    assert resmi is True
    assert "sku_sayfa_tam" in kanit


def test_kisa_sku_substring_yanlis_eslesmez():
    assert pr._kod_metin_de("X1", "MODEL X10 başka ürün") is False
    assert pr._kod_metin_de("X1", "MODEL X1 ürün") is True


def test_sitemap_adayi_ddg_indeksinden_once_kullanilir():
    kart = {
        "marka": "Örnek Marka", "kod": "OM-42", "kategori": "İç Giyim",
        "varyantlar": []
    }
    url = "https://uretici.example/urun/om-42"
    class SitemapWeb(SahteWeb):
        def site_haritasi_ara(self, host, terim, adet=4):
            return {"result": json.dumps([url]) if terim == "OM-42" else "[]"}
    ws = SitemapWeb(
        {}, {url: {
            "metin": "Örnek Marka OM-42 kendi markamız fabrikamızda üretiyoruz",
            "urunler": [{"name": "OM-42 Ürün", "brand": "Örnek Marka",
                         "sku": "", "gtin": []}],
            "gorseller": ["https://uretici.example/i/om42.jpg"]}})
    firma = [{"host": "uretici.example", "kaynak_turu": "uretici_adayi",
              "kanitlar": ["guclu_uretim_beyani"]}]
    sonuc = pr.urun_bul(kart, firma, ws=ws)
    assert sonuc["resmi_dogrulandi"] is True
    assert sonuc["kaynak"] == url


def test_varyant_kaniti_urun_kimliginden_ayri_tasinir():
    kimlik = pr.kart_kimligi({
        "marka": "Marka", "kod": "A-1", "kategori": "Tekstil",
        "varyantlar": [{"renk": "Siyah", "beden": "M", "barkod": ""}]
    })
    veri = {
        "metin": "A-1 Marka Renk: Siyah Beden: M",
        "urunler": [{"name": "A-1", "brand": "Marka", "sku": "A-1",
                     "color": "", "size": "", "image": ""}]
    }
    v = pr._varyant_kaniti(kimlik, veri)
    assert v["durum"] == "uyumlu"
    assert v["renk_eslesen"] == ["Siyah"]
    assert v["beden_eslesen"] == ["M"]


def test_varyant_schema_gorseli_once_gelir():
    kimlik = pr.kart_kimligi({
        "marka": "Marka", "kod": "A-1",
        "varyantlar": [{"renk": "Siyah", "beden": "M", "barkod": ""}]
    })
    veri = {
        "metin": "A-1 Marka Siyah M",
        "urunler": [
            {"name": "A-1 Siyah M", "brand": "Marka", "sku": "A-1",
             "color": "Siyah", "size": "M",
             "image": "https://firma.example/siyah-m.jpg"},
            {"name": "A-1 Beyaz L", "brand": "Marka", "sku": "A-1",
             "color": "Beyaz", "size": "L",
             "image": "https://firma.example/beyaz-l.jpg"},
        ]
    }
    v = pr._varyant_kaniti(kimlik, veri)
    assert v["durum"] == "uyumlu"
    assert v["varyant_gorseller"] == [
        "https://firma.example/siyah-m.jpg"]


def test_schema_organization_ayni_host_resmi_marka_kaniti():
    kurumlar = [{
        "type": "Organization",
        "name": "Kaktüs Moda Giyim San. ve Tic. Ltd. Şti.",
        "url": "https://www.kaktusmoda.com/tr/",
        "sameAs": []
    }]
    tur, kanit = pr._kaynak_sinifi(
        "kaktusmoda.com",
        "KAKTÜS MODA stok kodu 23Y108-001-01",
        "Kaktüs Moda", kurumlar)
    assert tur == "resmi_marka_adayi"
    assert "schema_kurum_marka" in kanit


def test_fatura_kodu_schema_yoksa_sku_diye_uydurulmaz():
    kart = {
        "marka": "Tutku", "kod": "TER0117",
        "varyantlar": []
    }
    url = "https://uretici.example/urun/ter0117"
    ws = SahteWeb(
        {"TER0117": blok("TER0117 Tutku Boxer", url, "Tutku")},
        {url: {
            "metin": "Tutku TER0117 kendi markamız fabrikamızda üretiyoruz",
            "kurumlar": [],
            "urunler": [{"name": "TER0117 Tutku Boxer", "brand": "Tutku",
                         "sku": "", "mpn": "", "gtin": []}],
            "gorseller": []
        }})
    firma = [{"host": "uretici.example", "kaynak_turu": "uretici_adayi",
              "kanitlar": ["guclu_uretim_beyani"]}]
    sonuc = pr.urun_bul(kart, firma, ws=ws)
    assert sonuc["resmi_dogrulandi"] is True
    assert sonuc["fatura_kodu"] == "TER0117"
    assert sonuc["sku"] == ""
    assert sonuc["dogrulanmis_kod"] == "TER0117"
    assert sonuc["kod_turu"] == "uretici_sayfa_kodu"
