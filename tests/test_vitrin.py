"""tests/test_vitrin.py — Ana sayfa vitrini kilidi (2026-10-22 yeniden yazım).

Eski kilid (2026-10-01): "Benim için neler yapabilir?" bolumu + ornek gorev
cipleri (6 adet, `.ornek` sinifli). O bolum 2026-10-22'de Casper karariyla
KALDIRILDI: vitrin acemi dolgusu degil, sohbetin kendisi; bolum ve buyuk
yapay zeka uyari karti telefonda/gorunur alanda gereksiz yer kapliyordu.

Yeni kilid:
- oneri basligi, cipler ve `.ornek` isleyicisi geri gelmez,
- hero'daki buyuk `.ai-notice` karti YOKTUR,
- uyari kaybolmadi: composer altinda TEK satirdir (metin birebir
  app.js UYARI_NOTU ile aynidir) + sorumluluk/bilgi linkleri tasir,
- cache surumu yeni: chat.css?v=19 / app.js?v=28 (ayni damga
  test_vercel_stream.py, test_gorsel.py, test_kesilme_devam.py,
  test_harita_z2.py, test_harita_dedektif.py'de de kilitlidir).
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

WEB = Path(__file__).resolve().parents[1] / "web"
INDEX = (WEB / "index.html").read_text(encoding="utf-8")
JS = (WEB / "app.js").read_text(encoding="utf-8")
STIL = (WEB / "chat.css").read_text(encoding="utf-8")


def test_ornek_gorev_bolumu_geri_gelmez():
    """Casper karari (2026-10-22): bolum ve cipler TAMAMEN kalkti."""
    assert "Benim için neler yapabilir" not in INDEX
    assert "quick-chip" not in INDEX
    assert "quick-actions" not in INDEX
    assert "quick-head" not in INDEX
    # app.js'te cip tiklama isleyicisi de kalmadi (artik tiklanan cip yok).
    assert 'querySelectorAll(".ornek")' not in JS
    assert "quick-chip" not in JS
    # CSS'te olu kurallari da silindi (omru bitmis stil birakilmadi).
    assert "quick-chip" not in STIL
    assert ".ai-notice" not in STIL


def test_buyuk_uyari_karti_yok_hero_sade():
    """Hero karsilamasi sade: baslik + tek satir; kart yok."""
    assert 'class="ai-notice"' not in INDEX
    assert 'id="hero"' in INDEX


def test_uyari_tek_satirda_durust_ve_linkli():
    """Uyari silinmedi; composer altinda tek satir + iki link."""
    not_blok = INDEX.split('id="composerNote"', 1)[1].split("</p>", 1)[0]
    assert "Başak hata yapabilir" in not_blok
    assert "Önemli bilgileri" in not_blok
    assert 'href="/sorumluluk.html"' in not_blok
    assert 'href="/bilgilendirme.html"' in not_blok
    # Sesli donuste app.js ayni metni yazar (UYARI_NOTU birebir ayni).
    assert ('const UYARI_NOTU = '
            '"Başak hata yapabilir. Önemli bilgileri doğrulayın."') in JS


def test_surum_kilidi_yukseltildi():
    assert "/chat.css?v=19" in INDEX
    assert "/app.js?v=28" in INDEX
