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
                "metin": "Örnek Marka üretici OM-42 Siyah M",
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
