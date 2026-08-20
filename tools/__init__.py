"""tools — Başak'ın tool modülleri.

Her tool ayrı dosyada tanımlıdır:
- definitions.py: JSON schema tool tanımları
- web_search.py: DuckDuckGo araması
- tasks.py: Görev yönetimi
- notes.py: Not yönetimi

TOOLS listesi ve calistir fonksiyonu buradan import edilir.
"""

from tools.definitions import TOOLS
from tools.executor import calistir

__all__ = ["TOOLS", "calistir"]
