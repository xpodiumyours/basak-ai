"""Başak bulut işçisi — karar vermeyen tarayıcı yürütücüsü.

Bu paket model çağırmaz, plan yapmaz, araç seçmez. Yalnız Başak'ın
onayladığı tek bir eylemi uygular ve kanıt döndürür.

Alt modüller:
- `guvenlik`: HMAC onay belgesi, nonce, SSRF.
- `tarayici`: gerçek Chromium adım yürütücüsü (Playwright).
- `kuyruk`: Postgres/SQLite iş kuyruğu, kalp atışı, kalıcı nonce.
- `calistirici`: kuyruktan al → uygula → sonucu yaz.
- `ayar`, `saglik`, `__main__`: çalışma ortamı.
"""

from worker.guvenlik import (
    GuvenlikHatasi,
    TekKullanim,
    TokenHatasi,
    guvenli_url,
    token_dogrula,
    token_uret,
)
from worker.hatalar import TarayiciHatasi
from worker.kuyruk import Kuyruk, KuyrukHatasi, KuyrukNonce

__all__ = [
    "GuvenlikHatasi",
    "Kuyruk",
    "KuyrukHatasi",
    "KuyrukNonce",
    "TarayiciHatasi",
    "TekKullanim",
    "TokenHatasi",
    "guvenli_url",
    "token_dogrula",
    "token_uret",
]
