"""tools/tool_logger.py — Araç loglama sistemi.

Her tool çağrısı arac.log dosyasına yazılır. Güvenlik denetimi içindir —
ve bu yüzden KENDİSİ sızdırmamalıdır (2026-08-24, Casper'in bulgusu):

- Hassas araçların serbest metin alanları (not içeriği, defter kaydı,
  dosya gövdesi...) değer olarak DEĞİL uzunluk bilgisiyle yazılır
- Anahtar/token/parola desenleri her satırda kirmalanır (_kirmala)
- Dosya okuma sonucu (ham içerik) asla loglanmaz
- Arac.log yerel kalır ve commit'e girmez (.gitignore)
"""

import logging
import os
import re
from datetime import datetime

logger = logging.getLogger(__name__)

# Değerleri loga HAM girmeyecek serbest metin alanları
_ARG_MASKE = {
    "save_note": ("title", "content"),
    "deftere_kaydet": ("title", "content"),
    "write_file_tool": ("content",),
}

# Sonucu ham içerik olan araçlar — sonuç uzunluk bilgisiyle değiştirilir
_SONUCU_GIZLI_ARACLAR = frozenset(("read_file",))


def _kirmala(metin):
    """Bilinen şifre/anahtar desenlerini maskeleyip döndürür.

    (2026-08-24 savunma denetimi): saglayici onekleri genisletildi —
    gsk_ (Groq), hf_ (HuggingFace), nvapi- (NVIDIA), sk-or-v1-
    (OpenRouter) oncelikleri loga HAM giremez."""
    metin = re.sub(r"(?i)(bearer\s+)\S+", r"\1***", metin)
    metin = re.sub(r"\bsk-[A-Za-z0-9_-]{8,}", "sk-***", metin)
    metin = re.sub(r"\bsk-or-v1-[A-Za-z0-9]{8,}", "sk-or-***", metin)
    metin = re.sub(r"\bgsk_[A-Za-z0-9]{10,}", "gsk-***", metin)
    metin = re.sub(r"\bhf_[A-Za-z0-9]{10,}", "hf-***", metin)
    metin = re.sub(r"\bnvapi-[A-Za-z0-9_-]{10,}", "nvapi-***", metin)
    metin = re.sub(
        r"(?i)\b(api[_-]?key|token|parola|password|sifre|secret|anahtar)"
        r"(\s*[=:]\s*)(?:\"[^\"]*\"|'[^']*'|\S+)",
        r"\1\2***", metin)
    return metin


def _ozet_args(tool_name, arguments):
    """Argüman özeti: hassas alanlar '<N karakter>' olarak görünür."""
    if tool_name in _ARG_MASKE:
        gosterilecek = {}
        for anahtar, deger in (arguments or {}).items():
            if anahtar in _ARG_MASKE[tool_name] and isinstance(deger, str):
                gosterilecek[anahtar] = "<%d karakter>" % len(deger)
            else:
                gosterilecek[anahtar] = deger
        return str(gosterilecek)
    return str(arguments or {})


def _ozet_sonuc(tool_name, sonuc):
    """Sonuç özeti: ham içerik döndüren araçlarda gövde gizlenir."""
    if (tool_name in _SONUCU_GIZLI_ARACLAR
            and isinstance(sonuc, dict)
            and isinstance(sonuc.get("result"), str)):
        kopya = dict(sonuc)
        kopya["result"] = "<%d karakter gizli>" % len(sonuc["result"])
        return str(kopya)
    return str(sonuc)


def log_tool_call(tool_name: str, arguments: dict, sonuc: dict, base_dir: str):
    """Tool çağrısını arac.log'a yazar (kırmalamadan sonra).

    Args:
        tool_name: Çağrılan tool'un adı.
        arguments: Tool parametreleri.
        sonuc: Tool sonucu.
        base_dir: Proje kök dizini.
    """
    try:
        log_dosyasi = os.path.join(base_dir, "arac.log")
        tarih = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Önce maskele-kirmala, SONRA kıs (200 karakter sınırı en sona)
        args_str = _kirmala(_ozet_args(tool_name, arguments))
        if len(args_str) > 200:
            args_str = args_str[:200] + "..."

        sonuc_str = _kirmala(_ozet_sonuc(tool_name, sonuc))
        if len(sonuc_str) > 200:
            sonuc_str = sonuc_str[:200] + "..."

        durum = "OK" if isinstance(sonuc, dict) and "result" in sonuc \
            else "HATA"

        satir = f"[{tarih}] {durum} | {tool_name} | {args_str} | {sonuc_str}\n"

        with open(log_dosyasi, "a", encoding="utf-8") as f:
            f.write(satir)

    except OSError as e:
        logger.warning("Tool log yazılamadı: %s", e)
