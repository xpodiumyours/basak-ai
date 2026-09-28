"""araclar_sayfa.py — /araclar/<kategori>/<arac> sayfalarini uretir (Faz 3).

Kural:
- 163 arac sayfasi DOSYA olarak degil, katalogdan TURETILIR (tek kaynak:
  tools/freetools_katalog.py). Katalog degisince sitemap de degisir.
- Sayfa istemcide (ziyaretcinin tarayicisinda) calisir; girdi sunucuya
  gitmez (MIMARI ilke 5).
- JSON-LD (schema.org WebApplication + breadcrumb) arama motoru icin.
- freetools.org yalnizca ATIF baglantisi olarak gosterilir; kod kopyasi
  yok, ortaklik izlenimi yok.
"""

import html
import json
from urllib.parse import quote

from tools.freetools_katalog import ARACLAR, KATEGORI_ADI, adres as kat_adres

# Tarayicida kendi basimiza hesapladigimiz araclar (web/araclar.js ile ayni).
# Digerleri sayfada bilgi + derin baglanti olarak gosterilir; uydurma sonuc yok.
YEREL_ARACLAR = {
    "sha-hash-generator": {
        "baslik": "SHA Üretici",
        "girdiler": [("Metin", "text", ""),
                     ("Algoritma (sha256, sha1, sha384, sha512)",
                      "text", "sha256")],
        "ipucu": "SHA ailesi tarayicinin ic yapimidir; sonuc sunucuya "
                 "gitmeden uzerinizde hesaplanir.",
    },
    "base64-encode-decode": {
        "baslik": "Base64 Kodla / Çöz",
        "girdiler": [("Metin", "text", ""),
                     ("Kip (bos: kodla, decode: çöz)", "text", "")],
        "ipucu": "UTF-8 desteklidir; Türkçe karakterler bozulmaz.",
    },
    "base64-decoder": {
        "baslik": "Base64 Çözücü",
        "girdiler": [("Base64 metni", "text", "")],
        "ipucu": "Gecersiz Base64 girisinde hata verir, uydurmaz.",
    },
    "url-encode-decode": {
        "baslik": "URL Kodla / Çöz",
        "girdiler": [("Metin", "text", ""),
                     ("Kip (bos: kodla, decode: çöz)", "text", "")],
        "ipucu": "Adres satirlari ve sorgu degerleri icin kullanilir.",
    },
    "percentage-calculator": {
        "baslik": "Yüzde Hesaplayıcı",
        "girdiler": [("Birinci sayi", "text", ""),
                     ("Yüzde (veya ikinci sayi)", "text", "")],
        "ipucu": "a x b / 100 — ornek: 15 ve 200 → 30.",
    },
    "letter-counter": {
        "baslik": "Harf ve Karakter Sayacı",
        "girdiler": [("Metin", "textarea", "")],
        "ipucu": "Kelime, harf, rakam ve satir sayisini tek seferde verir.",
    },
    "reverse-text": {
        "baslik": "Metni Ters Çevirme",
        "girdiler": [("Metin", "textarea", "")],
        "ipucu": "Emoji ve Türkçe karakterler bozulmadan ters cevrilir.",
    },
    "binary-hex-converter": {
        "baslik": "İkili ⇄ Hex Çevirici",
        "girdiler": [("Sayi (0/1 ikilisi veya hex)", "text", "")],
        "ipucu": "0/1 ile basliyorsa ikiliden hex'e, digerlerinde hex'ten "
                 "ikiliye cevirir.",
    },
    "hexadecimal-to-decimal-converter": {
        "baslik": "Hex ⇄ Ondalık Çevirici",
        "girdiler": [("Hex sayi (ornek ff)", "text", "")],
        "ipucu": "Cikti ondaliktir; 255 icin 'ff' yazin.",
    },
    "case-converter": {
        "baslik": "Büyük / Küçük Harf Çevirici",
        "girdiler": [("Metin", "textarea", ""),
                     ("Kip (bos: hepsi, upper, lower, title)", "text", "")],
        "ipucu": "Kip bos birakilirsa uc bicim birden gosterilir.",
    },
    "text-binary": {
        "baslik": "Metin ⇄ İkili (Binary) Çevirici",
        "girdiler": [("Metin veya ikili (ornek 01000001)", "textarea", ""),
                     ("Kip (bos: kodla, decode: çöz)", "text", "")],
        "ipucu": "Türkçe karakterler UTF-8 ile 8 bit bloklara cevrilir.",
    },
    "text-ascii": {
        "baslik": "Metin ⇄ ASCII Kodu Çevirici",
        "girdiler": [("Metin veya kodlar (ornek 65 66)", "textarea", ""),
                     ("Kip (bos: kodla, decode: çöz)", "text", "")],
        "ipucu": "Bosluk ya da virgulle ayrilmis ondalik kodlari cozebilirsiniz.",
    },
    "remove-empty-lines": {
        "baslik": "Boş Satır Temizleyici",
        "girdiler": [("Metin", "textarea", "")],
        "ipucu": "Bos ve yalniz-bosluk satirlari atilir; dolu satirlar korunur.",
    },
    "line-break-remover": {
        "baslik": "Satır Birleştirici",
        "girdiler": [("Metin", "textarea", "")],
        "ipucu": "Satir sonlari tek bosluga indirilir; metin tek paragrafa doner.",
    },
}

