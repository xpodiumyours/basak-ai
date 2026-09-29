"""gelir.py — reklam + affiliate baglanti disiplini (kazanc zemini).

Kural:
- Affiliate/sponsor baglantilari rel="sponsored nofollow" tasir (Google
  arama kurali) ve sayfada acik gelir-aciklamasi etiketiyle gosterilir
  (sartlar.html m.7 + sorumluluk.html zaten bunu yazar).
- Normal kaynak/atif baglantilari rel="noopener noreferrer nofollow" aynen
  kalir; ortaklik izlenimi vermez.
"""

import html
import re
from urllib.parse import urlparse

# Ortaklik/komisyon goturen alan adlari — buraya yazilan adres
# affiliate kurallarina girer (sponsored + aciklama). Liste kucuk tutulur,
# her giris Casper onayiyla eklenir.
ORTAKLIK_ALANLARI = frozenset({
    "amazon.com.tr",
    "www.amazon.com.tr",
    "amazon.com",
    "www.amazon.com",
    "hepsiburada.com",
    "www.hepsiburada.com",
    "trendyol.com",
    "www.trendyol.com",
    "n11.com",
    "www.n11.com",
    "ciceksepeti.com",
    "www.ciceksepeti.com",
})

_ACIKLAMA = ("(destek baglantisi: bu baglanti uzerinden alisveris "
             "yaparsaniz komisyon kazanabiliriz)")


def _alan(adres):
    try:
        return (urlparse(str(adres or "")).hostname or "").lower()
    except ValueError:
        return ""


def ortaklik_mi(adres):
    """Adres ortaklik alaninda mi?"""
    alan = _alan(adres)
    return bool(alan) and alan in ORTAKLIK_ALANLARI


def baglanti(metin, adres):
    """Guvenli dis baglanti HTML'i.

    Ortaklik adresiyse rel sponsored + aciklama etiketi eklenir;
    degilse normal atif (nofollow, aciklamasiz).
    """
    adres = str(adres or "").strip()
    metin = str(metin or "").strip() or adres
    if not adres.startswith(("http://", "https://")):
        return html.escape(metin, quote=True)
    if ortaklik_mi(adres):
        return ('<a href="%s" rel="sponsored nofollow" '
                'target="_blank">%s</a> <span class="gelir-aciklama">%s</span>'
                % (html.escape(adres, quote=True),
                   html.escape(metin, quote=True), _ACIKLAMA))
    return ('<a href="%s" rel="noopener noreferrer nofollow" '
            'target="_blank">%s</a>'
            % (html.escape(adres, quote=True),
               html.escape(metin, quote=True)))


def sayfadaki_ortakliklar(html_metni):
    """HTML icindeki ortaklik alanlarina giden baglantilari listeler."""
    bulunan = []
    for m in re.finditer(r'<a\b[^>]*href="([^"]+)"[^>]*>', str(html_metni)):
        if ortaklik_mi(m.group(1)):
            bulunan.append(m.group(1))
    return bulunan
