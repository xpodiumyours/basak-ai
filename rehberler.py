"""rehberler.py — Turkce rehber sayfalari (/rehber/<slug>).

Kural:
- Yalniz gercek ise yarayan, kisa ve durust icerik; dolgu yok.
- Ic baglantilar katalogdan DOGRULANIR ([[slug]] isareti uydurma adres
  uretemez; bilinmeyen slug baglantiya cevrilmez).
- Harici kod yok; sayfa tarayicida hafif (araclar.css + olcum.js disi
  hicbir sey yuklemez).
"""

import html
import json
from urllib.parse import quote

from araclar_sayfa import baslik_uret
from tools.freetools_katalog import ARACLAR

REHBERLER = [
    {
        "slug": "base64-nedir-nasil-cozulur",
        "baslik": "Base64 Nedir, Nasıl Çözülür?",
        "aciklama": "Base64 nedir, ne işe yarar ve elimizdeki bir Base64 "
                    "metni nasıl çözülür? Tarayıcınızda çalışan ücretsiz "
                    "araçlarla hızlı çözüm.",
        "soru": "Base64 ile kodlanmış metni çöz",
        "bolumler": [
            ("Base64 nedir?", [
                "Base64, ikili veriyi (görsel, dosya, rastgele baytlar) "
                "yazı karakterlerine çeviren bir kodlama biçimidir. E-posta "
                "eklerinde, JSON içinde ikili veri taşımada ve veri "
                "adreslerinde sık kullanılır.",
                "En kritik nokta: <strong>Base64 şifreleme değildir.</strong> "
                "Kodlanmış bir metni isteyen herkes kolayca geri çözebilir. "
                "Bu yüzden parola veya gizli anahtar saklamak için kullanılmaz.",
            ]),
            ("Nasıl çözülür?", [
                "Yapıştır-çöz için [[base64-decoder]] aracını kullanın. "
                "Metni veya dosyayı Base64'e çevirmek için "
                "[[base64-encode-decode]] aracı yeterlidir.",
                "Bu araçlar tarayıcınızda çalışır; yapıştırdığınız metin "
                "sunucuya gönderilmez. Geçersiz bir metin verirseniz araç "
                "hata gösterir; uydurma sonuç üretmez.",
            ]),
            ("Nelere dikkat edilmeli?", [
                "Base64 ile gizlenmiş zararlı içerik mümkündür: tanımadığınız "
                "kaynaktan gelen çözümlerde dosyayı tanımıyorsanız indirmeyin.",
                "Uzun metinlerde satır sonları normaldir; araç bunları tolere "
                "eder.",
            ]),
        ],
        "ilgili": ["base64-decoder", "base64-encode-decode"],
    },
    {
        "slug": "hash-nedir-sha-md5-farki",
        "baslik": "Hash Nedir? SHA ile MD5 Arasındaki Fark",
        "aciklama": "Hash (özet) fonksiyonları ne işe yarar; MD5 neden "
                    "artık güvenilmez, SHA-256 nerede kullanılır? "
                    "Tarayıcıda ücretsiz hash üretin.",
        "soru": "sha256 özeti üret",
        "bolumler": [
            ("Hash (özet) nedir?", [
                "Hash fonksiyonu bir veriyi (metin, dosya) sabit uzunlukta "
                "bir parmak izine dönüştürür. Aynı girdi her zaman aynı "
                "çıktıyı üretir; çıktıdan girdiye dönüş yoktur.",
                "Dosya bütünlüğü kontrolü ve veri karşılaştırma gibi işlerde "
                "kullanılır: indirdiğiniz dosyanın özeti, sitede yazanla "
                "aynı mı diye bakabilirsiniz.",
            ]),
            ("SHA ve MD5 farkı", [
                "MD5 eski bir algoritmadır ve güvenlik için <strong>artık "
                "kullanılmaz</strong> (farklı iki veri aynı özete "
                "düşürülebiliyor). Yalnız eski sistemlerle uyumluluk "
                "kontrolünde anlamı vardır.",
                "Güncel standart SHA-256'dır; SHA-384/512 daha geniş güvenlik "
                "isteyen işler içindir. Üretmek için [[sha-hash-generator]] "
                "aracını kullanın.",
            ]),
            ("Parola saklarken", [
                "Parolaları düz hash'lemek de yetersizdir; her kullanıcı için "
                "rastgele \"tuz\" (salt) ve yavaşlatılmış algoritmalar "
                "(örn. bcrypt/argon2) gerekir. Bu işi kendiniz yazmak yerine "
                "kullandığınız çerçevenin sunduğu parola fonksiyonunu seçin.",
            ]),
        ],
        "ilgili": ["sha-hash-generator"],
    },
    {
        "slug": "json-nasil-bicimlendirilir",
        "baslik": "JSON Nasıl Biçimlendirilir ve Hataları Bulunur?",
        "aciklama": "Tek satırlık JSON'u okunur hale getirin, sözdizimi "
                    "hatalarını bulun. Tarayıcıda çalışan ücretsiz JSON "
                    "biçimlendirici.",
        "soru": "şu JSON'u biçimlendir: {\"a\":1}",
        "bolumler": [
            ("JSON neden okunmaz görünür?", [
                "API yanıtları ve yapılandırma dosyaları çoğu zaman tek "
                "satır hâlinde gelir; iç içe yapılar gözle takip edilemez. "
                "Biçimlendirme (girintileme), yapıyı görünür kılar; veriyi "
                "değiştirmez.",
            ]),
            ("Adım adım biçimlendirme", [
                "Metni [[json-formatter]] aracına yapıştırın; girinti "
                "sayısını seçip düğmeye basın. Sonuç aynı veridir, yalnız "
                "yerleşimi düzgündür.",
                "JSON bozuksa araç hata verir ve sorunlu yeri işaret eder. "
                "Araç tarayıcınızda çalışır; veriniz sunucuya gitmez.",
            ]),
            ("Sık yapılan hatalar", [
                "Anahtarlar ve metinler <strong>çift tırnak</strong> ister; "
                "tek tırnak geçersizdir. Son elemandan sonra virgül "
                "bırakılamaz. JSON içine yorum satırı yazılamaz.",
                "Sayılar tırnaksız olmalıdır; \"5\" ile 5 farklı şeydir. "
                "Türkçe karakterler UTF-8 ile sorunsuz taşınır.",
            ]),
        ],
        "ilgili": ["json-formatter"],
    },
    {
        "slug": "metinden-istenmeyen-karakterleri-temizleme",
        "baslik": "Metinden İstenmeyen Karakterler Nasıl Temizlenir?",
        "aciklama": "Kopyala-yapıştır metinlerdeki fazla boşluk, sekme ve "
                    "istenmeyen karakterleri ücretsiz araçlarla saniyeler "
                    "içinde temizleyin.",
        "soru": "metindeki fazla boşlukları temizle",
        "bolumler": [
            ("Sorun nereden gelir?", [
                "PDF, Excel veya web sayfalarından kopyalanan metinler "
                "görünmez karakterler taşır: fazladan boşluklar, sekmeler, "
                "sabit olmayan boşluklar ve satır sonu kalıntıları. Bunlar "
                "kod içinde ve formlarda hataya yol açar.",
            ]),
            ("Hangi araç hangi işe yarar?", [
                "Belirli bir karakteri metnin tamamından silmek için "
                "[[character-remover]]; bir karakteri başkasıyla "
                "değiştirmek için [[character-replacer]] kullanılır.",
                "Ardışık boşlukları teke indirmek için [[space-remover]]; "
                "sekmeleri boşluğa çevirmek için [[tabs-to-space]] uygundur.",
            ]),
            ("Püf noktası", [
                "İşlemden önce metni \"düz metin olarak yapıştır\" "
                "seçeneğiyle yapıştırın; gizli biçimlendirme baştan düşer. "
                "Bu araçlar tarayıcınızda çalışır; metniniz sunucuya gitmez.",
            ]),
        ],
        "ilgili": ["character-remover", "character-replacer",
                   "space-remover", "tabs-to-space"],
    },
]