# Slug son kelimeleri icin kisa Turkce cevir (basligi anlasilir yapar).
SON_EK = {
    "generator": "Üretici", "calculator": "Hesaplayıcı", "converter": "Çevirici",
    "checker": "Denetleyici", "counter": "Sayacı", "formatter": "Biçimlendirici",
    "remover": "Temizleyici", "extractor": "Çıkarıcı", "validator": "Doğrulayıcı",
    "splitter": "Bölücü", "replacer": "Değiştirici", "sorter": "Sıralayıcı",
    "finder": "Bulucu", "picker": "Seçici", "editor": "Düzenleyici",
    "minifier": "Küçültücü", "beautifier": "Güzelleştirici",
    "highlighter": "Vurgulayıcı", "checker": "Denetleyici",
}

_KISA = {"sha", "hex", "url", "base64", "json", "xml", "sql", "html", "css",
         "ip", "ipv4", "ipv6", "qr", "cron", "xss", "md5", "utc", "ssl",
         "http", "https", "png", "jpg", "csv", "jwt", "uuid"}


def baslik_uret(slug, kategori):
    """'sha-hash-generator' -> 'SHA Hash Üretici' gibi okunur baslik."""
    if slug in YEREL_ARACLAR:
        return YEREL_ARACLAR[slug]["baslik"]
    parca = [p for p in slug.split("-") if p]
    if not parca:
        return slug
    parca[-1] = SON_EK.get(parca[-1], parca[-1])
    return " ".join(p.upper() if p in _KISA else p.capitalize() for p in parca)


def aciklama_uret(slug, kategori):
    kadi = KATEGORI_ADI.get(kategori, kategori)
    ek = ("Tarayicinizda calisir; girdiniz cihazinizdan cikmaz."
          if slug in YEREL_ARACLAR else
          "Ayni isi Basak sohbetinde de yaptirabilirsiniz.")
    return ("%s — ücretsiz çevrimiçi araç (%s). %s "
            "Kayit gerekmez." % (baslik_uret(slug, kategori), kadi, ek))


def _esc(s):
    return html.escape(str(s), quote=True)


def _jsonld(kategori, slug, kok):
    ad = baslik_uret(slug, kategori)
    yol = "/araclar/%s/%s" % (kategori, slug)
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "WebApplication",
        "name": ad,
        "url": kok + yol,
        "description": aciklama_uret(slug, kategori),
        "inLanguage": "tr",
        "applicationCategory": "UtilitiesApplication",
        "operatingSystem": "Web",
        "browserRequirements": "JavaScript gerekir",
        "isAccessibleForFree": True,
        "offers": {"@type": "Offer", "price": "0",
                   "priceCurrency": "TRY"},
        "breadcrumb": {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Ana sayfa",
                 "item": kok + "/"},
                {"@type": "ListItem", "position": 2, "name": "Araçlar",
                 "item": kok + "/araclar"},
                {"@type": "ListItem", "position": 3, "name": ad,
                 "item": kok + yol},
            ],
        },
    }, ensure_ascii=False)


def sayfa_html(kategori, slug, kok=""):
    """Tek arac sayfasi; bilinmeyen arac icin None (404)."""
    if (kategori, slug) not in set(ARACLAR):
        return None
    yerel = YEREL_ARACLAR.get(slug)
    ad = baslik_uret(slug, kategori)
    aciklama = aciklama_uret(slug, kategori)
    freetools = kat_adres(kategori, slug)
    soru = quote("%s aracini kullan: %s" % (ad, freetools))

    if yerel:
        parcalar = []
        for i, (et, tur, dg) in enumerate(yerel["girdiler"]):
            parcalar.append('<label for="g%d">%s</label>' % (i, _esc(et)))
            if tur == "textarea":
                parcalar.append('<textarea id="g%d"%s></textarea>'
                                % (i, ' placeholder="%s"' % _esc(dg) if dg
                                   else ""))
            else:
                parcalar.append('<input id="g%d" type="text"%s '
                                'autocomplete="off">'
                                % (i, ' value="%s"' % _esc(dg) if dg else ""))
        girdiler = "".join(parcalar)
        form = ('<div id="formKutu">%s'
                '<button id="hesapla" type="button">Hesapla</button>'
                '<div id="sonuc" class="sonuc" aria-live="polite"></div>'
                '<p class="not">%s</p></div>'
                % (girdiler, _esc(yerel["ipucu"])))
        betik = ('<script>window.ARAC_SLUG=%s;</script>'
                 '<script src="/araclar.js?v=1"></script>'
                 % json.dumps(slug))
    else:
        form = ('<p>Bu aracin tarayici surumu hazirlanana kadar ayni isi '
                'Basak sohbetinde ucretsiz yaptirabilirsin; ayrica orijinal '
                'arac da baglantida.</p>')
        betik = ""

    benzer = "".join('<li><a href="/araclar/%s/%s">%s</a></li>'
                     % (k, s, _esc(baslik_uret(s, k)))
                     for k, s in doner_listesi(kategori, slug))

    return _SABLON.format(
        ad=_esc(ad), aciklama=_esc(aciklama),
        yol="/araclar/%s/%s" % (kategori, slug), kok=_esc(kok),
        kadi=_esc(KATEGORI_ADI.get(kategori, kategori)),
        jsonld=_jsonld(kategori, slug, kok), form=form, soru=_esc(soru),
        freetools=_esc(freetools), betik=betik, benzer=benzer)


