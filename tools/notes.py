"""tools/notes.py — Not yönetimi.

Notları knowledge/ klasörüne kaydeder (save_note).
OD-1: deftere_kaydet ile ortak deftere de yazar (kim/tarih/tip/ömür/kaynak biçimi).
"""

import logging
import os
import re
from datetime import datetime

logger = logging.getLogger(__name__)

# OD-1: Ortak defter biçimi — ORTAK-DEFTER.md §3
_DEFTER_KIMLER = ("freebuff", "claude", "basak", "casper", "kilo", "opencode")
_DEFTER_TIPLER = ("olcum", "alinti", "cikarim", "karar", "soru")
_DEFTER_OMURLAR = ("1s", "6s", "1g", "30g", "sonsuz")


def _slug(title, varsayilan="not"):
    """Başlıktan güvenli dosya adı gövdesi üretir."""
    govde = re.sub(r"[^\w\s-]", "", title.lower())
    govde = re.sub(r"\s+", "-", govde.strip())[:40]
    return govde or varsayilan


def _benzersiz_yol(klasor, dosya_adi):
    """Aynı ada çarpmadan yeni yol döndürür.

    ÜZERİNE YAZILMAZ kuralı (2026-08-24, Casper'in bulgusu): hedef varsa
    '-2', '-3'... sonekiyle boş ad bulunur. Eski kayıt her zaman yaşar.
    """
    kok, uzanti = os.path.splitext(dosya_adi)
    aday = os.path.join(klasor, dosya_adi)
    sira = 2
    while os.path.exists(aday):
        aday = os.path.join(klasor, "%s-%d%s" % (kok, sira, uzanti))
        sira += 1
        if sira > 999:
            # teorik taşma — zaman damgasıyla garantili benzersiz
            aday = os.path.join(
                klasor, "%s-%s%s" % (kok,
                                     datetime.now().strftime("%H%M%S%f"),
                                     uzanti))
            break
    return aday


def save_note(title: str, content: str, knowledge_dir: str) -> dict:
    """Notu knowledge/ altına kaydeder ve INDEX.md'yi günceller.

    Dosya adı title'dan türetilir; AYNI ADA denk gelirse eski dosya
    korunur ve yeni not '-2', '-3'... sonekli dosyaya yazılır.
    """
    if not title or not title.strip():
        return {"error": "Not başlığı boş olamaz"}
    if not content or not content.strip():
        return {"error": "Not içeriği boş olamaz"}

    try:
        dosya_adi = _slug(title) + ".md"

        # knowledge/ klasörü yoksa oluştur
        os.makedirs(knowledge_dir, exist_ok=True)

        dosya_yolu = _benzersiz_yol(knowledge_dir, dosya_adi)
        dosya_adi = os.path.basename(dosya_yolu)

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


