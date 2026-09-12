"""chat/gate.py — Çıkış kapıları ve dil kontrolü modülü.

Model cevabı kullanıcıya gitmeden denetlenir:
  - Dil kontrolü (Türkçe mu? İngilizce sızıntı mı?)
  - Çıkış kapısı (sözleşme modu + işaretleme sistemi)
  - Raw tool call temizliği

Bağımlılıklar: re (standart)
DI Container: GateConfig (dil_esik, sozlesme_modu)
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
    """Cevabın çoğunlukla Türkçe olup olmadığını kontrol eder.

    Orijinal chat.py'deki mantık: karakter oranı yerine kelime tabanlı
    İngilizce sızıntı kontrolü kullanılır.
    """
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


# ── Metin temizleme ──────────────────────────────────────────────────

def temizle(text):
    """Model çıktısını temizler — ama yapısı korunur.

    - thinking/chain-of-thought blokları silinir
    - badge:: formatları temizlenir
    - Fazla boş satırlar tek satıra düşürülür
    """
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
    text = re.sub(
        "[\U0001F300-\U0001FAFF\u2600-\u27BF\u2B00-\u2BFF\uFE0F]", "",
        text)
    # badge::O:: veya badge::Ö:: formatını temizle
    text = re.sub(r'badge::[OÖ]::', '', text)
    # Kalan badge:: satırlarını da temizle
    text = re.sub(r'badge::[^\n]*', '', text)
    # Fazla boş satırları tek satıra düşür
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()
    return text


# ── Raw tool call tespiti (geçici — asıl parser chat/tools.py'de) ────

_RAW_TOOL_PATTERNS = frozenset((
    'list_files ', 'read_file ', 'web_search ', 'git_durum ',
    'belge_ara ', 'dosya_bilgi ', 'add_task ', 'save_note ',
))


def raw_tool_temizle(metin):
    """Raw tool call deseni varsa insancıl formata çevir."""
    if not metin:
        return metin
    if any(metin.startswith(p) for p in _RAW_TOOL_PATTERNS):
        alinti = re.search(r'"([^"]+)"', metin)
        if alinti:
            return alinti.group(1)
    return metin


# ── Ham ölçüm satırları (olcu.py'den birebir taşıma, 2026-09-12) ─────
# SELECT fallback'i: kazanan metin birebir YEDEK cümle ise ham ölçüm
# satırları basılır. Saf formatlayıcıdır — kapı/eleme mantığı YOKTUR.


def _arac_adi(ad):
    """Araç adını insan okuyabilir şekilde göster."""
    return {
        "list_files": "klasör listeleme",
        "read_file": "dosya okuma",
        "git_durum": "git durum",
        "belge_ara": "belge arama",
        "dosya_bilgi": "dosya bilgi",
        "web_search": "web arama",
        "sayfa_oku": "sayfa okuma",
        "add_task": "görev ekleme",
        "list_tasks": "görev listeleme",
        "complete_task": "görev tamamlama",
        "save_note": "not kaydetme",
        "deftere_kaydet": "deftere kaydetme",
        "write_file_tool": "dosya yazma",
        "ac_uygulama": "uygulama başlatma",
    }.get(ad, ad.replace("_", " "))


def ham_olcum_satirlari(olcumler, sinir=400):
    """Ölçüm çıktılarından okunabilir ham satırlar üretir.

    Bu satırları model değil KOD üretir — birebirliği tanım gereği kesindir.
    """
    satirlar = []
    for o in (olcumler or []):
        if isinstance(o, (tuple, list)) and len(o) == 2:
            ad, cikti = o
        else:
            ad, cikti = "", o
        cikti = re.sub(r"\s+", " ", str(cikti or "")).strip()
        if not cikti:
            continue
        if len(cikti) > sinir:
            cikti = cikti[:sinir].rstrip() + "..."
        cikti = cikti.replace('"', "'")
        insan_ad = _arac_adi(ad) if ad else "araç"
        satirlar.append('%s sonucu: %s' % (insan_ad, cikti))
    return satirlar


# ── GateConfig (DI Container için) ───────────────────────────────────

class GateConfig:
    """Kapı yapılandırma ayarları."""

    def __init__(self, sozlesme_modu="acik"):
        self.sozlesme_modu = sozlesme_modu