def doner_listesi(kategori, atlanan, adet=8):
    """Ayni kategoriden baska araclar (sayfayi zenginlestirir)."""
    return [(k, s) for k, s in ARACLAR
            if k == kategori and s != atlanan][:adet]


def liste_html(kok=""):
    """Tum kategoriler + araclar listesi (/araclar)."""
    kisalt = {}
    for kat, slug in ARACLAR:
        kisalt.setdefault(kat, []).append(slug)
    bloklar = []
    for kat in sorted(kisalt):
        satirlar = "".join(
            '<li><a href="/araclar/%s/%s">%s</a></li>'
            % (kat, s, _esc(baslik_uret(s, kat)))
            for s in kisalt[kat])
        bloklar.append("<h2>%s</h2><ul>%s</ul>"
                       % (_esc(KATEGORI_ADI.get(kat, kat)), satirlar))
    return _LISTE_SABLON.format(toplam=len(ARACLAR),
                                bloklar="".join(bloklar), kok=_esc(kok))


_SABLON = """<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1,viewport-fit=cover">
<meta name="theme-color" content="#fbfbfc">
<title>{ad} — ücretsiz çevrimiçi araç</title>
<meta name="description" content="{aciklama}">
<link rel="canonical" href="{kok}{yol}">
<meta property="og:type" content="website">
<meta property="og:title" content="{ad} — ücretsiz çevrimiçi araç">
<meta property="og:description" content="{aciklama}">
<meta property="og:url" content="{kok}{yol}">
<meta property="og:locale" content="tr_TR">
<meta name="robots" content="index,follow">
<script type="application/ld+json">{jsonld}</script>
<link rel="stylesheet" href="/araclar.css?v=1">
</head>
<body><main>
<p class="crumb"><a href="/">Başak</a> › <a href="/araclar">Araçlar</a> › {kadi}</p>
<div class="card">
<h1>{ad}</h1>
<p>{aciklama}</p>
{form}
<h2>Denemek ister misiniz?</h2>
<p><a href="/?soru={soru}">Başak'a sorup sohbette de çalıştırın</a> —
kayıt gerekmez, günlük ücretsiz hakkınız vardır.</p>
<h2>Bu kategoriden diğer araçlar</h2>
<ul>{benzer}</ul>
<p class="not">Kaynak/atıf: benzer araç <a href="{freetools}"
rel="noopener noreferrer nofollow" target="_blank">freetools.org</a>
adresinde de bulunur. Bu sayfa bağımsız çalışır; ortaklık yoktur.</p>
<div class="reklam" id="reklamAlani" hidden>Reklam alanı — yalnız çerez onayınızdan sonra yüklenir.</div>
</div>
<footer>
<a href="/gizlilik.html">Gizlilik</a>
<a href="/cerez.html">Çerez politikası</a>
<a href="/sartlar.html">Kullanım şartları</a>
<a href="/sorumluluk.html">Sorumluluk reddi</a>
<a href="/destek.html">Destek ol</a>
</footer>
<div class="cerez" id="cerezBandi" hidden>
Bu sitede yalnız onayladığınız çerezler kullanılır. Reklam kodları
onay verilmeden yüklenmez.
<button id="cerezOnay" type="button">Onayla</button>
<button id="cerezRed" type="button">Yalnız zorunlu</button>
<a href="/cerez.html">Ayrıntı</a>
</div>
{betik}
</main></body>
</html>
"""

_LISTE_SABLON = """<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Ücretsiz çevrimiçi araçlar — Başak</title>
<meta name="description" content="{toplam} ücretsiz çevrimiçi araç: hesaplama, kodlama, metin ve dönüşüm araçları. Kayıt gerekmez.">
<link rel="canonical" href="{kok}/araclar">
<meta name="robots" content="index,follow">
<link rel="stylesheet" href="/araclar.css?v=1">
</head>
<body><main>
<p class="crumb"><a href="/">Başak</a> › Araçlar</p>
<div class="card">
<h1>Ücretsiz araçlar</h1>
<p>{toplam} aracın hepsi tarayıcınızda çalışır, kayıt gerekmez.
Dilerseniz sohbette de Başak'a yaptırabilirsiniz.</p>
{bloklar}
</div>
<footer><a href="/">Sohbete dön</a><a href="/gizlilik.html">Gizlilik</a>
<a href="/destek.html">Destek ol</a></footer>
</main></body>
</html>
"""
