"""brain — Başak'ın beyin modülü.

Otomatik sohbet zinciri yalnız sıfır-maliyet olarak doğrulanmış bulut
sağlayıcılardan oluşur. Ajan modu ayrıca required-tool protokolü doğrulanmış
sağlayıcıları kullanır. Qwen entegrasyonu korunur ancak süreli kota nedeniyle
otomatik sıfır-maliyet zincirine alınmaz.
"""

from brain.brain import Brain

__all__ = ["Brain"]
