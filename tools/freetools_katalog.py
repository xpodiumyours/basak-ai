"""tools/freetools_katalog.py — freetools.org arac katalogu (yerel kopya).

Kaynak: https://www.freetools.org/sitemap.xml (2026-09-28 anlik kopya).
Katalog YERELDIR: arama icin ag gerekmez, bozuk katalog aramayi
dusturmez. Yalniz arac ADI ve ADRESI tutulur; freetools.org kodu
kopyalanmaz (lisansi acik degil), yalnizca ad+adres uzerinden
baglanti kurulur.
"""

# (kategori, arac-slug) — sitemap'teki tum arac sayfalari
ARACLAR = (
    # math-tools
    ("math-tools", "rectangle-area-calculator"),
    ("math-tools", "prime-number-calculator"),
    ("math-tools", "qr-decomposition-calculator"),
    ("math-tools", "jacobian-calculator"),
    ("math-tools", "convolution-calculator"),
    ("math-tools", "orthogonal-projection-calculator"),
    ("math-tools", "inverse-modulo-calculator"),
    ("math-tools", "simpsons-rule-calculator"),
    ("math-tools", "fibonacci-sequence-calculator"),
    ("math-tools", "matrix-subtraction-calculator"),
    ("math-tools", "matrix-transpose-calculator"),
    # security-tools
    ("security-tools", "keyword-password-generator"),
    ("security-tools", "strong-password-generator"),
    ("security-tools", "sha-hash-generator"),
    ("security-tools", "ssl-certificate-format-converter"),
    ("security-tools", "ssl-certificate-decoder"),
    ("security-tools", "ssl-certificate-generator"),
    ("security-tools", "http-security-headers-analyzer"),
    ("security-tools", "open-graph-simulator"),
    # networking-tools
    ("networking-tools", "accessibility-checker"),
    ("networking-tools", "postcode-validator"),
    ("networking-tools", "bulk-url-checker"),
    ("networking-tools", "href-extractor"),
    ("networking-tools", "port-checker"),
    ("networking-tools", "http2-checker"),
    ("networking-tools", "http-requests-checker"),
    ("networking-tools", "traceroute-checker"),
    ("networking-tools", "ipv4-ipv6-converter"),
    ("networking-tools", "domain-ip-converter"),
    ("networking-tools", "domain-extractor"),
    ("networking-tools", "ip-search"),
    # image-tools
    ("image-tools", "hue-shift-generator"),
    ("image-tools", "image-splitter"),
    ("image-tools", "image-color-picker"),
    ("image-tools", "image-downloader"),
    # encode-tools
    ("encode-tools", "url-encode-decode"),
    ("encode-tools", "binary-hex-converter"),
    ("encode-tools", "base64-encode-decode"),
    ("encode-tools", "base64-decoder"),
    # data-tools
    ("data-tools", "country-name-generator"),
    ("data-tools", "temperature-checker"),
    ("data-tools", "binary-division-calculator"),
    ("data-tools", "roasoft-sample-size-calculator"),
    ("data-tools", "coefficient-calculator"),
    ("data-tools", "multi-dice-roller"),
    ("data-tools", "area-calculator"),
    ("data-tools", "percentage-calculator"),
    ("data-tools", "empty-row-remover"),
    ("data-tools", "number-list-generator"),
    ("data-tools", "number-sorter"),
    ("data-tools", "random-number-generator"),
    ("data-tools", "email-extractor"),
    ("data-tools", "url-metadata-extractor"),
    # conversion-tools
    ("conversion-tools", "radians-converter"),
    ("conversion-tools", "hexadecimal-to-decimal-converter"),
    ("conversion-tools", "engineering-unit-converter"),
    ("conversion-tools", "temperature-converter"),
    ("conversion-tools", "power-unit-converter"),
    ("conversion-tools", "weight-mass-converter"),
    ("conversion-tools", "electrical-unit-converter"),
    ("conversion-tools", "length-unit-converter"),
    # text-tools
    ("text-tools", "text-splitter"),
    ("text-tools", "space-remover"),
    ("text-tools", "remove-empty-lines"),
    ("text-tools", "reverse-text"),
    ("text-tools", "letter-counter"),
    ("text-tools", "character-remover"),
    ("text-tools", "character-replacer"),
    ("text-tools", "text-appender"),
    ("text-tools", "tabs-to-space"),
    ("text-tools", "word-randomizer"),
    ("text-tools", "random-sentence-generator"),
    ("text-tools", "comma-inserter"),
    ("text-tools", "line-break-remover"),
    ("text-tools", "text-repeater"),
    ("text-tools", "diff-checker"),
    ("text-tools", "ascii-art"),
    ("text-tools", "text-ascii"),
    ("text-tools", "text-binary"),
    ("text-tools", "case-converter"),
    ("text-tools", "text-pattern-finder"),
    # code-tools
    ("code-tools", "json-sorter"),
    ("code-tools", "unstringify-json-online"),
    ("code-tools", "stringify-json-online"),
    ("code-tools", "xss-checker"),
    ("code-tools", "nginx-validator"),
    ("code-tools", "python-syntax-validator"),
    ("code-tools", "code-syntax-highlighter"),
    ("code-tools", "html-formatter"),
    ("code-tools", "js-css-minify"),
    ("code-tools", "html-entities"),
    ("code-tools", "json-formatter"),
    ("code-tools", "js-css-beautify"),
    ("code-tools", "sql-formatter"),
    ("code-tools", "htaccess-file-generator"),
    ("code-tools", "html5-validator"),
    ("code-tools", "html-editor"),
    ("code-tools", "xml-schema-generator"),
    ("code-tools", "cron-generator"),
    ("code-tools", "random-picker"),
    ("code-tools", "random-team-generator"),
    # time-tools
    ("time-tools", "clock-with-nanoseconds"),
    ("time-tools", "online-stopwatch"),
    ("time-tools", "clock-with-milliseconds"),
    ("time-tools", "countdown-timer"),
    ("time-tools", "count-up-timer"),
    ("time-tools", "world-time-clock"),
    # seo-tools
    ("seo-tools", "open-graph-generator"),
    ("seo-tools", "google-ads-description-generator"),
    ("seo-tools", "google-ads-headline-generator"),
    ("seo-tools", "noindex-checker"),
    ("seo-tools", "seo-content-checker"),
    ("seo-tools", "google-search-preview"),
    ("seo-tools", "canonical-tag-checker"),
    ("seo-tools", "h1-tag-checker"),
    ("seo-tools", "title-tag-checker"),
    ("seo-tools", "sitemap-checker"),
    ("seo-tools", "favicon-checker"),
    ("seo-tools", "on-page-seo-checker"),
    ("seo-tools", "page-size-checker"),
    # ai-tools
    ("ai-tools", "faction-generator"),
    ("ai-tools", "artifact-generator"),
    ("ai-tools", "prophecy-generator"),
    ("ai-tools", "quest-generator"),
    ("ai-tools", "religion-maker"),
    ("ai-tools", "spell-generator"),
    ("ai-tools", "romantic-scenario-generator"),
    ("ai-tools", "superpower-generator"),
    ("ai-tools", "boss-generator"),
    ("ai-tools", "lore-generator"),
    ("ai-tools", "world-building-generator"),
    ("ai-tools", "planet-generator"),
    ("ai-tools", "country-maker"),
    ("ai-tools", "kingdom-generator"),
    ("ai-tools", "fantasy-currency-generator"),
    ("ai-tools", "character-outfit-generator"),
    ("ai-tools", "character-generator"),
    ("ai-tools", "youtube-description-generator"),
    ("ai-tools", "youtube-channel-name-generator"),
    ("ai-tools", "youtube-video-idea-generator"),
    ("ai-tools", "tv-show-generator"),
    ("ai-tools", "newsletter-generator"),
    ("ai-tools", "poem-generator"),
    ("ai-tools", "lyrics-generator"),
    ("ai-tools", "dialogue-enhancer"),
    ("ai-tools", "dialogue-generator"),
    ("ai-tools", "story-rewriter"),
    ("ai-tools", "continue-writing"),
    ("ai-tools", "story-plot"),
    ("ai-tools", "story-outline"),
    ("ai-tools", "chapter-generator"),
    ("ai-tools", "text-similarity"),
    ("ai-tools", "paragraph-writer"),
    ("ai-tools", "ai-story"),
    ("ai-tools", "faq-generator"),
    ("ai-tools", "book-title-generator"),
    ("ai-tools", "sentence-generator"),
    ("ai-tools", "ai-response-generator"),
    ("ai-tools", "tone-checker"),
    ("ai-tools", "story-summarizer"),
    ("ai-tools", "paragraph-summarizer"),
    ("ai-tools", "text-rephrase"),
)

