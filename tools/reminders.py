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


def _saati_gecti_mi(metin, simdi):
    """Gorev metnindeki 'saat HH:MM' ifadesi bugun icin gecti mi?

    (2026-08-24 canli bulgu: 15:00'lik gorev 18:35 kartinda etiketsizdi.)
    """
    eslesme = re.search(r"saat\s+(\d{1,2})[:.](\d{2})", metin, re.IGNORECASE)
    if not eslesme:
        return False
    try:
        gorev_saati = datetime(simdi.year, simdi.month, simdi.day,
                               int(eslesme.group(1)), int(eslesme.group(2)))
    except ValueError:
        return False
    return gorev_saati < simdi


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

                    # Saat bileşeni hesaba karışmasın: takvim günü farkı
                    # (2026-08-24 canli bulgu: 2 gün kala "1 gun" diyordu)
                    kalan = (bilgi["tarih"].date() - bugun.date()).days

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
                etiketli = []
                for g in bugunku[:5]:
                    on = "[SAATI GECTI] " if _saati_gecti_mi(
                        g.get("text", ""), bugun) else ""
                    etiketli.append(on + g["text"][:30])
                hatirlatmalar.append(
                    f"BUGUN ICIN {sayi} GOREV: " + ", ".join(etiketli)
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


# --- Karşılama metni (2026-08-25, task: GOREV-acilis-ekrani) -----

_GUNLER = ("Pazartesi", "Salı", "Çarşamba", "Perşembe",
           "Cuma", "Cumartesi", "Pazar")

_AYLAR = ("", "Ocak", "Şubat", "Mart", "Nisan", "Mayıs", "Haziran",
          "Temmuz", "Ağustos", "Eylül", "Ekim", "Kasım", "Aralık")


def _selam_ver(saat):
    if 5 <= saat < 11:
        return "Günaydın"
    elif 11 <= saat < 18:
        return "Merhaba"
    elif 18 <= saat < 23:
        return "İyi akşamlar"
    else:
        return "İyi geceler"


def _turkce_sadelestir(metin):
    """Turkce harfleri ASCII'ye cevir (karsilastirma icin)."""
    harita = str.maketrans({
        'ı': 'i', 'İ': 'i', 'ş': 's', 'ğ': 'g',
        'ü': 'u', 'ö': 'o', 'ç': 'c',
    })
    return metin.translate(harita)


def _hatirlatma_temizle(satir):
    s = satir.strip()
    for etiket in ("YARIN:", "BUGUN ICIN", "BUGUN:"):
        if s.upper().startswith(etiket):
            s = s[len(etiket):].strip()
    s = re.sub(r"\s*\([^)]*\)\s*", " ", s)
    s = re.sub(r"\s*—\s*[A-Z].*", " ", s)  # gelistirici notlarini temizle
    s = re.sub(r"\s+", " ", s).strip()
    return s


def karsila_metni_olustur(knowledge_dir, gorevler_file):
    simdi = datetime.now()
    selam = _selam_ver(simdi.hour)
    gun_adi = _GUNLER[simdi.weekday()]
    tarih = f"{simdi.day} {_AYLAR[simdi.month]} {simdi.year}, {gun_adi}"
    bolumler = [f"{selam} Casper. Bugun {tarih}."]

    try:
        hatirlatma = bugunku_hatirlatmalar(knowledge_dir, gorevler_file)
        ham_metin = hatirlatma.get("result", "")
    except Exception:
        ham_metin = ""

    if ham_metin and "ozel bir hatirlatma yok" not in ham_metin.lower():
        satirlar = [l.strip() for l in ham_metin.splitlines() if l.strip()]
        temizlenmis = []
        for s in satirlar:
            temiz = _hatirlatma_temizle(s)
            if not temiz:
                continue
            if "dogum" in _turkce_sadelestir(temiz).lower():
                gun_kalan = "Yarin " if ("1 gun" in s.lower() or "yarin" in s.lower()) else ""
                yas = ""
                yil_eslesme = re.search(r"19(\d{2})", s)
                if yil_eslesme:
                    dogum_yili = 1900 + int(yil_eslesme.group(1))
                    yas = f" -- {simdi.year - dogum_yili + 1} yasina giriyorsun"
                temiz = f"{gun_kalan}Dogum gunun{yas}."
            elif re.match(r"^\d+\s+GOREV:", temiz, re.IGNORECASE):
                eslesme = re.match(r"^(\d+)\s+GOREV:(.*)", temiz, re.IGNORECASE)
                sayi = int(eslesme.group(1))
                detay = eslesme.group(2).strip()
                temiz = f"Bekleyen {sayi} gorevin var."
                if detay:
                    ilk = detay.split(",")[0].strip()
                    if len(ilk) < 50:
                        temiz += f" Birinde: {ilk}"
            elif re.match(r"^(\d+)\s+gun sonra:", temiz, re.IGNORECASE):
                eslesme = re.match(r"^(\d+)\s+gun sonra:(.*)", temiz, re.IGNORECASE)
                gun = int(eslesme.group(1))
                konu = eslesme.group(2).strip()
                temiz = f"Yarin {konu} var." if gun == 1 else f"{gun} gun sonra {konu} var."
            temizlenmis.append(temiz)
        if temizlenmis:
            bolumler.append(chr(10).join(temizlenmis))

    try:
        if os.path.exists(gorevler_file):
            with open(gorevler_file, "r", encoding="utf-8-sig") as f:
                gorevler = json.load(f)
            bugunku = [g for g in gorevler if g.get("date") == simdi.strftime("%Y-%m-%d") and not g.get("done")]
            zaten_var = any("gorev" in b.lower() for b in bolumler)
            if not zaten_var:
                if bugunku:
                    bolumler.append(f"Bekleyen {len(bugunku)} gorevin var.")
    except (OSError, json.JSONDecodeError):
        pass

    bolumler.append("Ne yapmami istersin? Dosyalarini listeleyebilir, internette arastirma yapabilirim.")

    return {"result": chr(10).join(bolumler)}
