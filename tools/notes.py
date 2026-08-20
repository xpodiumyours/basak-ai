"""tools/notes.py — Not yönetimi.

Notları knowledge/ klasörüne kaydeder.
Her not bir .md dosyası olarak saklanır.
Yeni not eklendiğinde INDEX.md otomatik güncellenir.
"""

import logging
import os
import re
from datetime import datetime

logger = logging.getLogger(__name__)


def save_note(title: str, content: str, knowledge_dir: str) -> dict:
    """Notu knowledge/ altına kaydeder ve INDEX.md'yi günceller.

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

        # INDEX.md'yi otomatik güncelle
        _index_guncelle(knowledge_dir, dosya_adi, title.strip(), content.strip())

        return {"result": f"Not kaydedildi: {dosya_adi}"}

    except OSError as e:
        logger.error("Not kaydedilemedi: %s", e)
        return {"error": f"Not kaydedilemedi: {e}"}


def _index_guncelle(knowledge_dir, dosya_adi, title, content):
    """INDEX.md'ye yeni not için tek satırlık özet ekler.

    INDEX.md yoksa oluşturur.
    Zaten varsa ## Notlar bölümüne ekler.
    """
    index_yolu = os.path.join(knowledge_dir, "INDEX.md")
    tarih = datetime.now().strftime("%Y-%m-%d")

    # İçeriğin ilk 60 karakterini özet olarak kullan
    ozet = content[:60].replace("\n", " ").strip()
    if len(content) > 60:
        ozet += "..."

    yeni_satir = f"- **{dosya_adi}** | konu: {title} | tarih: {tarih} | {ozet}\n"

    try:
        if os.path.exists(index_yolu):
            with open(index_yolu, "r", encoding="utf-8") as f:
                mevcut = f.read()

            # Bu dosya zaten index'de mi kontrol et
            if dosya_adi in mevcut:
                return

            # ## Notlar bölümünü bul ve ekle
            if "## Notlar" in mevcut:
                mevcut = mevcut.rstrip() + "\n" + yeni_satir
            else:
                # Notlar bölümü yoksa sona ekle
                mevcut = mevcut.rstrip() + "\n\n## Notlar\n\n" + yeni_satir
        else:
            # INDEX.md oluştur
            mevcut = (
                "# Başak Bilgi Endeksi\n\n"
                "Her not burada tek satırlık özetle listelenir.\n"
                "Başak önce bu dosyayı okur, sonra sadece ilgili dosyaları açar.\n\n"
                "## Notlar\n\n" + yeni_satir
            )

        with open(index_yolu, "w", encoding="utf-8") as f:
            f.write(mevcut)

    except OSError as e:
        logger.warning("INDEX.md güncellenemedi: %s", e)
