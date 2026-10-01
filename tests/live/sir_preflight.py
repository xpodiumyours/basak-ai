"""tests/live/sir_preflight.py — kabul matrisinden once sır öndenetimi.

Neden ayrı dosya: GitHub Actions'ta bu kontrol **bağımlılık kurulmadan
önce** çalışmalı. `github_full_acceptance.py` modülü içe aktarımda
`matris_kosucu`'yu (ve onun bağımlılıklarını) çeker; bu dosya yalnız
`os`/`sys` kullanır, dolayısıyla saniyeler içinde, dakikalık kurulum
harcamadan koşar.

Neden gerekli: depo gizli, Actions dakikası sınırlı ve bu iş **gerçek
sağlayıcı kotasını** harcar. Sırlar tanımlı değilse 4 dakika kurulum +
60 dakikalık koşum tamamen israf olur ve sonunda anlaşılmaz bir hata
çıkar. Bu kontrol o noktada "hangi anahtar yok" der.

Kural (fail-closed ama orantılı):
  * Hiç anahtar yoksa  -> dur (1). Test edilecek hiçbir şey yok.
  * En az biri varsa   -> devam et (0). Eksik olanlar raporda zaten
    "NOT TESTED" olarak işaretleniyor; kısmi koşum değerlidir.

Sır **değeri** hiçbir yere yazılmaz, yalnız adı ve var/yok durumu.
"""

import os
import sys

# Kapsamdaki 7 sağlayıcının anahtarı (tests/live/matris_kosucu.KAPSAM).
# Bu liste TEK kaynaktır: .github/workflows/test.yml'in env blogu ve
# preflight aynı adlari konusur (tests/test_kabul_matrisi_tetikleyici.py
# kaymanin ikisini de kilitler).
GEREKEN_SIRLER = (
    "GROQ_API_KEY",
    "GEMINI_API_KEY",
    "KILO_API_KEY",
    "NVIDIA_API_KEY",
    "ZAI_API_KEY",
    "OPENROUTER_API_KEY",
    "MISTRAL_API_KEY",
)


def _durumlar(environ=None):
    """(var, eksik) — bos ve bosluklu degerler YOK sayilir."""
    cevre = os.environ if environ is None else environ
    var, eksik = [], []
    for ad in GEREKEN_SIRLER:
        deger = (cevre.get(ad) or "").strip()
        (var if deger else eksik).append(ad)
    return var, eksik


def preflight(environ=None) -> int:
    var, eksik = _durumlar(environ)
    print("PREFLIGHT: %d/%d sır tanimli."
          % (len(var), len(GEREKEN_SIRLER)))
    for ad in var:
        print("  var     : %s" % ad)
    for ad in eksik:
        print("  EKSIK   : %s" % ad)
    if var:
        if eksik:
            print("KISIMLI KOSU: eksik %d sirlı sağlayıcılar raporda "
                  "NOT TESTED olarak işaretlenecek." % len(eksik))
        return 0
    print("HIC SIR YOK: kabul matrisi kosulamaz. Depo Ayarlari > "
          "Secrets > Actions'a ekle, sonra yeniden tetikle.")
    return 1


if __name__ == "__main__":
    sys.exit(preflight())