# ── yardımcılar ───────────────────────────────────────────────────────


def _arac_sozlugu():
    """slug -> (yol, baslik): yalniz katalogda gercekten var olanlar."""
    sozluk = {}
    for kat, slug in ARACLAR:
        try:
            baslik = baslik_uret(slug, kat)
        except Exception:
            baslik = slug
        sozluk[slug] = ("/araclar/%s/%s" % (kat, slug), baslik)
    return sozluk


_ARAC = _arac_sozlugu()


def _arac_baglantisi(slug):
    """[[slug]] icin dogrulanmis baglanti; bilinmeyeni duz metin yapar."""
    kayit = _ARAC.get(slug)
    if not kayit:
        return html.escape(slug, quote=True)
    yol, baslik = kayit
    return ('<a href="%s">%s</a>'
            % (html.escape(yol, quote=True),
               html.escape(baslik, quote=True)))


def _metin_dondur(metin):
    """Paragraf metnindeki [[slug]] isaretlerini dogrulanmis baglantilara
    cevirir; geri kalan yazi guvenilir kaynaktan geldigi icin korunur.
    """
    parcalar = []
    konum = 0
    while True:
        bas = metin.find("[[", konum)
        if bas < 0:
            parcalar.append(metin[konum:])
            break
        bit = metin.find("]]", bas + 2)
        if bit < 0:
            parcalar.append(metin[konum:])
            break
        parcalar.append(metin[konum:bas])
        parcalar.append(_arac_baglantisi(metin[bas + 2:bit].strip()))
        konum = bit + 2
    return "".join(parcalar)


def _bul(slug):
    for rehber in REHBERLER:
        if rehber.get("slug") == slug:
            return rehber
    return None


