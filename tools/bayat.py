"""tools/bayat.py — Ö-2: Bayat (staleness) kontrol modülü.

OLCU.md §5 ömür tablosuna göre her bilginin ömrü vardır.
Süresi geçmiş bilgi "bayat" olarak işaretlenir; yeniden ölçülmezse
"bayat" etiketiyle sunulur.

Ömür tablosu:
- git durumu: 1 saat
- dosya varlığı/değişim tarihi: 6 saat
- canlı site durumu: 1 gün
- kota/limit durumu: 1 gün
- proje kararı/kapsam: 30 gün
- kişisel sabitler: sonsuz
"""

import json
import os
import re
from datetime import datetime, timedelta

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Ömür tablosu — OLCU.md §5
# Anahtar: tip kelimesi (defter kaydındaki tip alanı veya kaynak ipucu)
# Değer: timedelta
OMUR_TABLOSU = {
    "git":       timedelta(hours=1),
    "olcum":     timedelta(hours=6),    # genel ölçüm varsayılanı
    "dosya":     timedelta(hours=6),
    "site":      timedelta(days=1),
    "web":       timedelta(days=1),
    "kota":      timedelta(days=1),
    "karar":     timedelta(days=30),
    "alinti":    timedelta(days=30),    # belge alıntıları yavaş değişir
    "cikarim":   timedelta(days=30),    # çıkarımlar ölçümle desteklenir
    "soru":      None,                  # açık sorular bayatlamaz
    "sonsuz":    None,                  # sonsuz ömürlü
}

# Kaynak ipuçlarına göre otomatik tespit
_KAYNAK_IPUCU = {
    "git log":      "git",
    "git status":   "git",
    "git diff":     "git",
    "rev-parse":    "git",
    "dosya":        "dosya",
    "mtime":        "dosya",
    "http://":      "site",
    "https://":     "site",
    "open-meteo":   "site",
    "kota":         "kota",
    "limit":        "kota",
}


def omur_al(tip: str = "", kaynak: str = "") -> timedelta | None:
    """Bilgi türüne göre ömür döndürür.

    Öncelik: tip alanına bakılır, bulamazsa kaynak ipuçlarından tespit edilir.
    None dönerse sonsuz ömürlüdür (bayatlamaz).

    Args:
        tip: Defter kaydındaki tip alanı (olcum, alinti, karar vb.)
        kaynak: Kaynak bilgisi (dosya yolu, URL, komut vb.)

    Returns:
        timedelta veya None (sonsuz).
    """
    # 1. Doğrudan tip eşleşmesi
    tip_lower = (tip or "").strip().lower()
    if tip_lower in OMUR_TABLOSU:
        return OMUR_TABLOSU[tip_lower]

    # 2. Kaynak ipuçlarıyla tespit
    kaynak_lower = (kaynak or "").strip().lower()
    for ipucu, tür in _KAYNAK_IPUCU.items():
        if ipucu in kaynak_lower:
            return OMUR_TABLOSU.get(tür)

    # 3. Varsayılan: ölçüm ömrü (6 saat)
    return OMUR_TABLOSU["olcum"]


