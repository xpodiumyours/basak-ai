"""_sirket_ara_erken_cikis.py — erken çıkış SONUCU DEĞİŞTİRİYOR MU?

Soru: aday sayfaları sırayla okunuyor ve `uyuyor=True` (sayfa markaya
ait) bulunduktan SONRA da kalan adaylar okunuyor. Erken çıkış eklemek
sureyi kısaltır — ama **kart aynı kalır mı?**

Yöntem (varsayım değil ölçüm): aynı marka icin iki dEGERLENDIRME
yapilir, ayni aday sirasi ve ayni ayni sayfa okuma sonuclari uzerinde:
  A) mevcut kural — tum adaylar okunur, en iyi sayfa secilir
  B) erken cikis  — `uyuyor=True` ve gercek varsa dur
Kartlar karsilastirilir. Ayni ise erken cikis guvenlidir.

Kosum: python scripts/olcum/_sirket_ara_erken_cikis.py [marka ...]
"""

import json
import pathlib
import sys
import time

# Depo kokunu __file__ uzerinden bul; calisma dizinine bagimli degildir.
KOK = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

MARKALAR = sys.argv[1:] or ["Trendyol", "Getir", "Arçelik"]


def _adaylar(marka):
    import tools.katalog as k
    kayit, cozulen_ad = k.tedarikci_coz(marka)
    kayit = kayit or {}
    site = kayit.get("site", "")
    adaylar = []
    if site:
        adaylar.extend(k._sirket_iletisim_yollari(site))
    else:
        from tools import product_resolver
        for firma in product_resolver.firma_bul(
                {"marka": marka, "kod": "", "varyantlar": []}) or []:
            fs = firma.get("site") or ""
            if fs:
                adaylar.extend(k._sirket_iletisim_yollari(
                    fs.replace("https://", "").replace("http://", "")))
    anahtar = k._marka_anahtari(cozulen_ad)
    return cozulen_ad, k._sirket_aday_sirasi(adaylar, anahtar)


def _degerlendir(marka, erken_cikis):
    """Mevcut algoritmayı taklit et; tek fark: erken çıkış."""
    import tools.katalog as k
    from tools import web_search as ws

    cozulen_ad, okunacak = _adaylar(marka)
    if not okunacak:
        return {"hata": "aday yok", "okunan": 0}

    anahtar = k._marka_anahtari(cozulen_ad)
    en_metin, en_gercekler, en_skor, en_site, en_uyuyor = "", [], 0, "", False
    okunan, sure = [], 0.0

    for aday in okunacak:
        t0 = time.perf_counter()
        okuma = ws.kurum_sayfasi_oku(aday)
        sure += time.perf_counter() - t0
        okunan.append(aday)
        if okuma.get("error"):
            continue
        try:
            okunan_veri = json.loads(okuma.get("result") or "{}")
        except (TypeError, ValueError):
            continue
        metin = str(okunan_veri.get("metin") or "")
        skor = k._sirket_sayfa_skor(metin)
        uyuyor = k._sayfa_markaya_ait(anahtar, aday, okunan_veri)
        daha_iyi = ((not en_site) or (uyuyor and not en_uyuyor)
                    or (uyuyor == en_uyuyor and skor > en_skor))
        if daha_iyi:
            en_metin, en_skor, en_site, en_uyuyor = metin, skor, aday, uyuyor
            en_gercekler = [g for g in (okunan_veri.get("gercekler") or [])
                            if isinstance(g, dict)
                            and k._gercek_markaya_ait(anahtar, g)]
        # ── ERKEN ÇIKIŞ: markaya ait sayfa + yapısal gerçek bulunduysa
        #    daha iyisi olamaz (skor yüksek olsa bile sayfa BAŞKA kuruma ait).
        if erken_cikis and uyuyor and en_gercekler:
            break

    if not en_site:
        return {"hata": "okunabilir sayfa yok", "okunan": len(okunan),
                "sure": round(sure, 3)}
    if en_uyuyor:
        telefon, eposta, adresler, unvan, vergi = k._sirket_alanlari(
            en_metin[:6000], en_gercekler)
        dogrulandi = True
    else:
        telefon, eposta, adresler, unvan, vergi = [], [], [], "", ""
        dogrulandi = False
    return {
        "site": en_site, "dogrulandi": dogrulandi,
        "telefon": telefon, "eposta": eposta, "adresler": adresler,
        "unvan": unvan, "vergi_no": vergi,
        "okunan": len(okunan), "sure": round(sure, 3),
        "okunanlar": okunan,
    }


def _ayni_kart(a, b):
    """Kartin dolu alanlari ayni mi? (okunulan aday sayisi degil)"""
    for alan in ("site", "dogrulandi", "telefon", "eposta", "adresler",
                 "unvan", "vergi_no"):
        if a.get(alan) != b.get(alan):
            return False, alan
    return True, ""


def main():
    toplam_ayni = toplam = 0
    tasarruf_sayfa = tasarruf_sn = 0.0
    raporlar = []

    for marka in MARKALAR:
        print("\n=== %s" % marka)
        a = _degerlendir(marka, erken_cikis=False)
        b = _degerlendir(marka, erken_cikis=True)
        ayni, farkli_alan = _ayni_kart(a, b)
        toplam += 1
        toplam_ayni += 1 if ayni else 0
        print("  A) mevcut : %d sayfa, %s sn, site=%s dogrulandi=%s"
              % (a.get("okunan", 0), a.get("sure"), a.get("site"),
                 a.get("dogrulandi")))
        print("  B) erken  : %d sayfa, %s sn, site=%s dogrulandi=%s"
              % (b.get("okunan", 0), b.get("sure"), b.get("site"),
                 b.get("dogrulandi")))
        print("  KART AYNI MI: %s%s" % ("EVET" if ayni else "HAYIR",
                                        "" if ayni else " (%s)" % farkli_alan))
        if not ayni:
            print("     A alanlari:", json.dumps(
                {k: a.get(k) for k in ("site", "dogrulandi", "telefon",
                                       "eposta")}, ensure_ascii=False)[:150])
            print("     B alanlari:", json.dumps(
                {k: b.get(k) for k in ("site", "dogrulandi", "telefon",
                                       "eposta")}, ensure_ascii=False)[:150])
        tasarruf_sayfa += (a.get("okunan", 0) - b.get("okunan", 0))
        if isinstance(a.get("sure"), float) and isinstance(b.get("sure"), float):
            tasarruf_sn += a["sure"] - b["sure"]
        raporlar.append({"marka": marka, "A": a, "B": b, "ayni": ayni})

    print("\n" + "=" * 66)
    print("Kart ayni: %d/%d marka" % (toplam_ayni, toplam))
    print("Sayfa tasarrufu: %d adet, %.2f sn (toplam)"
          % (tasarruf_sayfa, tasarruf_sn))
    print("Tavan koyulmadi; bu bir olcum.")

    # Cikti depo kokundaki data/ altina (.gitignore yollari kok gorelidir).
    with open(KOK / "data" / "sirket-ara-erken-cikis.json", "w",
              encoding="utf-8") as f:
        json.dump(raporlar, f, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())