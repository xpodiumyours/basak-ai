"""chat/gate.py — Model ciktisi oldugu gibi gecer.

2026-09-13 (Casper karari): burada modelin cevabini duzenleyen her sey
kaldirildi.

Neler vardi ve neden kalkti:
  - <think> bloklarinin silinmesi. GLM'in dusunme modu artik acik;
    o metni silmek modelin muhakemesini cope atmakti.
  - Emoji silme. Model ne yazarsa o gider.
  - Ucten fazla bos satirin kisaltilmasi.
  - Kelime listesiyle "Ingilizce sizinti" tespiti.

Geriye yalniz tip guvenligi kaldi: dict/None gelirse metne cevrilir,
yoksa arayuz patlar.
"""

import logging

logger = logging.getLogger(__name__)


def temizle(text):
    """Cevabi oldugu gibi dondurur; yalniz metin tipine cevirir."""
    if text is None:
        return ""
    if isinstance(text, str):
        return text
    if isinstance(text, dict):
        return str(text.get("content", "") or "")
    return str(text)


def dil_kontrol(text):
    """Dil denetimi kaldirildi - her cevap gecer."""
    return True


def ingilizce_sizinti_mi(text):
    """Kelime listesiyle dil tespiti kaldirildi."""
    return False
