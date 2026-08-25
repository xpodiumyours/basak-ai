"""brain/adapters — Sağlayıcı adapter'ları paketi.

Her adapter brain/adapters/*_adapter.py dosyasında tanımlıdır.
Otomatik keşif: brain.adapters.registry.discover_all()
"""

from brain.adapters.registry import discover_all, create_providers  # noqa: F401
