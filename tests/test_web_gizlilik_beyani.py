"""tests/test_web_gizlilik_beyani.py — Faz 2 kabul 2.5 ve 2.6.

2.5: Çerez onayı verilmeden üçüncü taraf kod (reklam/analitik) calismaz —
     web/ icinde harici kaynakli script/link/import YOKTUR.
2.6: Gizlilik metni (web/bilgilendirme.html) veri listesi ile
     docs/KVKK-ENVANTER.md ayni verileri soylemelidir.
"""

import os
import re
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

ROOT = Path(__file__).resolve().parents[1]
WEB = ROOT / "web"
ENVANTER = (ROOT / "docs" / "KVKK-ENVANTER.md").read_text(encoding="utf-8")
BILGI = (WEB / "bilgilendirme.html").read_text(encoding="utf-8")


class TestOnaysizUcuncuTarafYok:
    """Faz 3 reklam/analitik kodu ancak onay SONRASI gelir (Faz 3)."""

    # Yalniz KOD yukleyen etiketler kontrol edilir: <a href> gezinme
    # baglantisi kod calistirmaz (freetools/kagit baglantilari boyle gelir).
    HARICI_KALIP = re.compile(
        r"<(?:script|link|img|iframe|source|video|audio|object|embed)\b"
        r"[^>]*?(?:src|href)\s*=\s*[\"'](?:https?:)?//[^\"']+",
        re.IGNORECASE)

    YASAK_IMZA = (
        "googletagmanager", "google-analytics", "doubleclick",
        "adsbygoogle", "pagead2.googlesyndication", "connect.facebook",
        "hotjar", "mixpanel", "segment.", "sentry.io", "fullstory",
        "clarity.ms", "criteo", "amazon-adsystem",
    )

    def test_html_ve_js_tamami_yerel_kaynak(self):
        for yol in sorted(list(WEB.rglob("*.html")) +
                          list(WEB.rglob("*.js"))):
            metin = yol.read_text(encoding="utf-8")
            eslesen = self.HARICI_KALIP.findall(metin)
            assert not eslesen, (yol.name, eslesen)

    def test_reklam_analitik_imzasi_yok(self):
        for yol in sorted(list(WEB.rglob("*.html")) +
                          list(WEB.rglob("*.js"))):
            metin = yol.read_text(encoding="utf-8").lower()
            for imza in self.YASAK_IMZA:
                assert imza not in metin, (yol.name, imza)

    def test_ucuncu_taraf_cagri_api_yok(self):
        """fetch/XHR sadece kendi sunucumuza (ayni origin) yapilir."""
        for yol in sorted(WEB.rglob("*.js")):
            metin = yol.read_text(encoding="utf-8")
            for es in re.finditer(r"""fetch\(\s*["'](https?:)?//[^"']+""",
                                  metin):
                raise AssertionError((yol.name, es.group(0)))


class TestGizlilikMetniEslestigi:
    # (envanterde aranacak ifade, bilgilendirme.html'de aranacak ifade)
    CIFTLER = (
        ("**Basak ID**", "başak id"),
        ("Sohbet geçmişi", "konuşma bağlamı"),
        ("Kalıcı hafıza notları", "kalıcı hafızaya"),
        ("Görsel ekler", "fotoğraflar"),
        ("IP / günlük verisi", "ip adresi"),
        ("Anonim günlük kota sayacı", "günlük kayıtlar"),
        ("Sağlayıcıya giden mesaj", "sağlayıcısına giden mesaj"),
    )

    def test_cift_yonde_okunur(self):
        dusuk_envanter = ENVANTER.lower()
        dusuk_bilgi = BILGI.lower()
        for envanter_sozcuk, bilgi_sozcuk in self.CIFTLER:
            assert envanter_sozcuk.lower() in dusuk_envanter, envanter_sozcuk
            assert bilgi_sozcuk.lower() in dusuk_bilgi, bilgi_sozcuk

    def test_veri_listesi_bos_madde_birakmaz(self):
        blok = re.search(r"Hangi veriler işlenebilir\?.*?</ul>", BILGI,
                         re.DOTALL)
        assert blok, "bilgilendirme.html'de veri listesi yok"
        maddeler = re.findall(r"<li>(.*?)</li>", blok.group(0), re.DOTALL)
        assert len(maddeler) >= len(self.CIFTLER)
        for m in maddeler:
            assert m.strip(), "bos veri maddesi"

    def test_bilgilendirme_sayfasi_arayuzden_bagli(self):
        index = (WEB / "index.html").read_text(encoding="utf-8")
        assert "/bilgilendirme.html" in index

    def test_kvkk_dokumani_guncel(self):
        # Anonim kimlik bicimi gerceklesenle ayni: u + 16 hane
        assert "u` ile başlayan 16 haneli" in ENVANTER
        # Yeni kota sayaci da envanterde (veri listesi eksik kalmasin)
        assert "basak_kota" in ENVANTER
