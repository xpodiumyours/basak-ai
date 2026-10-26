"""`python -m worker` — bulut tarayıcı işçisinin giriş noktası.

Akış: ayarları oku → kalıcı kuyruğu aç → Chromium yöneticisini kur →
kalp atışıyla kuyruktan iş al → çıkışta tarayıcıyı kapat.

Karar vermez: hangi eylemin yapılacağı onay belgesinde yazılıdır.
"""

import asyncio
import logging
import os
import sys

from worker.ayar import AyarHatasi, oku
from worker.calistirici import Calistirici
from worker.kuyruk import Kuyruk, KuyrukNonce
from worker.saglik import sunucu_baslat

logger = logging.getLogger(__name__)


async def _kos(ayar, kuyruk):
    try:
        from worker.tarayici import BulutTarayici
    except ImportError as hata:
        raise AyarHatasi(
            "Playwright kurulu değil; worker/requirements-worker.txt "
            "kurulmalı") from hata

    tarayici = BulutTarayici(
        ayar.anahtar,
        zaman_asimi_ms=ayar.zaman_asimi_ms,
        nonce_defteri=KuyrukNonce(kuyruk),
    )
    calistirici = Calistirici(
        kuyruk,
        tarayici,
        isci=ayar.isci,
        surum=ayar.surum,
        aralik=ayar.aralik,
        kalp_aralik=ayar.kalp_aralik,
        esik=ayar.esik,
    )

    httpd = None
    if ayar.saglik_port:
        httpd = sunucu_baslat(ayar.saglik_port, calistirici.saglik)

    try:
        await calistirici.kos()
    finally:
        if httpd is not None:
            httpd.shutdown()
            httpd.server_close()
        await tarayici.kapat()


def main(argv=None):
    logging.basicConfig(
        level=(os.environ.get("BASAK_LOG") or "INFO").upper(),
        format="%(asctime)s %(levelname)s %(name)s: %(message)s",
    )
    try:
        ayar = oku()
    except AyarHatasi as hata:
        logger.error("ayar hatası: %s", hata)
        return 2

    try:
        kuyruk = Kuyruk(dsn=ayar.dsn or None)
    except Exception:
        logger.exception("iş kuyruğu açılamadı")
        return 2

    logger.info("Başak işçisi başlıyor: %s", ayar.ozet())
    logger.info("kuyruk arka ucu: %s", kuyruk.ad)

    try:
        asyncio.run(_kos(ayar, kuyruk))
    except AyarHatasi as hata:
        logger.error("%s", hata)
        return 2
    except KeyboardInterrupt:
        logger.info("klavyeden durduruldu")
    return 0


if __name__ == "__main__":
    sys.exit(main())
