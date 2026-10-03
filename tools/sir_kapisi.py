"""tools/sir_kapisi.py — sir taramasi (kurulum gerektirmez).

2026-10-03: Bu kontrol `.githooks/pre-commit` icinde yasiydi. O dosya
calistirilabilir kod oldugu icin Git tarafindan BILINCLI OLARAK kayit
disi tutulur; o yuzden her makinede `git config core.hooksPath`
calistirmak gerekiyordu. Depo herkese acik oldugu icin kapi bir
kisin bilgisayarina bagli olamaz. Bu dosya ayni kontrolu, kurulum
gerekmeden, GitHub'da her push'ta kosturacak sekilde yazar.

Ne yapar:
  1) Izlenen dosyalar arasinda yasakli AD var mi
     (ayarlar.json, gecmis.json, .env*, *.pem, *.key)
  2) Izlenen dosyalarin icinde gercek anahtar DESENI var mi
     (sk-..., ghp_..., PRIVATE KEY, api_key = "...")

Yalnizca `git ls-files` ile listelenen (izlenen) dosyalara bakar.
Yerdeki calisma dosyalari gecerli degildir: .gitignore zaten eliyor
ve GitHub'a hic yuklenmezler.

Cikis: 0 = temiz, 1 = kapi kirmizi.

TASIMA NOTU (AGENTS.md md.5): bu bir ajan isi degil, elle
kosulabilen bir tanidir:  python tools/sir_kapisi.py
"""
import os
import re
import subprocess
import sys

# ------------------------------------------------------------ yasakli adlar
# Tasi ve karsilastirilacak adlar (buyuk/kucuk harf duyarsiz).
YASAKLI_ADLAR = (
    "ayarlar.json",
    "gecmis.json",
    "gorevler.json",
    ".env",
    ".env.local",
    ".env.production",
)

# Uzantiya bazli yasakli dosyalar.
YASAKLI_UZANTILAR = (".pem", ".key", ".p12", ".pfx")

# Icerik desenleri: gercek anahtar sekli.
# Her biri (aciklama, duzenli ifade)
ICERIK_DESENLERI = (
    ("OpenAI tarzi anahtar (sk-...)",
     re.compile(r"\bsk-[A-Za-z0-9]{20,}\b")),
    ("GitHub token (ghp_...)",
     re.compile(r"\bgh[pousr]_[A-Za-z0-9]{20,}\b")),
    ("Ozel anahtar basligi (BEGIN ... PRIVATE KEY)",
     re.compile(r"-----BEGIN [A-Z ]*PRIVATE KEY-----")),
    ("api_key / apiKey atamasi uzun degerle",
     re.compile(r"""(?i)\b(api[_-]?key|apikey|secret[_-]?key|password)\b\s*[:=]\s*["'][A-Za-z0-9_\-]{16,}["']""")),
)

# Bu dosyalar desenleri kendileri icerir; kendi kaynak kodunu
# "sir" saymamak icin muaf.
MUAF = ("tools/sir_kapisi.py",)

# Ikili/derlenmis dosyalara metin olarak bakmanin anlami yok.
BINARY_UZANTILAR = (
    ".onnx", ".wav", ".mp3", ".png", ".jpg", ".jpeg", ".gif", ".ico",
    ".pdf", ".zip", ".gz", ".db", ".sqlite", ".pyc", ".woff", ".woff2",
)

# En buyuk dosya boyutu: 2 MB ustu metin degildir (log/veri dolgusu).
MAKS_BYT = 2 * 1024 * 1024


def izlenenler():
    """`git ls-files` ciktisi (yoksa hata)."""
    try:
        out = subprocess.run(
            ["git", "ls-files", "-z"],
            capture_output=True, check=True,
        ).stdout
    except (OSError, subprocess.CalledProcessError) as e:
        print("HATA: git ls-files calismadi: %s" % e, file=sys.stderr)
        raise SystemExit(1)
    return [p for p in out.decode("utf-8", "replace").split("\0") if p]


def ad_kotu(yol):
    ad = os.path.basename(yol).lower()
    if ad in YASAKLI_ADLAR:
        return "yasakli dosya adi"
    if ad.startswith(".env"):
        return ".env dosyasi"
    if ad.endswith(YASAKLI_UZANTILAR):
        return "anahtar dosyasi uzantisi"
    return None


def tara():
    """(tur, dosya, aciklama) listesi dondurur."""
    bulunan = []
    for yol in izlenenler():
        if yol in MUAF:
            continue

        sebep = ad_kotu(yol)
        if sebep:
            bulunan.append(("AD", yol, sebep))
            continue

        if yol.lower().endswith(BINARY_UZANTILAR):
            continue
        try:
            if os.path.getsize(yol) > MAKS_BYT:
                continue
            with open(yol, "r", encoding="utf-8") as f:
                icerik = f.read()
        except (OSError, UnicodeDecodeError):
            continue

        for ad, desen in ICERIK_DESENLERI:
            m = desen.search(icerik)
            if m:
                # Eslesmenin kendisini yazma: gizli deger olabilir.
                bulunan.append(("ICERIK", yol, "%s (satir %d)"
                                % (ad, icerik[:m.start()].count("\n") + 1)))
    return bulunan


def main():
    dosyalar = izlenenler()
    bulunan = tara()

    print("Taranan izlenen dosya: %d" % len(dosyalar))
    if not bulunan:
        print("SIR KAPISI: temiz.")
        return 0

    print("")
    print("SIR KAPISI: %d SORUN" % len(bulunan))
    for tur, yol, aciklama in bulunan:
        print("  [%s] %s — %s" % (tur, yol, aciklama))
    print("")
    print("Bu dosyalar gecmisten cikarilip gecmise yazilmalidir.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
