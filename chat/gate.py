"""chat/gate.py — Çıkış temizliği ve dil kontrolü.

Model cevabı kullanıcıya gitmeden buradan geçer:
  - düşünme metni (<think>) silinir
  - emoji silinir (kişilik "emoji yok" der ama küçük modeller yine koyar)
  - İngilizce sızıntı yakalanır

2026-09-13: araç katmanı söküldüğü için ham araç çağrısı yakalama
(`raw_tool_temizle`) kaldırıldı — ortada çağrılacak araç yok.
"""

import logging
import re

logger = logging.getLogger(__name__)


# ── Dil kontrolü ─────────────────────────────────────────────────────

# İngilizce düşünme metni kalıpları
_ING_KELIMELER = frozenset(
    "the we need user should must answer because "
    "let okay first then assistant tool call question response they there "
    "what which about would could their this that with from have".split()
)
_TR_KELIMELER = frozenset(
    "bir ve için bu şu var yok ile daha göre olarak "
    "değil şimdi son ama veya gibi kadar sonra önce hangi nedir dalında".split()
)


def dil_kontrol(text):
    """Cevabın çoğunlukla Türkçe olup olmadığını söyler."""
    if not text or not isinstance(text, str):
        return True
    return not ingilizce_sizinti_mi(text)


def ingilizce_sizinti_mi(text):
    """Cevap, Türkçe yanıt değil de İngilizce düşünme metni mi?"""
    if not text or not isinstance(text, str):
        return False
    kelimeler = re.findall(r"[a-zçğıöşü]+", text.lower())
    if len(kelimeler) < 8:
        return False
    ing = sum(1 for k in kelimeler if k in _ING_KELIMELER)
    tr = sum(1 for k in kelimeler if k in _TR_KELIMELER)
    return ing >= 3 and ing > tr


# Emoji araliklari kod noktasiyla yazilir: kaynak dosyada duz emoji
# karakteri birakmak okunmaz ve kodlama kazalarina acik.
_EMOJI = re.compile("[%s-%s%s-%s%s-%s%s]" % (
    chr(0x1F300), chr(0x1FAFF),   # semboller, pictograflar
    chr(0x2600), chr(0x27BF),     # muhtelif semboller, dingbat
    chr(0x2B00), chr(0x2BFF),     # oklar
    chr(0xFE0F),                  # varyasyon secici
))


# ── Metin temizleme ──────────────────────────────────────────────────

def temizle(text):
    """Model çıktısını temizler — ama yapısı korunur."""
    if not text:
        return ""
    if not isinstance(text, str):
        if isinstance(text, dict):
            text = text.get("content", str(text))
        else:
            text = str(text)
    # Modelin özel düşünme metnini sil
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    # Emoji temizligi (2026-09-09): kisilik "emoji yok" der ama kucuk
    # modeller yine koyar. Gorunum katmaninda sessizce alinir.
    text = _EMOJI.sub("", text)
    # Fazla boş satırları tek satıra düşür
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
