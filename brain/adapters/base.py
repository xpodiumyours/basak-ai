"""brain/adapters/base.py — Adapter arayüzü.

Her sağlayıcı adapter'ı bu arayüzü uygular.
Factory fonksiyonu: ayar dict'ini alır, client döndürür (None = kullanılamaz).
"""

from typing import Optional, Protocol


class ProviderAdapter(Protocol):
    """Sağlayıcı adapter'ı arayüzü."""

    @property
    def name(self) -> str:
        """Sağlayıcı adı (registry key): 'groq', 'gemini', vb."""
        ...

    def create(self, ayar: dict) -> Optional[object]:
        """Client oluşturur.

        Args:
            ayar: ayarlar.json + env variable'lar (birleştirilmiş)

        Returns:
            Client nesnesi veya None (başarısızsa/kullanılamıyorsa)
        """
        ...