def bayat_mi(tarih_str: str, tip: str = "", kaynak: str = "",
             simdi: datetime = None) -> dict:
    """Bir kaydın bayat olup olmadığını kontrol eder.

    Args:
        tarih_str: Kayıt tarihi (YYYY-MM-DD formatında)
        tip: Kayıt tipi (olcum, alinti, karar vb.)
        kaynak: Kaynak bilgisi
        simdi: Şu anki zaman (test için özelleştirilebilir)

    Returns:
        {
            "bayat": bool,
            "omur": str or None,
            "kalan": str or None,
            "mesaj": str
        }
    """
    if not tarih_str:
        return {"bayat": False, "omur": None, "kalan": None,
                "mesaj": "Tarih bilgisi yok"}

    try:
        tarih = datetime.strptime(tarih_str.strip(), "%Y-%m-%d")
    except ValueError:
        return {"bayat": False, "omur": None, "kalan": None,
                "mesaj": "Tarih formati hatali: %s" % tarih_str}

    if simdi is None:
        simdi = datetime.now()

    omur = omur_al(tip, kaynak)

    # Sonsuz ömürlü
    if omur is None:
        return {"bayat": False, "omur": "sonsuz", "kalan": None,
                "mesaj": "Sonsuz omurlu — bayatlamaz"}

    # Defter tarihleri gun bazli (saat icermez).
    # Ayni gun icinde olusturulmus kayitlar icin: kisa omurlu olcumler
    # (1s, 6s) ayni gun taze sayilir; uzun omurluler (1g, 30g) gun farkiyla kontrol edilir.
    gun_farki = (simdi.date() - tarih.date()).days

    if gun_farki == 0:
        # Ayni gun — kisa omurlu olcumler icin taze
        gun_sayisi = omur.days if omur.days > 0 else 0
        if gun_sayisi <= 0:
            # 1s veya 6s gibi kisa omurlu: ayni gun taze
            return {
                "bayat": False,
                "omur": _omur_str(omur),
                "kalan": "ayni gun",
                "mesaj": "Taze — ayni gun olusturuldu (omur: %s)"
                         % _omur_str(omur)
            }
        # 1g veya daha uzun: ayni gun taze
        return {
            "bayat": False,
            "omur": _omur_str(omur),
            "kalan": "%d gun" % gun_sayisi,
            "mesaj": "Taze — omur: %s" % _omur_str(omur)
        }

    # Farkli gunler — gun bazli karsilastir
    omur_gun = max(omur.days, 1) if omur.days > 0 else 1
    if gun_farki >= omur_gun:
        return {
            "bayat": True,
            "omur": _omur_str(omur),
            "kalan": None,
            "mesaj": "BAYAT — %d gun once olusturuldu (omur: %s)"
                     % (gun_farki, _omur_str(omur))
        }
    else:
        kalan_gun = omur_gun - gun_farki
        return {
            "bayat": False,
            "omur": _omur_str(omur),
            "kalan": "%d gun" % kalan_gun,
            "mesaj": "Taze — %d gun kaldi (omur: %s)"
                     % (kalan_gun, _omur_str(omur))
        }


def _omur_str(omur: timedelta) -> str:
    """ timedelta'ı okunabilir string'e çevirir."""
    if omur is None:
        return "sonsuz"
    gun = omur.days
    saniye = omur.seconds
    if gun > 0:
        return "%d gun" % gun
    saat = saniye // 3600
    if saat > 0:
        return "%d saat" % saat
    dakika = saniye // 60
    return "%d dakika" % dakika


def defter_bayat_kontrol(defter_dir: str, simdi: datetime = None) -> list:
    """defter/INDEX.md'deki tüm kayıtların bayatlık durumunu kontrol eder.

    Returns:
        [{"dosya": str, "bayat": bool, "mesaj": str}, ...]
    """
    index_yolu = os.path.join(defter_dir, "INDEX.md")
    sonuclar = []

    try:
        with open(index_yolu, "r", encoding="utf-8-sig") as f:
            satirlar = f.readlines()
    except OSError:
        return sonuclar

    for satir in satirlar:
        satir = satir.strip()
        if not satir.startswith("|") or satir.startswith("| dosya") or \
           satir.startswith("|---"):
            continue

        parcalar = [p.strip() for p in satir.split("|")]
        # | dosya | konu | kim | tarih | ömür |
        if len(parcalar) < 6:
            continue

        dosya = parcalar[1]
        kim = parcalar[3]
        tarih = parcalar[4]
        omur = parcalar[5]

        if not dosya or dosya == "dosya":
            continue

        # Ömür alanından tip tespit et
        tip = ""
        if omur in ("1s",):
            tip = "git"
        elif omur in ("6s",):
            tip = "olcum"
        elif omur in ("1g",):
            tip = "site"
        elif omur in ("30g",):
            tip = "karar"
        elif omur in ("sonsuz",):
            tip = "sonsuz"

        sonuc = bayat_mi(tarih, tip=tip, simdi=simdi)
        sonuc["dosya"] = dosya
        sonuc["kim"] = kim
        sonuclar.append(sonuc)

    return sonuclar


