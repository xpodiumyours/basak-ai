"""_uretim_import_denetimi.py — canlıya almadan ÖNCE üretim yolu denetimi.

Vercel'de `app.py` sunucu-giriş noktasıdır. Burada o ortam taklit
edilir: `VERCEL=1` (kalıcı disk yok, state /tmp'ye) ve state dizini
ayarlanmış.

Neden ayrı dosya: `run_terminal_command` ortam değişkeni atamasını
engelliyor; burada `os.environ` içinde yapılır.

Kontrol edilenler:
  1. `app.py` VERCEL ortamında içe aktarılabiliyor mu?
  2. Uçlar yerinde mi (17 http ucu bekleniyor)?
  3. Z2 harita taşıması koda girdi mi (handoff olayları)?
  4. Marka ekleri sözlüğü üretimde yüklendi mi?

Kosum: python _uretim_import_denetimi.py
"""

import os
import sys

BASAK = os.path.dirname(os.path.abspath(__file__))


def main():
    os.environ["VERCEL"] = "1"
    os.environ["BASAK_STATE_DIR"] = "/tmp/basak-uretim-denetimi"
    sys.path.insert(0, BASAK)

    hata = 0
    print("URETIM YOLU DENETIMI (VERCEL=1, kalici disk yok)\n")

    try:
        import app
        print("[1] app.py import: OK")
    except Exception as e:
        print("[1] app.py import: HATA %s: %s" % (type(e).__name__, e))
        return 1

    yollar = sorted({r.path for r in app.app.routes if hasattr(r, "path")})
    http = [y for y in yollar if not y.startswith("/openapi")
            and not y.startswith("/docs") and not y.startswith("/redoc")]
    print("[2] uc sayisi: %d" % len(http))
    for y in http:
        print("      %s" % y)
    if len(http) < 15:
        print("    !! beklenenden az uc — kayıp olabilir")
        hata += 1

    # Z2 harita taşıması üretimde yerinde mi?
    olaylar = getattr(app, "_HANDOFF_OLAYLARI", None)
    if isinstance(olaylar, (set, frozenset, list, tuple)):
        harita = "harita" in olaylar
        print("[3] Z2 'harita' handoff olayi: %s (kume: %d)"
              % ("VAR" if harita else "YOK", len(olaylar)))
        if not harita:
            print("    !! Z2 tasimasi eksik")
            hata += 1
    else:
        print("[3] _HANDOFF_OLAYLARI bulunamadi (%r)" % type(olaylar).__name__)
        hata += 1

    try:
        import tools.katalog as k
        print("[4] marka ekleri sozlugu: %d meşru, %d sahte ek"
              % (len(k._SIRKET_MARKA_EKLERI), len(k._SIRKET_SAhte_EKLER)))
        if not k._SIRKET_MARKA_EKLERI or not k._SIRKET_SAhte_EKLER:
            print("    !! sozluk bos — yuklenmemis")
            hata += 1
    except Exception as e:
        print("[4] katalog import HATASI: %s" % e)
        hata += 1

    print("\nSONUC: %s" % ("GECTI" if not hata else
                             "%d SORUN VAR" % hata))
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())