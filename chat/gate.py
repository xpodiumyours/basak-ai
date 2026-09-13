"""chat/gate.py — Model ciktisi oldugu gibi gecer.

2026-09-13 (Casper karari): modelin cevabini duzenleyen her sey
kaldirildi: <think> silme, emoji silme, bos satir kisaltma, badge
temizligi, kelime listesiyle dil tespiti, ham arac cagrisi yakalama.

Geriye yalniz tip guvenligi kaldi: dict/None gelirse metne cevrilir,
yoksa arayuz patlar.
"""


def temizle(text):
    """Cevabi oldugu gibi dondurur; yalniz metin tipine cevirir."""
    if text is None:
        return ""
    if isinstance(text, str):
        return text
    if isinstance(text, dict):
        return str(text.get("content", "") or "")
    return str(text)
