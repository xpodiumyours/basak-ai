"""brain/adapters/registry.py — Adapter keşif ve kayıt sistemi.

brain/adapters/ klasöründeki tüm *_adapter.py dosyalarını otomatik keşfeder.
Her dosyada `adapter` adında bir nesne beklenir (ProviderAdapter arayüzü).

Kullanım:
    from brain.adapters.registry import discover_all
    adapters = discover_all()  # {name: adapter_instance}
"""

import importlib
import logging
import os
import pkgutil

logger = logging.getLogger(__name__)


def discover_all() -> dict:
    """brain/adapters/ klasöründeki tüm adapter'ları keşfeder.

    Dönüş: {ad: adapter_instance, ...}
    Her adapter modülünde `adapter` adında bir nesne beklenir.
    """
    adapters = {}
    package_dir = os.path.dirname(os.path.abspath(__file__))

    for importer, modname, ispkg in pkgutil.iter_modules([package_dir]):
        # base.py ve registry.py'yi atla
        if modname in ("base", "registry", "__init__"):
            continue
        if not modname.endswith("_adapter"):
            continue

        try:
            mod = importlib.import_module(f"brain.adapters.{modname}")
            adapter = getattr(mod, "adapter", None)
            if adapter is None:
                logger.warning("Adapter bulunamadı: %s (adapter nesnesi yok)", modname)
                continue
            adapters[adapter.name] = adapter
            logger.info("Adapter keşfedildi: %s -> %s", modname, adapter.name)
        except Exception as e:
            logger.warning("Adapter yüklenemedi: %s - %s", modname, e)

    return adapters


def create_providers(ayar: dict, adapters: dict = None) -> dict:
    """Tüm adapter'ları kullanarak sağlayıcı client'ları oluşturur.

    Args:
        ayar: ayarlar.json + env variable'lar
        adapters: önceden keşfedilmiş adapter dict (None ise otomatik keşfeder)

    Dönüş: {ad: client, ...}  — None değerler client oluşturulamadığını gösterir
    """
    if adapters is None:
        adapters = discover_all()

    providers = {}
    for ad, adapter in adapters.items():
        try:
            client = adapter.create(ayar)
            if client is not None:
                providers[ad] = client
                logger.info("Sağlayıcı başlatıldı: %s", ad)
            else:
                # None = bos yuva (anahtar girilmemis), ariza degil.
                logger.info("Sağlayıcı boş, atlandı: %s", ad)
        except Exception as e:
            logger.warning("Sağlayıcı başlatılamadı: %s - %s", ad, e)

    return providers
