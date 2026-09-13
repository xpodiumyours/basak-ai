"""brain — Başak'ın ücretsiz sağlayıcı geçidi.

Ücretsiz/yerel sağlayıcılar teknik uygunluk ve hata fallback'i ile kullanılır.
Sağlayıcılar görev türüne göre zekâ sınıfına ayrılmaz. Ücretli sağlayıcılar
anahtar tanımlı olsa bile bu zincire otomatik olarak alınmaz.
"""

import brain.brain as _brain_mod
from brain.brain import Brain
from brain import registry as _registry

# SIFIR MALIYET KILIDI — QwenCloud/DashScope yeni kullanıcı kotası süreli ve
# hesap bilgileri tamamlandıysa kota bittikten sonra kullandıkça ödeye dönebilir.
# Kullanıcının "Free Quota Only" hesap ayarı uygulamadan doğrulanamadığı için
# direct QwenCloud otomatik zincire girmez. Qwen'in ücretsiz varyantları
# OpenRouter/Kilo free rotaları üzerinden yine kullanılabilir.
_brain_mod._QWEN_BEKLEMEDE = True

# Maliyet kilidi: Brain içindeki eski kod özel/ücretli "genel" sağlayıcıyı
# en sona ekleyebiliyordu. Kullanıcının hedefi sıfır maliyet olduğu için
# otomatik zincirde yalnız registry'de ücretsiz işaretli sağlayıcılar kalır.
_orijinal_bulut_zinciri = Brain._bulut_zinciri


def _ucretsiz_bulut_zinciri(self):
    return [
        (ad, istemci)
        for ad, istemci in _orijinal_bulut_zinciri(self)
        if not _registry.ucretli_mi(ad)
    ]


Brain._bulut_zinciri = _ucretsiz_bulut_zinciri

__all__ = ["Brain"]