KOK = "https://www.freetools.org"

KATEGORI_ADI = {
    "math-tools": "matematik hesaplayicilari",
    "security-tools": "sifre/hash/SSL guvenlik araclari",
    "networking-tools": "ag ve URL denetim araclari",
    "image-tools": "gorsel donusturme araclari",
    "encode-tools": "base64/url/hex kodlama araclari",
    "data-tools": "veri ve liste araclari",
    "conversion-tools": "birim donusum araclari",
    "text-tools": "metin isleme araclari",
    "code-tools": "kod bicimlendirme ve dogrulama araclari",
    "time-tools": "saat/kronometre araclari",
    "seo-tools": "SEO denetim araclari",
    "ai-tools": "uretici/olusturucu araclar",
}


def adres(kategori, slug):
    """Aracin tam adresi."""
    return "%s/%s/%s" % (KOK, kategori, slug)


def kategoriler():
    """(kategori, arac sayisi) listesi — sorgusuz aramada doner."""
    sayim = {}
    for kategori, _slug in ARACLAR:
        sayim[kategori] = sayim.get(kategori, 0) + 1
    return [(k, sayim[k], KATEGORI_ADI.get(k, k))
            for k in sorted(sayim)]


def ara(sorgu, kategori="", adet=8):
    """Katalogda kelimelerle arama; en fazla `adet` sonuc.

    Hem arac slug'i hem kategori adi uzerinde aranir (kucuk harfe
    cevrilerek). Sorgu bossa ve kategori verilmisse o kategorinin
    tum araclari doner; ikisi de bossa kategoriler listesi doner.
    """
    adet = max(1, min(int(adet or 8), 20))
    kategori = str(kategori or "").strip().lower()
    kelimeler = [k for k in str(sorgu or "").lower().split() if k]

    secilen = []
    for kat, slug in ARACLAR:
        if kategori and kat != kategori:
            continue
        if not kelimeler:
            secilen.append((kat, slug))
            continue
        # slug ve kategori uzerinde and-eslesmesi
        alan = slug.replace("-", " ") + " " + kat.replace("-", " ")
        if all(k in alan for k in kelimeler):
            secilen.append((kat, slug))

    if not kelimeler and not kategori:
        # ne sorgu ne kategori: kategorileri doner (katalog hazir degil)
        return {"kategoriler": kategoriler(), "toplam": len(ARACLAR)}

    return {
        "sonuclar": [
            {"ad": slug, "kategori": kat, "adres": adres(kat, slug)}
            for kat, slug in secilen[:adet]
        ],
        "eslesen": len(secilen),
        "toplam": len(ARACLAR),
    }
