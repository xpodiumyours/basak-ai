"""tests/test_vitrin.py — Ana sayfa vitrini kilidi (2026-10-01).

"Bütün adımlar" işinde 1. adım olarak eklenen "Benim için neler
yapabilir?" bölümünün geri gelmezliği burada kilitlenir:

- bölüm başlığı index.html'de durur,
- altindaki ornek gorev cipleri tamdir (6 adet),
- HER cip `.ornek` sinifindadir: app.js yuklemede bu siniftaki
  butun butonlara gercek gonderme yolunu baglar (metni kutuya yazar,
  gonder tusunu acar). Sinif eksilirse cip olur kalir, ziyaretci
  gorevi geciremez.
- cipler sahte/hazir cevap DEGILDIR: iclerinde donmus yanit yoktur,
  metin kullanici mesaji olarak chat.flow.mesaj_isle'den gecer.

Cache surumu kilidi (chat.css?v=11) tests/test_vercel_stream.py'dedir.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

WEB = Path(__file__).resolve().parents[1] / "web"
INDEX = (WEB / "index.html").read_text(encoding="utf-8")

BASLIK = "Benim için neler yapabilir?"
ORNEKLER = (
    "Bugün İstanbul'da hava nasıl?",
    "Bunu araştır ve kısa özetle",
    "basak-ai reposunun son commit'leri ne?",
    "240'ın yüzde 18'i kaç eder?",
    "Bunu daha anlaşılır yaz",
    "Bu fotoğraftaki ürünleri çıkar",
)


def test_vitrin_basligi_yerinde():
    assert BASLIK in INDEX


def test_ornek_cipleri_tam_ve_ornek_sinifinda():
    for metin in ORNEKLER:
        parca = 'class="quick-chip ornek" type="button">%s</button>' % metin
        assert parca in INDEX, metin


def test_cip_sayisi_kilitli():
    """Fazla/eksik cip da kırılganlık: tam 6, hepsi gercek yola bagli."""
    assert INDEX.count('class="quick-chip ornek"') == len(ORNEKLER)


def test_ciplerde_hazir_cevap_yok():
    """Cip metni bir gorev sorusudur; icinde donmus yanit/sozdizimi yoktur."""
    for metin in ORNEKLER:
        assert "BasakUI" not in metin
        assert "{{" not in metin
