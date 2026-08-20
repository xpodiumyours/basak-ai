"""tools/notes.py — Not yönetimi.

Notları knowledge/ klasörüne kaydeder.
Her not bir .md dosyası olarak saklanır.
"""

import logging
import os
import re

logger = logging.getLogger(__name__)


def save_note(title: str, content: str, knowledge_dir: str) -> dict:
    """Notu knowledge/ altına kaydeder.

    Dosya adı title'dan türetilir: özel karakterler temizlenir,
    boşluklar tire ile değiştirilir, maximum 40 karakter.

    Args:
        title: Not başlığı.
        content: Not içeriği.
        knowledge_dir: knowledge/ klasörünün yolu.

    Returns:
        {"result": str} formatında başarı mesajı veya
        {"error": str} formatında hata mesajı.
    """
    if not title or not title.strip():
        return {"error": "Not başlığı boş olamaz"}
    if not content or not content.strip():
        return {"error": "Not içeriği boş olamaz"}

    try:
        # Dosya adını title'dan türet
        dosya_adi = re.sub(r"[^\w\s-]", "", title.lower())
        dosya_adi = re.sub(r"\s+", "-", dosya_adi.strip())[:40] + ".md"

        # knowledge/ klasörü yoksa oluştur
        os.makedirs(knowledge_dir, exist_ok=True)

        dosya_yolu = os.path.join(knowledge_dir, dosya_adi)

        with open(dosya_yolu, "w", encoding="utf-8") as f:
            f.write(f"# {title.strip()}\n\n{content.strip()}\n")

        return {"result": f"Not kaydedildi: {dosya_adi}"}

    except OSError as e:
        logger.error("Not kaydedilemedi: %s", e)
        return {"error": f"Not kaydedilemedi: {e}"}