def _jsonld(rehber, kok):
    yol = kok + "/rehber/" + rehber["slug"]
    return json.dumps({
        "@context": "https://schema.org",
        "@type": "Article",
        "headline": rehber["baslik"],
        "description": rehber["aciklama"],
        "inLanguage": "tr",
        "url": yol,
        "breadcrumb": {
            "@type": "BreadcrumbList",
            "itemListElement": [
                {"@type": "ListItem", "position": 1, "name": "Ana sayfa",
                 "item": kok + "/"},
                {"@type": "ListItem", "position": 2, "name": "Rehberler",
                 "item": kok + "/rehber"},
                {"@type": "ListItem", "position": 3,
                 "name": rehber["baslik"], "item": yol},
            ],
        },
    }, ensure_ascii=False)


_SABLON = """<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>{baslik} — Başak Rehber</title>
<meta name="description" content="{aciklama}">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{kok}/rehber/{slug}">
<meta property="og:type" content="article">
<meta property="og:title" content="{baslik}">
<meta property="og:description" content="{aciklama}">
<meta property="og:url" content="{kok}/rehber/{slug}">
<meta property="og:locale" content="tr_TR">
<script type="application/ld+json">{jsonld}</script>
<link rel="stylesheet" href="/araclar.css?v=1">
</head>
<body><main>
<p class="crumb"><a href="/">Başak</a> › <a href="/rehber">Rehberler</a> › {baslik}</p>
<div class="card">
<h1>{baslik}</h1>
<p>{aciklama}</p>
{bolumler}
<h2>Başak'a da sorabilirsiniz</h2>
<p>Bu işi kayıtsız sohbette de yaptırabilirsiniz: <a href="/?soru={soru}">Başak'a sor</a>.</p>
{ilgili}
{diger}
</div>
<footer>
<a href="/rehber">Tüm rehberler</a>
<a href="/araclar">Araçlar</a>
<a href="/destek.html">Destek ol</a>
</footer>
<script src="/olcum.js?v=1" defer></script>
</main></body>
</html>
"""


def sayfa_html(slug, kok=""):
    """Tek rehber sayfasi; bilinmeyen slug icin None (404)."""
    rehber = _bul(slug)
    if not rehber:
        return None
    bolumler = "".join(
        "<h2>%s</h2>%s"
        % (html.escape(baslik, quote=True),
           "".join("<p>%s</p>" % _metin_dondur(p) for p in paragraflar))
        for baslik, paragraflar in rehber["bolumler"])
    ilgili = ""
    onerilen = [s for s in rehber.get("ilgili", []) if s in _ARAC]
    if onerilen:
        satirlar = "".join(
            "<li>%s</li>" % _arac_baglantisi(s) for s in onerilen)
        ilgili = "<h2>İlgili araçlar</h2><ul>%s</ul>" % satirlar
    diger = "".join(
        '<li><a href="/rehber/%s">%s</a></li>'
        % (html.escape(r["slug"], quote=True),
           html.escape(r["baslik"], quote=True))
        for r in REHBERLER if r["slug"] != slug)
    if diger:
        diger = "<h2>Diğer rehberler</h2><ul>%s</ul>" % diger
    return _SABLON.format(
        baslik=html.escape(rehber["baslik"], quote=True),
        aciklama=html.escape(rehber["aciklama"], quote=True),
        slug=html.escape(slug, quote=True),
        kok=html.escape(kok, quote=True),
        jsonld=_jsonld(rehber, kok),
        bolumler=bolumler,
        soru=quote(rehber["soru"]),
        ilgili=ilgili,
        diger=diger)


_LISTE_SABLON = """<!doctype html>
<html lang="tr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<title>Rehberler — Başak</title>
<meta name="description" content="Ücretsiz araçları adım adım anlatan kısa rehberler: Base64, hash, JSON ve metin temizleme. Kayıt gerekmez.">
<meta name="robots" content="index,follow">
<link rel="canonical" href="{kok}/rehber">
<link rel="stylesheet" href="/araclar.css?v=1">
</head>
<body><main>
<p class="crumb"><a href="/">Başak</a> › Rehberler</p>
<div class="card">
<h1>Rehberler</h1>
<p>Araçları doğru kullanmanın kısa yolları. Her rehber birkaç dakikada
okunur; anlatılan araçlar kayıt istemez ve tarayıcınızda çalışır.</p>
<ul>
{girdiler}
</ul>
</div>
<footer><a href="/">Sohbete dön</a><a href="/araclar">Araçlar</a>
<a href="/destek.html">Destek ol</a></footer>
<script src="/olcum.js?v=1" defer></script>
</main></body>
</html>
"""


def liste_html(kok=""):
    """Tum rehberlerin listesi (/rehber)."""
    girdiler = "".join(
        '<li><a href="/rehber/%s">%s</a> — %s</li>'
        % (html.escape(r["slug"], quote=True),
           html.escape(r["baslik"], quote=True),
           html.escape(r["aciklama"], quote=True))
        for r in REHBERLER)
    return _LISTE_SABLON.format(girdiler=girdiler,
                                kok=html.escape(kok, quote=True))
