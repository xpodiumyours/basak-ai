"""tools/reminders.py — Proaktif hatırlatma sistemi.

Knowledge dosyalarındaki tarih bazlı bilgileri okur,
görev listesini kontrol eder ve bugünkü hatırlatmaları üretir.
"""

import json
import logging
import os
import re
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)

# Türkçe ay isimleri → numara
AY_MAP = {
    "ocak": 1, "şubat": 2, "mart": 3, "nisan": 4,
    "mayıs": 5, "haziran": 6, "temmuz": 7, "ağustos": 8,
    "eylül": 9, "ekim": 10, "kasım": 11, "aralık": 12,
}


def _tarih_ayikla(dosya_adi: str, icerik: str) -> list:
    """Dosya içeriğinden tarih bilgilerini çıkarır.

    Konu olarak DOSYA ADINI değil, tarihin geçtiği satırı kullanır;
    böylece 'casper hakkinda' gibi anlamsız etiketler çıkmaz.

    Returns:
        [{"tarih": datetime, "konu": str, "dosya": str}, ...]
    """
    bulunanlar = []
    bugun = datetime.now()

    pattern = re.compile(
        r'(\d{1,2})\s+(ocak|şubat|mart|nisan|mayıs|haziran|temmuz'
        r'|ağustos|eylül|ekim|kasım|aralık)',
        re.IGNORECASE,
    )

    for satir in icerik.splitlines():
        satir_temiz = satir.strip().lstrip("-*# ").strip()
        if not satir_temiz:
            continue

        eslesme = pattern.search(satir_temiz.lower())
        if not eslesme:
            continue

        try:
            gun = int(eslesme.group(1))
            ay = AY_MAP.get(eslesme.group(2))
            if not ay:
                continue

            tarih = datetime(bugun.year, ay, gun)

            # Eğer bu tarih geçtiyse gelecek yıla ayarla
            if tarih < bugun - timedelta(days=1):
                tarih = datetime(bugun.year + 1, ay, gun)
        except (ValueError, KeyError):
            continue

        # Tarihi içeren satırın kendisi en iyi açıklamadır
        konu = re.sub(r"\*\*", "", satir_temiz)[:80]

        bulunanlar.append({
            "tarih": tarih,
            "konu": konu,
            "dosya": dosya_adi,
        })

    return bulunanlar


def bugunku_hatirlatmalar(knowledge_dir: str, gorevler_file: str) -> dict:
    """Bugünkü hatırlatmaları toplar.

    1. Knowledge dosyalarındaki tarih bazlı bilgiler
    2. Bugünkü görevler
    3. Yaklaşan görevler (3 gün içinde)

    Returns:
        {"result": str} formatında hatırlatma listesi.
    """
    hatirlatmalar = []
    gorulen = set()
    bugun = datetime.now()
    bugun_str = bugun.strftime("%Y-%m-%d")

    # 1. Knowledge dosyalarından tarih bazlı bilgiler
    try:
        if os.path.exists(knowledge_dir):
            for dosya in os.listdir(knowledge_dir):
                if not dosya.lower().endswith((".md", ".txt")):
                    continue
                if dosya in ("README.md", "INDEX.md"):
                    continue

                dosya_yolu = os.path.join(knowledge_dir, dosya)
                try:
                    with open(dosya_yolu, "r", encoding="utf-8", errors="replace") as f:
                        icerik = f.read()
                except OSError:
                    continue

                tarihler = _tarih_ayikla(dosya, icerik)
                for bilgi in tarihler:
                    # Aynı gün (ay+gün) birden çok dosyada geçiyorsa
                    # sadece ilkini göster — mükerrer satır olmasın
                    anahtar = (bilgi["tarih"].month, bilgi["tarih"].day)
                    if anahtar in gorulen:
                        continue
                    gorulen.add(anahtar)

                    kalan = (bilgi["tarih"] - bugun).days

                    if kalan == 0:
                        hatirlatmalar.append(
                            f"BUGUN: {bilgi['konu']} (bugun gunu!)"
                        )
                    elif kalan == 1:
                        hatirlatmalar.append(
                            f"YARIN: {bilgi['konu']} (1 gun kaldi)"
                        )
                    elif kalan <= 7:
                        hatirlatmalar.append(
                            f"{kalan} gun sonra: {bilgi['konu']}"
                        )
    except OSError as e:
        logger.warning("Knowledge okunamadi: %s", e)

    # 2. Bugünkü görevler
    try:
        if os.path.exists(gorevler_file):
            with open(gorevler_file, "r", encoding="utf-8-sig") as f:
                gorevler = json.load(f)

            bugunku = [g for g in gorevler
                       if g.get("date") == bugun_str and not g.get("done")]

            if bugunku:
                sayi = len(bugunku)
                hatirlatmalar.append(
                    f"BUGUN ICIN {sayi} GOREV: "
                    + ", ".join(g["text"][:30] for g in bugunku[:5])
                )

            # Yaklaşan görevler (1-3 gün)
            for g in gorevler:
                if g.get("done"):
                    continue
                try:
                    g_tarih = datetime.strptime(g["date"], "%Y-%m-%d")
                    kalan = (g_tarih - bugun).days
                    if 1 <= kalan <= 3:
                        hatirlatmalar.append(
                            f"{kalan} gun sonra: {g['text'][:40]}"
                        )
                except (ValueError, KeyError):
                    continue
    except (OSError, json.JSONDecodeError) as e:
        logger.warning("Gorevler okunamadi: %s", e)

    if not hatirlatmalar:
        return {"result": "Bugun ozel bir hatirlatma yok. Iyi geceler!"}

    return {"result": "\n".join(hatirlatmalar)}
