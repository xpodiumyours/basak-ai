"""tests/test_sir_kapisi.py — sır taraması gerçekten yakalıyor mu?

2026-10-03: kapı `.githooks/pre-commit` içindeydi ve HER BİLGİSAYARDA
`git config core.hooksPath` çalıştırmak gerekiyordu. Depo herkese açık
olduğu için kapı tek kişinin makinesine bağlı olamaz; `tools/sir_kapisi.py`
aynı kontrolü kurulum gerektirmeden yapar (bkz. `.github/workflows/kapi.yml`).

Bu test, taramanın boş çıkmadığını — yani bir kuralın kazara boş
kalmadığını — kanıtlar. Sır "bulunamadı" testi, sır yok demek değildir.
"""
import os
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import sir_kapisi as kap  # noqa: E402


def _yaz(yol, icerik):
    os.makedirs(os.path.dirname(yol) or ".", exist_ok=True)
    with open(yol, "w", encoding="utf-8") as f:
        f.write(icerik)
    return yol


def test_yasakli_ad_tanimli():
    """Yasaklı ad listesi boş olmamalı — boşsa kapı hiçbir şeyi yakalamaz."""
    assert kap.YASAKLI_ADLAR, "yasakli ad listesi bos"
    assert "ayarlar.json" in kap.YASAKLI_ADLAR
    assert "gecmis.json" in kap.YASAKLI_ADLAR
    assert ".env" in kap.YASAKLI_ADLAR


def test_icerik_desenleri_tanimli():
    assert len(kap.ICERIK_DESENLERI) >= 4, "desenler eksik"
    desenler = " ".join(d.pattern for _, d in kap.ICERIK_DESENLERI)
    # Kesin eslesme asagidaki testte; burada yalniz kapsam genisligi.
    assert "sk-" in desenler
    assert "gh" in desenler, "GitHub token deseni yok"
    assert "PRIVATE KEY" in desenler


def test_yasakli_ad_yakalanir():
    assert kap.ad_kotu("data/ayarlar.json") == "yasakli dosya adi"
    assert kap.ad_kotu("ayarlar.json") == "yasakli dosya adi"
    # .env.production listede de var; adi ya da .env baslangici olsun,
    # sonuc "bu dosya gitmez" olmali.
    assert kap.ad_kotu(".env.production") is not None
    assert kap.ad_kotu(".env") is not None
    assert kap.ad_kotu("certs/sunucu.pem") == "anahtar dosyasi uzantisi"


def test_normal_dosya_yanlis_pozitif_vermez():
    """Sir olmayan dosyalar tetiklenmemeli."""
    assert kap.ad_kotu("tools/sir_kapisi.py") is None
    assert kap.ad_kotu("ayarlar.ornek.json") is None
    assert kap.ad_kotu("web/index.html") is None
    assert kap.ad_kotu(".gitignore") is None
    # .env.example turu dosyalar da gecmis olabilir; burada yasakli.
    assert kap.ad_kotu("README.md") is None


def test_gercek_anahtar_deseni_eslesir():
    """Sahte ama bicim dogru bir anahtar yakalanmali.

    ORNEKLER PARCA PARCA KURULUR: sir kapisi kendi test dosyasini
    okuyor. Anahtar kalibi burada duz yazilirsa kapi kendi testini
    "sir" diye yakalar (gercekte boyle oldu). Muaf listeye eklemek
    yerine metin calisma aninda birlestirilir — muaf listesi zamanla
    delik olur.
    """
    desenler = [d for _, d in kap.ICERIK_DESENLERI]
    ornek = 'OPENAI_API_KEY = "sk-' + ("A" * 32) + '"'
    assert any(d.search(ornek) for d in desenler), "sk- deseni eslesmedi"

    gh = "token: ghp_" + ("b" * 36)
    assert any(d.search(gh) for d in desenler), "ghp_ deseni eslesmedi"

    pk = "-----BEGIN " + "RSA " + "PRIVATE KEY" + "-----"
    assert any(d.search(pk) for d in desenler), "PRIVATE KEY deseni eslesmedi"

    atama = 'password = "' + ("p" * 20) + '"'
    assert any(d.search(atama) for d in desenler), "atama deseni eslesmedi"


def test_kapi_kendi_kaynak_kodunda_tetiklenmez():
    """Kapi kendi desenlerini iceren dosyayi okumamali.

    Bu dosyada gercek anahtar deseni YOK; ama ilerde bir desen
    ornek olarak yazilirsa kapı kendini kirmiziye boyamamali.
    """
    assert "tools/sir_kapisi.py" in kap.MUAF


def test_gercek_depo_temiz():
    """Bu depoda su an sır olmamali.

    Kirmizi olursa: ya bir sır kaydedildi (gercek acil!) ya da tarama
    kurali fazla genis. Ikisini de ayirt etmek icin mesaj okunmali.
    """
    sonuc = subprocess.run(
        [sys.executable, "tools/sir_kapisi.py"],
        capture_output=True, text=True, encoding="utf-8",
    )
    assert sonuc.returncode == 0, sonuc.stdout
    assert "temiz" in sonuc.stdout
