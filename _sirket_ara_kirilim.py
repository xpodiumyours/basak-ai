"""_sirket_ara_kirilim.py — sirket_ara'nın 9-11 saniyesi NEREDE gidiyor?

Ölçüm amacı: daraltma yapmadan önce kırılımı bilmek. Varsayım yazıp
test etmek yasak; burada yalnız ölçülür.

Kirilim:
  1. `tedarikci_coz`        — bilinen tedarikçi ipucu (yerel sözlük)
  2. `firma_bul`             — ürün çözümleyici (ağ)
  3. `web_search`            — arama (ağ)
  4. `kurum_sayfasi_oku`     — **aday sayfaları teker teker** (ağ)
     -> her aday için ayrı süre; kaç aday okundu?
  5. alan çıkarma            — yerel

Kosum: python _sirket_ara_kirilim.py [marka]
"""

import json
import logging
import statistics
import sys
import time

sys.path.insert(0, ".")

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.WARNING)

MARKA = sys.argv[1] if len(sys.argv) > 1 else "Trendyol"
TEKRAR = 3


def _zamanla(ad, islev, *a, **kw):
    """Tek cagri; (sure, sonuc) doner."""
    t0 = time.perf_counter()
    try:
        sonuc = islev(*a, **kw)
    except Exception as e:
        return time.perf_counter() - t0, {"error": "%s: %s" % (
            type(e).__name__, str(e)[:100])}
    return time.perf_counter() - t0, sonuc


def kirilim(marka):
    import tools.katalog as k
    from tools import web_search as ws

    satir = []

    def ekle(ad, sn, not_=""):
        satir.append({"asama": ad, "sn": round(sn, 3), "not": not_})

    # 1) tedarikci_coz (yerel) — (kayit, ad) tuple doner
    sn, _cift = _zamanla("tedarikci_coz", k.tedarikci_coz, marka)
    kayit, cozulen_ad = _cift if isinstance(_cift, tuple) else (None, marka)
    kayit = kayit or {}
    ekle("tedarikci_coz", sn, "yerel sozluk: %s"
         % (kayit.get("site") or "yok"))

    cozulen_ad = cozulen_ad or marka
    site = kayit.get("site", "")

    # 2) firma_bul (ağ) — site yoksa devreye girer
    firma_adaylari = []
    if not site:
        try:
            from tools import product_resolver
            sn, firma_adaylari = _zamanla(
                "firma_bul", product_resolver.firma_bul,
                {"marka": marka, "kod": "", "varyantlar": []})
            ekle("firma_bul", sn, "%d firma adayi" % len(firma_adaylari or []))
        except Exception as e:
            ekle("firma_bul", 0.0, "HATA %s" % e)

    # 3) aday listesi
    adaylar = []
    if site:
        adaylar.extend(k._sirket_iletisim_yollari(site))
    else:
        for firma in (firma_adaylari or []):
            fs = firma.get("site") or ""
            if fs:
                adaylar.extend(k._sirket_iletisim_yollari(
                    fs.replace("https://", "").replace("http://", "")))

    arama_sn = 0.0
    if not adaylar:
        sn, arama = _zamanla("web_search", ws.web_search,
                             "%s iletişim adres telefon üretici resmi site"
                             % cozulen_ad)
        arama_sn = sn
        ekle("web_search", sn, "arama sonrasi aday listesine gecilir")
        for adres in k._URL_RE.findall(arama.get("result", "")):
            try:
                from urllib.parse import urlparse as _coz
                host = (_coz(adres).hostname or "").lower()
            except ValueError:
                continue
            if any(host.endswith(h) for h in k._SOSYAL_HOST):
                continue
            temel = "%s://%s" % (_coz(adres).scheme, host)
            if temel not in adaylar:
                adaylar.append(temel)
            if len(adaylar) >= k._SIRKET_SITE_TAVANI:
                break

    marka_anahtari = k._marka_anahtari(cozulen_ad)
    okunacak = k._sirket_aday_sirasi(adaylar, marka_anahtari)

    # 4) ADAY SAYFALARI — en pahalı kısım
    sayfa_sureleri = []
    for i, aday in enumerate(okunacak):
        sn, okuma = _zamanla("sayfa[%d]" % (i + 1), ws.kurum_sayfasi_oku, aday)
        hata = bool(okuma.get("error"))
        skor = ""
        try:
            okunan = json.loads(okuma.get("result") or "{}")
            metin = str(okunan.get("metin") or "")
            skor = "skor=%d uyuyor=%s" % (
                k._sirket_sayfa_skor(metin),
                k._sayfa_markaya_ait(marka_anahtari, aday, okunan))
        except (TypeError, ValueError):
            # Bozuk JSON: sayfa yine de sayildi, yalniz skoru yazilamaz.
            # Probo oldugu icin sessizce gecmek dogru; iz yine de kaliyor
            # (sessiz-yutma kapisi bunu yasakliyor).
            logger.debug("sayfa JSON'u cozulemedi: %s", aday, exc_info=True)
        sayfa_sureleri.append(sn)
        ekle("sayfa[%d]" % (i + 1), sn,
             "%s %s" % (aday[:52], "HATA" if hata else skor))

    toplam = sum(s["sn"] for s in satir)
    return {
        "marka": marka,
        "asamalar": satir,
        "toplam_olcumlu_sn": round(toplam, 3),
        "aday_sayisi": len(okunacak),
        "arama_sn": round(arama_sn, 3),
        "sayfa_toplam_sn": round(sum(sayfa_sureleri), 3),
        "sayfa_ort_sn": round(statistics.mean(sayfa_sureleri), 3)
        if sayfa_sureleri else 0.0,
    }


def main():
    print("SIRKET_ARA KIRILIMI — marka=%r\n" % MARKA)
    raporlar = []
    for i in range(TEKRAR):
        print("--- kosu %d/%d" % (i + 1, TEKRAR))
        r = kirilim(MARKA)
        for s in r["asamalar"]:
            print("  %-16s %7.3f sn  %s" % (s["asama"], s["sn"], s["not"][:56]))
        print("  %-16s %7.3f sn  (toplam olcumlu)"
              % ("TOPLAM", r["toplam_olcumlu_sn"]))
        print("  aday sayisi=%d  sayfa ort=%s sn"
              % (r["aday_sayisi"], r["sayfa_ort_sn"]))
        raporlar.append(r)
        print()

    ort = statistics.mean(r["toplam_olcumlu_sn"] for r in raporlar)
    ortalama_aday = statistics.mean(r["aday_sayisi"] for r in raporlar)
    ortalama_sayfa = statistics.mean(r["sayfa_toplam_sn"] for r in raporlar)
    print("=" * 66)
    print("MARKA=%s | kosu ort=%s sn | aday ort=%s | sayfa toplam ort=%s sn"
          % (MARKA, round(ort, 3), ortalama_aday, round(ortalama_sayfa, 3)))
    if ortalama_sayfa > 0:
        print("Sayfa okumanin toplam sure icindeki payi: %%%d"
              % round(ortalama_sayfa * 100 / max(ort, 0.001)))
    print("Tavan koyulmadi. Daraltma onerisi bu kirilimdan cikarilir.")

    with open("data/sirket-ara-kirilim.json", "w", encoding="utf-8") as f:
        json.dump(raporlar, f, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())