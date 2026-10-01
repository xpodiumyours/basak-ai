"""_erken_cikis_dondurulmus.py — erken çıkış ELMA ELMA testi.

Önceki ölçümün hatası (2026-10-01, dürüst kayıt): `_sirket_ara_erken_cikis.py`
her koşuda `firma_bul`'u YENIDEN çağırıyordu; arama sonuçları koşular
arası değiştiği için A ve B farklı aday listeleriyle çalışmıştı. Yani
"erken çıkış kartı bozdu" sonucu karşılaştırma kusuruydu.

Burada aday listesi **bir kez dondurulur**, iki değerlendirme de aynı
sayfaları okur. A) mevcut kural, B) erken çıkış.

Kosum: python _erken_cikis_dondurulmus.py
"""

import json
import sys
import time

sys.path.insert(0, ".")

MARKA = "Trendyol"


def _kisa(kart):
    """Kartin dolu alanlari — okunulan aday sayisi degil."""
    if not isinstance(kart, dict):
        return {"error": str(kart)[:60]}
    return {a: kart.get(a) for a in
            ("site", "dogrulandi", "telefonlar", "eposta", "adresler",
             "unvan", "vergi_no")}


def main():
    import tools.katalog as k
    from tools import web_search as ws

    kayit, ad = k.tedarikci_coz(MARKA)
    kayit = kayit or {}
    site = kayit.get("site", "")
    adaylar = []
    if site:
        adaylar.extend(k._sirket_iletisim_yollari(site))
    else:
        from tools import product_resolver
        for firma in product_resolver.firma_bul(
                {"marka": MARKA, "kod": "", "varyantlar": []}) or []:
            fs = firma.get("site") or ""
            if fs:
                adaylar.extend(k._sirket_iletisim_yollari(
                    fs.replace("https://", "").replace("http://", "")))

    anahtar = k._marka_anahtari(ad or MARKA)
    okunacak = k._sirket_aday_sirasi(adaylar, anahtar)

    print("MARKA=%r  aday=%d" % (MARKA, len(okunacak)))
    print("DONDURULMUŞ ADAY LİSTESİ (iki koşum da bunu okur):")
    for a in okunacak:
        print("   ", a)
    if not okunacak:
        print("ADAY YOK — arama bos dondu, test edilemez.")
        return 1

    # Sayfaları BİR KEZ oku; iki kural da AYNI sonuçları kullansın.
    print("\nSayfalar bir kez okunuyor...")
    t0 = time.perf_counter()
    okumalar = k._sirket_sayfalari_paralel(ws, okunacak)
    okuma_sn = time.perf_counter() - t0
    print("  okuma suresi: %.3f sn (%d sayfa)" % (okuma_sn, len(okumalar)))

    def degerlendir(erken_cikis):
        en_metin, en_gercekler, en_skor, en_site, en_uyuyor = "", [], 0, "", False
        for aday, okuma in zip(okunacak, okumalar):
            if not okuma or okuma.get("error"):
                continue
            try:
                okunan = json.loads(okuma.get("result") or "{}")
            except (TypeError, ValueError):
                continue
            metin = str(okunan.get("metin") or "")
            skor = k._sirket_sayfa_skor(metin)
            uyuyor = k._sayfa_markaya_ait(anahtar, aday, okunan)
            daha_iyi = ((not en_site) or (uyuyor and not en_uyuyor)
                        or (uyuyor == en_uyuyor and skor > en_skor))
            if daha_iyi:
                en_metin, en_skor, en_site, en_uyuyor = metin, skor, aday, uyuyor
                en_gercekler = [
                    g for g in (okunan.get("gercekler") or [])
                    if isinstance(g, dict) and k._gercek_markaya_ait(anahtar, g)]
            if erken_cikis and uyuyor and en_gercekler:
                break
        if not en_site:
            return {"error": "okunabilir sayfa yok"}
        if en_uyuyor:
            t, e, adr, uv, vn = k._sirket_alanlari(en_metin[:6000], en_gercekler)
            return {"site": en_site, "dogrulandi": True, "telefonlar": t,
                    "eposta": e, "adresler": adr, "unvan": uv, "vergi_no": vn}
        return {"site": en_site, "dogrulandi": False, "telefonlar": [],
                "eposta": [], "adresler": [], "unvan": "", "vergi_no": ""}

    a = degerlendir(False)
    b = degerlendir(True)
    ka, kb = _kisa(a), _kisa(b)
    ayni = ka == kb
    print("\nA) mevcut :", json.dumps(ka, ensure_ascii=False)[:190])
    print("B) erken  :", json.dumps(kb, ensure_ascii=False)[:190])
    print("\nKART AYNI MI: %s" % ("EVET" if ayni else "HAYIR"))
    if not ayni:
        for alan in ka:
            if ka.get(alan) != kb.get(alan):
                print("   FARK %s: A=%r B=%r" % (alan, ka.get(alan), kb.get(alan)))
    with open("data/erken-cikis-dondurulmus.json", "w",
              encoding="utf-8") as f:
        json.dump({"marka": MARKA, "adaylar": okunacak, "A": ka, "B": kb,
                   "ayni": ayni, "okuma_sn": round(okuma_sn, 3)},
                  f, ensure_ascii=False, indent=2)
    return 0


if __name__ == "__main__":
    sys.exit(main())