def deftere_kaydet(title: str, content: str, defter_dir: str,
                   kim: str = "basak", tip: str = "alinti",
                   omur: str = "30g", kaynak: str = "sohbet") -> dict:
    """OD-1: Ortak deftere kayıt yazar (ORTAK-DEFTER.md §3 biçimi).

    Format:
    ---
    kim: basak
    tarih: 2026-08-22
    konu: ...
    tip: alinti
    omur: 30g
    kaynak: sohbet
    ---
    İçerik...

    INDEX.md de otomatik güncellenir (tablo satırı olarak).

    Args:
        title: Kayıt konusu (dosya adına dönüştürülür).
        content: Kayıt içeriği (tek paragraf, uzun anlatım yok).
        defter_dir: defter/ klasörünün yolu.
        kim: Yazan taraf (freebuff|claude|basak|casper|kilo|opencode).
        tip: Kayıt tipi (olcum|alinti|cikarim|karar|soru).
        omur: Bilgi ömrü (1s|6s|1g|30g|sonsuz).
        kaynak: Bilgi kaynağı (ölçüm komutu, dosya adı, sohbet vb.).

    Returns:
        {"result": str} başarı veya {"error": str} hata.
    """
    if not title or not title.strip():
        return {"error": "Kayıt konusu boş olamaz"}
    if not content or not content.strip():
        return {"error": "Kayıt içeriği boş olamaz"}

    kim = kim.strip().lower()
    tip = tip.strip().lower()
    omur = omur.strip().lower()

    if kim not in _DEFTER_KIMLER:
        return {"error": "Geçersiz kim: '%s'. İzinliler: %s"
                         % (kim[:20], ", ".join(_DEFTER_KIMLER))}
    if tip not in _DEFTER_TIPLER:
        return {"error": "Geçersiz tip: '%s'. İzinliler: %s"
                         % (tip[:20], ", ".join(_DEFTER_TIPLER))}
    if omur not in _DEFTER_OMURLAR:
        return {"error": "Geçersiz ömür: '%s'. İzinliler: %s"
                         % (omur[:20], ", ".join(_DEFTER_OMURLAR))}

    try:
        # Dosya adını title'dan türet (ORTAK-DEFTER.md biçimi)
        dosya_adi = _slug(title, varsayilan="kayit") + ".md"

        os.makedirs(defter_dir, exist_ok=True)
        # ÜZERİNE YAZILMAZ (ORTAK-DEFTER.md): aynı ad varsa yeni sonekli
        # dosyaya yazılır — eski kayıt asla ezilmez.
        dosya_yolu = _benzersiz_yol(defter_dir, dosya_adi)
        dosya_adi = os.path.basename(dosya_yolu)

        tarih = datetime.now().strftime("%Y-%m-%d")

        # ORTAK-DEFTER.md §3frontmatter biçimi
        icerik = (
            "---\n"
            "kim:    %s\n"
            "tarih:  %s\n"
            "konu:   %s\n"
            "tip:    %s\n"
            "omur:   %s\n"
            "kaynak: %s\n"
            "---\n\n"
            "%s\n"
        ) % (kim, tarih, title.strip(), tip, omur,
             kaynak.strip(), content.strip())

        with open(dosya_yolu, "w", encoding="utf-8") as f:
            f.write(icerik)

        # INDEX.md'yi güncelle (tablo satırı)
        _defter_index_guncelle(defter_dir, dosya_adi, title.strip(),
                               kim, tarih, omur)

        return {"result": "Deftere kayıt eklendi: %s" % dosya_adi}

    except OSError as e:
        logger.error("Defter kaydı başarısız: %s", e)
        return {"error": "Defter kaydı başarısız: %s" % e}


def _defter_index_guncelle(defter_dir, dosya_adi, konu, kim, tarih, omur):
    """defter/INDEX.md'ye tablo satırı ekler (ORTAK-DEFTER.md §3 biçimi)."""
    index_yolu = os.path.join(defter_dir, "INDEX.md")

    try:
        if os.path.exists(index_yolu):
            with open(index_yolu, "r", encoding="utf-8-sig") as f:
                mevcut = f.read()

            # Bu dosya zaten index'de mi?
            if dosya_adi in mevcut:
                return

            # Tablonun sonuna ekle (son | satırından sonra)
            yeni_satir = ("| %s | %s | %s | %s | %s |"
                          % (dosya_adi, konu[:60], kim, tarih, omur))
            mevcut = mevcut.rstrip() + "\n" + yeni_satir + "\n"
        else:
            # INDEX.md oluştur
            mevcut = (
                "# ORTAK DEFTER — INDEX\n\n"
                "*Tek satır = tek kayıt. Ayrıntı için dosyanın kendisini oku."
                " Silme yok; bayat kayıt işaretlenir, üzerine yazılmaz.*\n\n"
                "| dosya | konu | kim | tarih | ömür |\n"
                "|---|---|---|---|---|\n"
                "| %s | %s | %s | %s | %s |\n"
                % (dosya_adi, konu[:60], kim, tarih, omur)
            )

        with open(index_yolu, "w", encoding="utf-8") as f:
            f.write(mevcut)

    except OSError as e:
        logger.warning("Defter INDEX güncellenemedi: %s", e)
