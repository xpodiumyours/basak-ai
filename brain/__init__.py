"""brain — Başak'ın sağlayıcı geçidi.

Ücretsiz/yerel sağlayıcılar teknik uygunluk ve hata fallback'i ile kullanılır.
Sağlayıcılar görev türüne göre zekâ sınıfına ayrılmaz.
"""

import brain.brain as _brain_mod
from brain.brain import Brain

# Eski 403 gözleminden kalan kalıcı Qwen kilidi kaldırıldı. Anahtarı/hesabı
# gerçekten çalışmıyorsa normal hata + cooldown/fallback mekanizması devralır.
_brain_mod._QWEN_BEKLEMEDE = False

__all__ = ["Brain"]
