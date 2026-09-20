"""tray.py — Sistem tepsisi ikonu (P1).

Pencere kapansa bile Başak arka planda yaşamaya devam eder.
Tepsi ikonundan geri açılır ya da tamamen kapatılır (kill switch).
"""

import logging
import threading

import pystray
from PIL import Image, ImageDraw

logger = logging.getLogger(__name__)

_icon = None


def _sar(func, ad):
    """Tepsi tıklaması asla sessiz yutulmaz: hata hata.log + ekrana."""
    def _kos():
        try:
            func()
        except Exception as e:
            logger.warning("Tepsi '%s' yapilamadi: %s", ad, e)
            try:
                print("Tepsi '%s' yapılamadı: %s" % (ad, e), flush=True)
            except Exception:
                pass
    return _kos


def _ikon_uret():
    """Mavi daire — Başak ikonu (harici dosya gerektirmez)."""
    img = Image.new("RGBA", (64, 64), (0, 0, 0, 0))
    ciz = ImageDraw.Draw(img)
    # Dış halka + iç küre görünümü
    ciz.ellipse([2, 2, 62, 62], fill=(29, 78, 216, 255))
    ciz.ellipse([8, 8, 56, 56], fill=(59, 130, 246, 255))
    ciz.ellipse([16, 12, 40, 34], fill=(147, 197, 253, 180))
    return img


def baslat(goster_cb, gizle_cb, cikis_cb):
    """Tepsi ikonunu ayrı iş parçacığında başlatır.

    Args:
        goster_cb: Pencereyi gösteren fonksiyon (ana iş parçacığında çalışır).
        gizle_cb: Pencereyi gizleyen fonksiyon.
        cikis_cb: Uygulamayı tamamen kapatan fonksiyon.
    """
    global _icon

    menu = pystray.Menu(
        pystray.MenuItem("Göster", _sar(goster_cb, "Göster"), default=True),
        pystray.MenuItem("Gizle", _sar(gizle_cb, "Gizle")),
        pystray.MenuItem("Tamamen Kapat", _sar(cikis_cb, "Tamamen Kapat")),
    )
    _icon = pystray.Icon("Basak", _ikon_uret(), "BAŞAK — kardeşin burada", menu)
    t = threading.Thread(target=_icon.run, daemon=True)
    t.start()
    logger.info("Tepsi ikonu başlatıldı.")
    try:
        print("Tepsi ikonu başlatıldı.", flush=True)
    except Exception:
        pass


def durdur():
    """Tepsi ikonunu kapatır."""
    global _icon
    if _icon is not None:
        try:
            _icon.stop()
        except Exception as e:
            logger.warning("Tepsi durdurulamadi: %s", e)
            try:
                print("Tepsi durdurulamadı: %s" % e, flush=True)
            except Exception:
                pass
        _icon = None
