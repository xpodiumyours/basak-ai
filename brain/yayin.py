"""brain/yayin.py — streaming uyumluluk katmani.

Eski streaming yolu modele tools vermeden çağrı açıyordu. Bu nedenle model
web/dosya/görev araçlarını seçemeden düz cevap üretebiliyordu. Tam kapasite
modunda bu hızlı ama araçsız yol kullanılmaz; çağıran kod AracIstegi görüp
standart, tool-enabled akışa geçer. Böylece gereksiz ilk API isteği de yapılmaz.
"""


class AracIstegi(Exception):
    """Tam tool-enabled yol kullanılmalı."""


class SonHata(Exception):
    def __init__(self, ozet):
        super().__init__(ozet)
        self.ozet = ozet


def akit(openai_client, model, messages):
    """Tool-blind streaming yerine doğrudan tam yetenekli yola geçir."""
    raise AracIstegi()
    yield ""  # pragma: no cover — fonksiyonun generator sözleşmesini korur


def ollama_akit(base_url, model, messages):
    """Yerel modelde de araçlar gizlenmesin; tam yola geçir."""
    raise AracIstegi()
    yield ""  # pragma: no cover
