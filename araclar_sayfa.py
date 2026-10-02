"""araclar_sayfa.py — /araclar/<kategori>/<arac> sayfalarini uretir (Faz 3).

Kural:
- 162 arac sayfasi DOSYA olarak degil, katalogdan TURETILIR (tek kaynak:
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

import gelir
from tools.freetools_katalog import ARACLAR, KATEGORI_ADI, adres as kat_adres

# Kategori -> ((gorunen metin, adres), ...) ortaklik onerileri.
# BOS baslar: ilk anlasma Casper onayiyla buraya yazilir; o zamana kadar
# sayfalarda "Ilgili urunler" bolumu hic cikmaz.
ORTAKLIK_ONERILERI = {}

# Tarayicida kendi basimiza hesapladigimiz araclar (web/araclar.js ile ayni).
# Digerleri sayfada bilgi + derin baglanti olarak gosterilir; uydurma sonuc yok.
YEREL_ARACLAR = {
    "sha-hash-generator": {
        "baslik": "SHA Üretici",
        "girdiler": [("Metin", "text", ""),
                     ("Algoritma (sha256, sha1, sha384, sha512)",
                      "text", "sha256")],
        "ipucu": "SHA ailesi tarayıcının iç yapısıdır; sonuç sunucuya "
                 "gitmeden üzerinizde hesaplanır.",
    },
    "base64-encode-decode": {
        "baslik": "Base64 Kodla / Çöz",
        "girdiler": [("Metin", "text", ""),
                     ("Kip (boş: kodla, decode: çöz)", "text", "")],
        "ipucu": "UTF-8 desteklidir; Türkçe karakterler bozulmaz.",
    },
    "base64-decoder": {
        "baslik": "Base64 Çözücü",
        "girdiler": [("Base64 metni", "text", "")],
        "ipucu": "Geçersiz Base64 girişinde hata verir, uydurmaz.",
    },
    "url-encode-decode": {
        "baslik": "URL Kodla / Çöz",
        "girdiler": [("Metin", "text", ""),
                     ("Kip (boş: kodla, decode: çöz)", "text", "")],
        "ipucu": "Adres satırları ve sorgu değerleri için kullanılır.",
    },
    "percentage-calculator": {
        "baslik": "Yüzde Hesaplayıcı",
        "girdiler": [("Birinci sayı", "text", ""),
                     ("Yüzde (veya ikinci sayı)", "text", "")],
        "ipucu": "a x b / 100 — örnek: 15 ve 200 → 30.",
    },
    "letter-counter": {
        "baslik": "Harf ve Karakter Sayacı",
        "girdiler": [("Metin", "textarea", "")],
        "ipucu": "Kelime, harf, rakam ve satır sayısını tek seferde verir.",
    },
    "reverse-text": {
        "baslik": "Metni Ters Çevirme",
        "girdiler": [("Metin", "textarea", "")],
        "ipucu": "Emoji ve Türkçe karakterler bozulmadan ters çevrilir.",
    },
    "binary-hex-converter": {
        "baslik": "İkili ⇄ Hex Çevirici",
        "girdiler": [("Sayı (0/1 ikilisi veya hex)", "text", "")],
        "ipucu": "0/1 ile başlıyorsa ikiliden hex'e, diğerlerinde hex'ten "
                 "ikiliye çevirir.",
    },
    "hexadecimal-to-decimal-converter": {
        "baslik": "Hex ⇄ Ondalık Çevirici",
        "girdiler": [("Hex sayı (örnek ff)", "text", "")],
        "ipucu": "Çıktı ondalıktır; 255 için 'ff' yazın.",
    },
    "case-converter": {
        "baslik": "Büyük / Küçük Harf Çevirici",
        "girdiler": [("Metin", "textarea", ""),
                     ("Kip (boş: hepsi, upper, lower, title)", "text", "")],
        "ipucu": "Kip boş bırakılırsa üç biçim birden gösterilir.",
    },
    "text-binary": {
        "baslik": "Metin ⇄ İkili (Binary) Çevirici",
        "girdiler": [("Metin veya ikili (örnek 01000001)", "textarea", ""),
                     ("Kip (boş: kodla, decode: çöz)", "text", "")],
        "ipucu": "Türkçe karakterler UTF-8 ile 8 bit bloklara çevrilir.",
    },
    "text-ascii": {
        "baslik": "Metin ⇄ ASCII Kodu Çevirici",
        "girdiler": [("Metin veya kodlar (örnek 65 66)", "textarea", ""),
                     ("Kip (boş: kodla, decode: çöz)", "text", "")],
        "ipucu": "Boşluk ya da virgülle ayrılmış ondalık kodları "
                 "çözebilirsiniz.",
    },
    "remove-empty-lines": {
        "baslik": "Boş Satır Temizleyici",
        "girdiler": [("Metin", "textarea", "")],
        "ipucu": "Boş ve yalnız-boşluk satırları atılır; dolu satırlar korunur.",
    },
    "line-break-remover": {
        "baslik": "Satır Birleştirici",
        "girdiler": [("Metin", "textarea", "")],
        "ipucu": "Satır sonları tek boşluğa indirilir; metin tek paragrafa döner.",
    },
    "character-remover": {
        "baslik": "Karakter Silici",
        "girdiler": [("Metin", "textarea", ""),
                     ("Silinecek karakterler (boş: noktalama sil)", "text", "")],
        "ipucu": "İkinci alan boş bırakılırsa noktalama işaretleri silinir; "
                 "doluysa yalnız o karakterler silinir.",
    },
    "character-replacer": {
        "baslik": "Karakter Değiştirici",
        "girdiler": [("Metin", "textarea", ""),
                     ("Eski > yeni (örnek a>e; birden fazlı için | ile ayır)", "text", "")],
        "ipucu": "Örnek: a>e yazar; birden fazlaysa a>e|b>f biçiminde ayır.",
    },
    "tabs-to-space": {
        "baslik": "Sekme Boşluk Çevirici",
        "girdiler": [("Metin", "textarea", ""),
                     ("Sekme başına boşluk (boş: 4)", "text", "")],
        "ipucu": "Her sekme karakteri seçilen sayıda boşluğa döner; boş "
                 "bırakılırsa 4 kullanılır.",
    },
    "text-splitter": {
        "baslik": "Metin Bölücü",
        "girdiler": [("Metin", "textarea", ""),
                     ("Ayraç (boş: satır, 'kelime': kelime, 'cümle': cümle)", "text", "")],
        "ipucu": "Ayraç boş bırakılırsa satırlara, 'kelime' yazılırsa "
                 "kelimelere, 'cümle' yazılırsa cümlelere böler ve numaralar.",
    },
    "space-remover": {
        "baslik": "Fazla Boşluk Temizleyici",
        "girdiler": [("Metin", "textarea", "")],
        "ipucu": "Satır başı/sonu boşlukları silinir; kelime arası çoklu "
                 "boşluklar teke indirilir.",
    },
    "comma-inserter": {
        "baslik": "Virgül Ekleyici",
        "girdiler": [("Liste (satır veya boşlukla ayrılmış)", "textarea", ""),
                     ("Ayraç (boş: virgül)", "text", "")],
        "ipucu": "Satırları veya boşlukla ayrılmış öğeleri tek satırda "
                 "virgülle birleştirir.",
    },
    "json-formatter": {
        "baslik": "JSON Biçimlendirici",
        "girdiler": [("JSON metni", "textarea", ""),
                     ("Girinti (boş: 2)", "text", "")],
        "ipucu": "Geçersiz JSON'da hata verir, uydurmaz; girinti 0-8 arası.",
    },
    "html-entities": {
        "baslik": "HTML Entity Kodlayıcı",
        "girdiler": [("Metin", "textarea", ""),
                     ("Kip (boş: kodla, decode: çöz)", "text", "")],
        "ipucu": "& < > \" ' karakterlerini HTML entity'ye çevirir; decode "
                 "ile geri çözer.",
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
    "highlighter": "Vurgulayıcı",
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
    ek = ("Tarayıcınızda çalışır; girdiniz cihazınızdan çıkmaz."
          if slug in YEREL_ARACLAR else
          "Aynı işi Başak sohbetinde de yaptırabilirsiniz.")
    return ("%s — ücretsiz çevrimiçi araç (%s). %s "
            "Kayıt gerekmez." % (baslik_uret(slug, kategori), kadi, ek))


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
    soru = quote("%s aracını kullan: %s" % (ad, freetools))

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
        form = ('<p>Bu aracın tarayıcı sürümü hazırlanana kadar aynı işi '
                'Başak sohbetinde ücretsiz yaptırabilirsin; ayrıca orijinal '
                'araç da bağlantıda.</p>')
        betik = ""

    benzer = "".join('<li><a href="/araclar/%s/%s">%s</a></li>'
                     % (k, s, _esc(baslik_uret(s, k)))
                     for k, s in doner_listesi(kategori, slug))

    # Ortaklik onerisi: yalniz ilgili kategoride tanimliysa gosterilir.
    # Simdilik liste bos — ilk ortaklik anlasmasinda Casper onayiyla dolar.
    # Bosken sayfada hicbir iz birakmaz (reklam gibi gosterme yasagi).
    ortaklik = ""
    oneriler = ORTAKLIK_ONERILERI.get(kategori, ())
    if oneriler:
        satirlar = "".join("<li>%s</li>" % gelir.baglanti(m, a)
                           for m, a in oneriler)
        ortaklik = ('<h2>İlgili ürünler</h2><ul class="ortaklik">%s</ul>'
                    % satirlar)

    return _SABLON.format(
        ad=_esc(ad), aciklama=_esc(aciklama),
        yol="/araclar/%s/%s" % (kategori, slug), kok=_esc(kok),
        kadi=_esc(KATEGORI_ADI.get(kategori, kategori)),
        jsonld=_jsonld(kategori, slug, kok), form=form, soru=_esc(soru),
        freetools=_esc(freetools), betik=betik, benzer=benzer,
        ortaklik=ortaklik)


def doner_listesi(kategori, atlanan, adet=8):
    """Ayni kategoriden baska araclar (sayfayi zenginlestirir)."""
    return [(k, s) for k, s in ARACLAR
            if k == kategori and s != atlanan][:adet]


def tarayici_kapsami():
    """(toplam arac, tarayicida hesaplayan arac) — liste sayfasi bunu soyler.

    Tarayicida hesaplayan = YEREL_ARACLAR (web/araclar.js ile birebir eslesir;
    bkz. tests/test_faz3_arac_sayfalari.py). Kalan araclar bu sayida SAYILMAZ:
    "tarayicida calisir" iddiasi yalniz gercekten hesaplayan araclar icin
    kullanilir (Faz 0 durustluk kurali, 2026-10-02).
    """
    hesaplayan = sum(1 for _kat, s in ARACLAR if s in YEREL_ARACLAR)
    return len(ARACLAR), hesaplayan


def kategori_kapsami():
    """kategori -> (toplam, tarayicida hesaplayan) — baslik etiketi icin."""
    sayim = {}
    for kat, slug in ARACLAR:
        toplam, tarayici = sayim.get(kat, (0, 0))
        sayim[kat] = (toplam + 1, tarayici + (1 if slug in YEREL_ARACLAR else 0))
    return sayim


def liste_html(kok=""):
    """Tum kategoriler + araclar listesi (/araclar)."""
    kisalt = {}
    for kat, slug in ARACLAR:
        kisalt.setdefault(kat, []).append(slug)
    kapsam = kategori_kapsami()
    bloklar = []
    for kat in sorted(kisalt):
        satirlar = "".join(
            '<li><a href="/araclar/%s/%s">%s</a></li>'
            % (kat, s, _esc(baslik_uret(s, kat)))
            for s in kisalt[kat])
        toplam_kat, tarayici_kat = kapsam[kat]
        bloklar.append(
            '<h2>%s <small>(%d araç · tarayıcıda %d)</small></h2><ul>%s</ul>'
            % (_esc(KATEGORI_ADI.get(kat, kat)), toplam_kat, tarayici_kat,
               satirlar))
    toplam, hesaplayan = tarayici_kapsami()
    kapsam_yazi = (
        "Bu listede %d ücretsiz araç var. Bunlardan %d tanesi doğrudan "
        "tarayıcınızda hesaplar — girdiniz cihazınızdan çıkmaz. "
        "Kalan araçlar için işi <a href=\"/\">Başak'a sorabilirsiniz</a> "
        "ya da aracın sayfasındaki orijinal bağlantıyı kullanabilirsiniz. "
        "Kayıt gerekmez." % (toplam, hesaplayan))
    return _LISTE_SABLON.format(toplam=toplam, kapsam=kapsam_yazi,
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
<meta name="reklam-yerlesimi" content="">
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
{ortaklik}
<div class="reklam" id="reklamAlani" hidden>Reklam alanı — yalnız çerez onayınızdan sonra yüklenir.</div>
</div>
<footer>
<a href="/gizlilik.html">Gizlilik</a>
<a href="/cerez.html">Çerez politikası</a>
<a href="/sartlar.html">Kullanım şartları</a>
<a href="/sorumluluk.html">Sorumluluk reddi</a>
<a href="/destek.html">Destek ol</a>
<a href="/rehber">Rehberler</a>
</footer>
<div class="cerez" id="cerezBandi" hidden>
Bu sitede yalnız onayladığınız çerezler kullanılır. Reklam kodları
onay verilmeden yüklenmez.
<button id="cerezOnay" type="button">Onayla</button>
<button id="cerezRed" type="button">Yalnız zorunlu</button>
<a href="/cerez.html">Ayrıntı</a>
</div>
{betik}
<script src="/olcum.js?v=1" defer></script>
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
<p>{kapsam} Adım adım anlatımlar için <a href="/rehber">rehberlere</a>
bakın.</p>
{bloklar}
</div>
<footer><a href="/">Sohbete dön</a><a href="/gizlilik.html">Gizlilik</a>
<a href="/destek.html">Destek ol</a><a href="/rehber">Rehberler</a></footer>
<script src="/olcum.js?v=1" defer></script>
</main></body>
</html>
"""
