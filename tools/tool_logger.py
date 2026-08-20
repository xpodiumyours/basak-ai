"""tools/tool_logger.py — Araç loglama sistemi.

Her tool çağrısı arac.log dosyasına yazılır.
Güvenlik denetimi için kullanılır.
"""

import logging
import os
from datetime import datetime

logger = logging.getLogger(__name__)


def log_tool_call(tool_name: str, arguments: dict, sonuc: dict, base_dir: str):
    """Tool çağrısını arac.log'a yazar.

    Args:
        tool_name: Çağrılan tool'un adı.
        arguments: Tool parametreleri.
        sonuc: Tool sonucu.
        base_dir: Proje kök dizini.
    """
    try:
        log_dosyasi = os.path.join(base_dir, "arac.log")
        tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Sonucu kısalt
        sonuc_str = str(sonuc)
        if len(sonuc_str) > 200:
            sonuc_str = sonuc_str[:200] + "..."

        # Parametreleri kısalt
        args_str = str(arguments)
        if len(args_str) > 200:
            args_str = args_str[:200] + "..."

        durum = "OK" if "result" in sonuc else "HATA"

        satir = f"[{tarih}] {durum} | {tool_name} | {args_str} | {sonuc_str}\n"

        with open(log_dosyasi, "a", encoding="utf-8") as f:
            f.write(satir)

    except OSError as e:
        logger.warning("Tool log yazılamadı: %s", e)
