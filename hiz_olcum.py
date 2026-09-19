"""hiz_olcum.py — Gecikme olcumu (tek seferlik, kod degistirmez).

Iki mod:

    python hiz_olcum.py            # her saglayiciyi tek tek olcer
    python hiz_olcum.py sohbet     # uctan uca sohbet (gercek yol, zincir)

"sohbet" modu kullanicinin gordugu seyi olcer: mesaj → cevap, saniye.
Once/sonra karsilastirmasi README §5'te yazili.

Cikti dosyaya da yazilabilir:
    python hiz_olcum.py sohbet > hiz_after.txt
"""

import os
import statistics
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from brain.brain import Brain  # noqa: E402

SORU = "Tek kelimeyle cevap ver: merhaba"
SOHBET_SORUSU = "merhaba, kisa cevap ver"
SOHBET_TEKERI = 3


def _saglayici_olc():
    istenen = [a.lower() for a in sys.argv[1:]]
    brain = Brain()
    zincir = brain._bulut_zinciri()
    adlar = [ad for ad, _ in zincir]
    print("musait saglayicilar: %s" % ", ".join(adlar), flush=True)
    if istenen:
        zincir = [(ad, c) for ad, c in zincir if ad in istenen]
    if not zincir:
        print("olculecek saglayici yok", flush=True)
        return

    satirlar = []
    for ad, istemci in zincir:
        t0 = time.time()
        try:
            yanit = istemci.cevapla([{"role": "user", "content": SORU}])
            sure = time.time() - t0
            if isinstance(yanit, dict):
                metin = str(yanit.get("content") or "")
            else:
                metin = str(yanit)
            satirlar.append((ad, sure, "OK", metin.strip()[:40]))
        except Exception as hata:
            sure = time.time() - t0
            satirlar.append((ad, sure, "HATA", str(hata)[:70]))
        ad, sure, durum, not_ = satirlar[-1]
        print("%-12s %6.2f sn  %-4s %s" % (ad, sure, durum, not_),
              flush=True)

    print("\n--- ozet ---", flush=True)
    calisanlar = [(a, s) for a, s, d, _ in satirlar if d == "OK"]
    for ad, sure in sorted(calisanlar, key=lambda x: x[1]):
        print("  %-12s %6.2f sn" % (ad, sure), flush=True)
    print("calisan: %d / denen: %d" % (len(calisanlar), len(satirlar)),
          flush=True)


def _sohbet_olc():
    """Kullanicinin gordugu gecikme: mesaj → cevap (zincirin tamami)."""
    brain = Brain()
    mesajlar = [
        {"role": "system", "content": "Sen Basak'sin. Turkce konus."},
        {"role": "user", "content": SOHBET_SORUSU},
    ]
    sureler = []
    for i in range(SOHBET_TEKERI):
        t0 = time.time()
        try:
            yanit, kaynak = brain.cevapla(mesajlar)
            sure = time.time() - t0
            if isinstance(yanit, dict):
                metin = str(yanit.get("content") or "")
            else:
                metin = str(yanit)
            sureler.append(sure)
            print("%d) %6.2f sn  kaynak=%-10s  %s"
                  % (i + 1, sure, kaynak, metin.strip()[:40]), flush=True)
        except Exception as hata:
            sure = time.time() - t0
            print("%d) %6.2f sn  HATA %s"
                  % (i + 1, sure, str(hata)[:80]), flush=True)
    if sureler:
        print("\nortanca: %.2f sn  (en hizli %.2f · en yavas %.2f)"
              % (statistics.median(sureler), min(sureler), max(sureler)),
              flush=True)


def main():
    if len(sys.argv) > 1 and sys.argv[1].lower() == "sohbet":
        _sohbet_olc()
    else:
        _saglayici_olc()


if __name__ == "__main__":
    main()
