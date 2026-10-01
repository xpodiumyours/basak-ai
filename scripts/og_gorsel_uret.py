"""web/og.png üretir — Başak (Virgo) takımyıldızı temalı OG paylaşım görseli.

Kullanım:  python scripts/og_gorsel_uret.py
Çıktı:     web/og.png  (yayında /og.png olarak sunulur, 1200x630)

Tasarım: gece mavisi zemin, solda marka metni, sağda Başak takımyıldızının
basitleştirilmiş çizimi (Spica en parlak yıldız). Font: Windows Segoe UI.
"""

from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

W, H = 1200, 630
KOK = Path(__file__).resolve().parents[1]
CIKTI = KOK / "web" / "og.png"

ZEMIN = (10, 14, 26)
YAZI = (240, 243, 250)
SOLUK = (150, 158, 175)
VURGU = (122, 162, 255)
ALTIN = (255, 214, 120)
CIZGI = (74, 92, 140)

FON_YOLU = Path("C:/Windows/Fonts/")


def font(ad, boyut):
    return ImageFont.truetype(str(FON_YOLU / ad), boyut)


# Başak (Virgo) takımyıldızı — birim kare içinde stilize konumlar.
YILDIZLAR = {
    "zaniah": (0.10, 0.34),
    "porrima": (0.28, 0.40),
    "auva": (0.44, 0.22),
    "vindemiatrix": (0.60, 0.05),
    "heze": (0.66, 0.48),
    "spica": (0.82, 0.86),
    "ksi": (0.86, 0.20),
}
CIZGILER = [
    ("zaniah", "porrima"),
    ("porrima", "auva"),
    ("auva", "vindemiatrix"),
    ("porrima", "heze"),
    ("heze", "spica"),
    ("auva", "heze"),
]


def yildiz_ciz(d, x, y, r, parlaklik=1.0):
    """Yildizi halesiyle birlikte cizer."""
    for halka, alfa in ((r * 5, 26), (r * 3, 52), (r * 1.7, 110)):
        d.ellipse(
            (x - halka, y - halka, x + halka, y + halka),
            fill=(VURGU[0], VURGU[1], VURGU[2], int(alfa * parlaklik)),
        )
    d.ellipse((x - r, y - r, x + r, y + r),
              fill=(255, 255, 255, int(255 * parlaklik)))


def main():
    img = Image.new("RGBA", (W, H), ZEMIN + (255,))
    d = ImageDraw.Draw(img, "RGBA")

    # Arka plan: seyrek yıldız tozu (tekrarlanabilirlik için sabit tohum).
    import random
    rnd = random.Random(7)
    for _ in range(90):
        x, y = rnd.uniform(0, W), rnd.uniform(0, H)
        r = rnd.uniform(0.6, 1.6)
        d.ellipse((x - r, y - r, x + r, y + r), fill=(255, 255, 255, rnd.randint(30, 120)))

    # --- Sag: Başak takımyıldızı ---
    kutu_x, kutu_y, kutu_w, kutu_h = 660, 70, 480, 470
    nokta = {
        ad: (kutu_x + nx * kutu_w, kutu_y + ny * kutu_h)
        for ad, (nx, ny) in YILDIZLAR.items()
    }
    for a, b in CIZGILER:
        d.line([nokta[a], nokta[b]], fill=CIZGI + (255,), width=3)
    for ad, (x, y) in nokta.items():
        if ad == "spica":
            # En parlak yildiz: arti seklinde kirilim isigi.
            d.line([(x - 34, y), (x + 34, y)], fill=ALTIN + (140,), width=2)
            d.line([(x, y - 34), (x, y + 34)], fill=ALTIN + (140,), width=2)
            yildiz_ciz(d, x, y, 8, parlaklik=1.0)
        else:
            yildiz_ciz(d, x, y, 4, parlaklik=0.85)
    d.text((kutu_x + 8, kutu_y + kutu_h + 24),
           "Başak (Virgo) takımyıldızı · en parlak yıldız: Spica",
           font=font("segoeui.ttf", 20), fill=SOLUK + (255,))

    # --- Sol: marka metni ---
    d.text((80, 96), "Başak", font=font("segoeuib.ttf", 120), fill=YAZI + (255,))
    d.text((84, 250), "Türkçe kişisel yapay zekâ asistanı",
           font=font("segoeui.ttf", 40), fill=YAZI + (255,))
    d.text((84, 306), "Kayıtsız web sohbeti · görsel · ses",
           font=font("segoeui.ttf", 30), fill=SOLUK + (255,))

    # Uc rozet (pill) etiketleri.
    rozet = [("162 ücretsiz araç", 84), ("kayıt gerekmez", 330)]
    rx = 84
    for metin, _ in rozet:
        en = d.textlength(metin, font=font("segoeui.ttf", 24))
        d.rounded_rectangle((rx, 380, rx + en + 44, 430), radius=25,
                            outline=VURGU + (255,), width=2)
        d.text((rx + 22, 391), metin, font=font("segoeui.ttf", 24),
               fill=VURGU + (255,))
        rx += en + 44 + 18

    d.text((84, 540), "basak-vercel.vercel.app", font=font("segoeuib.ttf", 26),
           fill=VURGU + (255,))

    CIKTI.parent.mkdir(exist_ok=True)
    img.convert("RGB").save(CIKTI, "PNG", optimize=True)
    print(f"yazildi: {CIKTI} ({CIKTI.stat().st_size} bayt)")


if __name__ == "__main__":
    main()