def bayat_ozet(defter_dir: str, simdi: datetime = None) -> str:
    """Bayat kayıt özetini döndürür — chat.py prompt'a eklenebilir."""
    sonuclar = defter_bayat_kontrol(defter_dir, simdi)
    bayatlar = [s for s in sonuclar if s["bayat"]]
    if not bayatlar:
        return ""
    satirlar = ["Dikkat: Su anki bayat kayitlar:"]
    for b in bayatlar:
        satirlar.append("- %s: %s" % (b["dosya"], b["mesaj"]))
    return "\n".join(satirlar)

# =========================================================================
# O-3: Otomatik yeniden sinav + karne
# =========================================================================

_KARNE_DOSYASI = os.path.join(BASE, "data", "karne.json")


def _karne_yukle():
    try:
        with open(_KARNE_DOSYASI, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return {}


def _karne_kaydet(karne):
    os.makedirs(os.path.dirname(_KARNE_DOSYASI), exist_ok=True)
    with open(_KARNE_DOSYASI, "w", encoding="utf-8") as f:
        json.dump(karne, f, ensure_ascii=False, indent=2)


def _frontmatter_oku(metin):
    if not metin.startswith("---"):
        return {}
    parcalar = metin.split("---", 2)
    if len(parcalar) < 3:
        return {}
    fm = {}
    for satir in parcalar[1].strip().splitlines():
        if ":" in satir:
            anahtar, deger = satir.split(":", 1)
            fm[anahtar.strip().lower()] = deger.strip()
    return fm


def acik_iddialari_cek(defter_dir):
    """Defterdeki acik iddialari ceker."""
    iddialar = []
    if not os.path.isdir(defter_dir):
        return iddialar

    for ad in os.listdir(defter_dir):
        if not ad.endswith(".md") or ad == "INDEX.md":
            continue
        tam = os.path.join(defter_dir, ad)
        try:
            with open(tam, "r", encoding="utf-8") as f:
                ham = f.read()
        except OSError:
            continue

        fm = _frontmatter_oku(ham)
        if not fm:
            continue

        tip = fm.get("tip", "").lower()
        durum = fm.get("durum", "").lower()

        if tip in ("olcum", "alinti") and durum in ("", "acik"):
            parcalar = ham.split("---", 2)
            icerik = parcalar[2].strip() if len(parcalar) >= 3 else ""
            iddialar.append({
                "dosya": ad,
                "konu": fm.get("konu", ad.replace(".md", "")),
                "kim": fm.get("kim", ""),
                "tarih": fm.get("tarih", ""),
                "tip": tip,
                "kaynak": fm.get("kaynak", ""),
                "icerik": icerik[:500],
            })

    return iddialar


def yeniden_sinav(dosya_yolu, yeni_olcum_metni):
    """Bir iddianin yeni olcumle karsilastirir."""
    try:
        with open(dosya_yolu, "r", encoding="utf-8") as f:
            ham = f.read()
    except OSError:
        return {"sonuc": "unknown", "mesaj": "Dosya okunamadi"}

    fm = _frontmatter_oku(ham)
    if not fm:
        return {"sonuc": "unknown", "mesaj": "Frontmatter yok"}

    parcalar = ham.split("---", 2)
    iddia_metni = parcalar[2].strip() if len(parcalar) >= 3 else ""

    if not iddia_metni or not yeni_olcum_metni:
        return {"sonuc": "unknown", "mesaj": "Yeterli metin yok"}

    # Anahtar kelime cikarma (3+ karakterli)
    iddia_kelimeleri = set(
        w.lower() for w in re.findall(r"\w{3,}", iddia_metni)
    )
    olcum_kelimeleri = set(
        w.lower() for w in re.findall(r"\w{3,}", yeni_olcum_metni)
    )

    if not iddia_kelimeleri:
        return {"sonuc": "unknown", "mesaj": "Anahtar kelime yok"}

    ortak = iddia_kelimeleri & olcum_kelimeleri
    ortak_orani = len(ortak) / len(iddia_kelimeleri)

    if ortak_orani >= 0.5:
        return {"sonuc": "confirm",
                "mesaj": "Desteklendi (ortak: %d, orani: %%%d)"
                         % (len(ortak), ortak_orani * 100)}
    elif ortak_orani < 0.2:
        return {"sonuc": "refute",
                "mesaj": "Chaturutuldu (ortak: %d, orani: %%%d)"
                         % (len(ortak), ortak_orani * 100)}
    else:
        return {"sonuc": "unknown",
                "mesaj": "Belirsiz (ortak: %d, orani: %%%d)"
                         % (len(ortak), ortak_orani * 100)}


def iddia_guncelle(dosya_yolu, yeni_durum):
    """Iddianin durumunu gunceller (confirm/refute)."""
    try:
        with open(dosya_yolu, "r", encoding="utf-8") as f:
            ham = f.read()
    except OSError:
        return False

    if not ham.startswith("---"):
        return False

    parcalar = ham.split("---", 2)
    if len(parcalar) < 3:
        return False

    fm_satirlari = parcalar[1].strip().splitlines()
    yeni_fm = []
    durum_bulundu = False
    for satir in fm_satirlari:
        if satir.strip().lower().startswith("durum:"):
            yeni_fm.append("durum: %s" % yeni_durum)
            durum_bulundu = True
        else:
            yeni_fm.append(satir)

    if not durum_bulundu:
        yeni_fm.append("durum: %s" % yeni_durum)

    yeni_ham = "---\n%s\n---%s" % ("\n".join(yeni_fm), parcalar[2])

    try:
        with open(dosya_yolu, "w", encoding="utf-8") as f:
            f.write(yeni_ham)
        return True
    except OSError:
        return False


def karnayi_guncelle(kaynak, konu, dogru=True):
    """Karneyi gunceller."""
    karne = _karne_yukle()

    if kaynak not in karne:
        karne[kaynak] = {}
    if konu not in karne[kaynak]:
        karne[kaynak][konu] = {"dogru": 0, "yanlis": 0}

    if dogru:
        karne[kaynak][konu]["dogru"] += 1
    else:
        karne[kaynak][konu]["yanlis"] += 1

    _karne_kaydet(karne)

    d = karne[kaynak][konu]
    toplam = d["dogru"] + d["yanlis"]
    basari = d["dogru"] / toplam if toplam > 0 else 0.0

    return {"toplam": toplam, "dogru": d["dogru"],
            "yanlis": d["yanlis"], "basari": basari}


def karne_ozet(kaynak=None):
    """Karse ozetini dondurur."""
    karne = _karne_yukle()
    if not karne:
        return "Karne bos."

    satirlar = []
    hedefler = {kaynak: karne[kaynak]} if kaynak and kaynak in karne else karne

    for kay, konular in hedefler.items():
        toplam_d = sum(k["dogru"] for k in konular.values())
        toplam_y = sum(k["yanlis"] for k in konular.values())
        toplam = toplam_d + toplam_y
        basari = toplam_d / toplam if toplam > 0 else 0.0
        satirlar.append("%s: %d dogru, %d yanlis (basari: %%%d)"
                        % (kay, toplam_d, toplam_y, basari * 100))

    return "\n".join(satirlar) if satirlar else "Karne bos."
