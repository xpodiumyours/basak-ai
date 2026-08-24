"""tools/dunya.py — Başak'ın dünya modeli katmanı (DÜNYA-0, kilitli hedef).

YENI DEPO ACMAZ: defter kayıtları zaten iddiadır, karne.json kaynak
güvenini tutar, bayat.py tazeliği ölçer. DÜNYA-0 bu üçünü TEK
sorgulanabilir inanç listesinde birleştirir. Dosyalar kaynak gerçeği
olmayı sürdürür — motor hiçbir şeyi kendi başına değiştirmez.

İnanç kaydı:
  {dosya, konu, kim, tarih, omur, kaynak, durum(taze|bayat),
   guven(0.0-1.0), icerik}

Güven kuralı: karne'de bu kaynak için doğru/yanlış verisi varsa
doğru/(doğru+yanlış); veri yoksa nötr 0.5 (bilinmedikçe suçlanmaz).
"""

import os

from tools import bayat

# ORTAK-DEFTER ömür etiketini bayat tipine çeviren harita
# (bayat.defter_bayat_kontrol ile aynı mantık)
_OMUR_TIP = {
    "1s": "git",
    "6s": "olcum",
    "1g": "site",
    "30g": "karar",
    "sonsuz": "sonsuz",
}


def _guven_hesapla(karne, kaynak):
    """Kaynağın karne başarısı; veri yoksa nötr 0.5."""
    konular = karne.get(kaynak) or {}
    dogru = sum(v.get("dogru", 0) for v in konular.values()
                if isinstance(v, dict))
    yanlis = sum(v.get("yanlis", 0) for v in konular.values()
                 if isinstance(v, dict))
    toplam = dogru + yanlis
    return round(dogru / toplam, 2) if toplam else 0.5


def inanclari_topla(defter_dir, simdi=None):
    """Defterdeki tüm kayıtları sorgulanabilir inanç kayıtlarına çevirir."""
    if not os.path.isdir(defter_dir):
        return []

    karne = bayat._karne_yukle()
    inanclar = []

    for ad in sorted(os.listdir(defter_dir)):
        if not ad.endswith(".md") or ad == "INDEX.md":
            continue
        tam_yol = os.path.join(defter_dir, ad)
        try:
            with open(tam_yol, "r", encoding="utf-8") as f:
                ham = f.read()
        except OSError:
            continue

        fm = bayat._frontmatter_oku(ham)
        if not fm:
            continue

        tarih = fm.get("tarih", "")
        omur = fm.get("omur", "")
        kaynak = fm.get("kaynak", "")

        try:
            tazelik = bayat.bayat_mi(tarih, tip=_OMUR_TIP.get(omur, ""),
                                     simdi=simdi)
            durum = "bayat" if tazelik.get("bayat") else "taze"
        except Exception:
            durum = "taze"

        parcalar = ham.split("---", 2)
        icerik = parcalar[2].strip()[:300] if len(parcalar) >= 3 else ""

        inanclar.append({
            "dosya": ad,
            "konu": fm.get("konu", ad[:-3]),
            "kim": fm.get("kim", ""),
            "tarih": tarih,
            "omur": omur,
            "kaynak": kaynak,
            "durum": durum,
            "guven": _guven_hesapla(karne, kaynak),
            "icerik": icerik,
        })

    # en güvenli ve en yeni önce
    inanclar.sort(key=lambda i: (-i["guven"], i["tarih"]), reverse=False)
    inanclar.sort(key=lambda i: i["tarih"], reverse=True)
    return inanclar


def dunya_sorgu(defter_dir, anahtar=None, kim=None, tip=None, kaynak=None,
                durum=None, min_guven=None, simdi=None):
    """İnanç deposunu filtreler. Tüm filtreler opsiyonel, VE ile birleşir.

    anahtar: konu/dosya/icerik içinde geçen metin (buyuk-kucuk duyarsız).
    """
    inanclar = inanclari_topla(defter_dir, simdi=simdi)

    a = (anahtar or "").lower()
    sonuc = []
    for i in inanclar:
        if a and a not in (i["konu"] + " " + i["dosya"] + " "
                           + i["icerik"]).lower():
            continue
        if kim and i["kim"].lower() != kim.lower():
            continue
        if tip and i["omur"].lower() != tip.lower():
            continue
        if kaynak and kaynak.lower() not in i["kaynak"].lower():
            continue
        if durum and i["durum"] != durum:
            continue
        if min_guven is not None and i["guven"] < min_guven:
            continue
        sonuc.append(i)
    return sonuc


def dunya_ozet(defter_dir, simdi=None):
    """İnsan-okur dünya özeti: kaç taze/bayat, ortalama güven."""
    inanclar = inanclari_topla(defter_dir, simdi=simdi)
    if not inanclar:
        return "Dünya modeli boş (defterde kayıt yok)."

    taze = sum(1 for i in inanclar if i["durum"] == "taze")
    bayat = len(inanclar) - taze
    ort_guven = round(sum(i["guven"] for i in inanclar) / len(inanclar), 2)

    satirlar = [
        "Dünya modeli: %d inanç (%d taze, %d bayat), ort. güven %s"
        % (len(inanclar), taze, bayat, ort_guven)]
    dusuk = [i for i in inanclar if i["durum"] == "bayat"][:5]
    for i in dusuk:
        satirlar.append("- BAYAT: %s (%s)" % (i["dosya"], i["konu"]))
    return "\n".join(satirlar)
