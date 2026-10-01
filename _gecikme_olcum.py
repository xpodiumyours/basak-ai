"""_gecikme_olcum.py — P1.4 gecikme bütçesi ÖLÇÜMÜ.

Amaç: süreleri **ölçmek**. Tavan koymak değil (AGENTS.md §0: tavan geri
gelmez; ölçülen sapma varsa kovulur).

Ne ölçülür:
  1. `konum_coz`   — harita zinciri (Photon -> open-meteo)
  2. `sayfa_oku`   — tek HTTP sayfa çekme
  3. `sirket_ara`  — arama + kurum sayfası okuma (en ağır araç)
  4. `mesaj_isle`  — sohbet turunun ÖLÇÜLEBİLEN kısmı

Sıcaklık ayrımı zorunlu: ilk çağrı DNS + TLS el sıkışması + bağlantı
havuzu soğuması içerir. Tek ölçüm bu yüzden "tipik süre" değildir.
Her iş 3 kez koşulur: ilk = SOĞUK, sonrakiler = SICAK.

Kosum: python _gecikme_olcum.py
"""

import json
import statistics
import sys
import time

sys.path.insert(0, ".")

TEKRAR = 3
# Gerçek, herkese açık, kararlı hedefler. Üretimde kullanılan yollar:
#   photon.komoot.io  -> tools/harita.py
#   turk.wikipedia.org -> sayfa_oku ölçümü (canlı araçla aynı yol)
HEDEF_SAYFA = "https://tr.wikipedia.org/wiki/Ba%C5%9Fak"
ORNEK_ADRES = "Moda, Kadikoy"
ORNEK_MARKA = "Trendyol"  # gerçek marka: sahte adresle "bulunamadi" ölçmek
                            # sahte bir yolun süresini ölçmek demek


def _olc(ad, islev, *a, **kw):
    """Bir işi TEKRAR kez koş, ilkini SOĞUK diye ayır."""
    sureler, sonuc, hata = [], None, None
    for i in range(TEKRAR):
        t0 = time.perf_counter()
        try:
            sonuc = islev(*a, **kw)
        except Exception as e:
            hata = "%s: %s" % (type(e).__name__, str(e)[:120])
            sonuc = None
        dt = time.perf_counter() - t0
        sureler.append(dt)
        print("    %s #%d %.3f sn%s"
              % (ad, i + 1, dt, "  <-- HATA" if hata else ""))
        if hata:
            break
    sicak = sureler[1:] or sureler
    kayit = {
        "ad": ad,
        "soğuk_sn": round(sureler[0], 3),
        "sicak_sn": [round(s, 3) for s in sicak],
        "sicak_ort_sn": round(statistics.mean(sicak), 3),
        "sicak_en_fazla_sn": round(max(sicak), 3),
        "hata": hata,
        "basarili": hata is None,
    }
    return kayit


def _ozet(kayit, sonuc):
    """Kısa sonuç özeti — kapsam ne kadar doldu?"""
    if sonuc is None:
        return "sonuc yok"
    if isinstance(sonuc, dict):
        if "error" in sonuc:
            return "error: %s" % str(sonuc["error"])[:70]
        if "kaynak" in sonuc:
            return "kaynak=%s aday=%s" % (
                sonuc.get("kaynak"), sonuc.get("aday_sayisi"))
        if "site" in sonuc:
            return "site=%s dogrulandi=%s" % (
                (sonuc.get("site") or "(yok)")[:40], sonuc.get("dogrulandi"))
        return "anahtarlar: %s" % ",".join(sorted(sonuc)[:5])
    return str(sonuc)[:60]


def main():
    from tools import calistir
    from tools.web_search import sayfa_oku
    from tools.harita import konum_coz
    from tools.katalog import sirket_ara

    print("P1.4 GECIKME OLCUMU — %d tekrar/is, ilk = soguk\n" % TEKRAR)
    rapor = {"tekrar": TEKRAR, "olcumler": [], "NOT": (
        "Bu ortamda saglayici anahtari YOK; model cagrilari olculmedi. "
        "Sadece ag katmani ve arac suresi olculdu.")}

    # ── 1. konum_coz ────────────────────────────────────────────────
    print("[1] konum_coz(%r)" % ORNEK_ADRES)
    r = _olc("konum_coz", konum_coz, ORNEK_ADRES)
    r["ozet"] = _ozet("konum_coz", konum_coz(ORNEK_ADRES))
    print("      ->", r["ozet"])
    rapor["olcumler"].append(r)

    # ── 2. sayfa_oku (doğrudan fonksiyon: dispatcher sarmalayıcısını
    #       ölçmemek için; JSON çevirme süresi ayrı) ──────────────────
    print("[2] sayfa_oku(%s)" % HEDEF_SAYFA[:48])
    r = _olc("sayfa_oku", sayfa_oku, HEDEF_SAYFA)
    # DİKKAT: sayfa_oku "result" doner, "icerik" DEGIL. Ilk olcumde
    # probun kendisi yanlis anahtari okuyup 0 karakter yazdi ve
    # tabloya yanlis bilgi girdi. Alan adi olculebilir olmali.
    _s = sayfa_oku(HEDEF_SAYFA)
    if isinstance(_s, dict) and "error" in _s:
        r["ozet"] = "error: %s" % str(_s["error"])[:60]
    else:
        r["ozet"] = "karakter=%d" % len(str(_s.get("result", "")))
    print("      ->", r["ozet"])
    rapor["olcumler"].append(r)

    # ── 3. sirket_ara (en ağır: arama + sayfa okuma) ────────────────
    print("[3] sirket_ara(%r)" % ORNEK_MARKA)
    r = _olc("sirket_ara", sirket_ara, ORNEK_MARKA)
    r["ozet"] = _ozet("sirket_ara", sirket_ara(ORNEK_MARKA))
    print("      ->", r["ozet"])
    rapor["olcumler"].append(r)

    # ── 4. sohbet turu: ÖLÇÜLEBİLEN kısım ──────────────────────────
    # Model cagrisi anahtarsiz yapilamaz. Olculebilen kisim:
    #   (a) hazirlik — bellek onbellegi + kimlik + gecmis baglami
    #   (b) arac dongusu YALNIZCA araç cagirmak isteyen, modele gitmeyen
    #       yol: dogrudan dispatcher uzerinden
    print("[4] sohbet turu — OLCULEBILEN kisimlar")
    r = _olc("hazirlik_belleg", _hazirlik_olc)
    r["ozet"] = "baglam hazirligi (model cagrisi YOK)"
    print("      ->", r["ozet"])
    rapor["olcumler"].append(r)

    # ── 5. dispatcher uzerinden tam araç zinciri ────────────────────
    # Model kararini simule etmek YASAK (sagat kabulu degil). Bu yuzden
    # burada yalniz TEK aracin dispatcher'dan gecisi olculur; uclu arac
    # zinciri model kararidir ve bu ortamda olculemez.
    print("[5] dispatcher: konum_coz (tek arac, model karari YOK)")
    r = _olc("dispatcher_konum_coz", calistir, "konum_coz",
             {"adres": ORNEK_ADRES})
    _d = calistir("konum_coz", {"adres": ORNEK_ADRES})
    try:
        import json as _json
        _i = _json.loads(_d.get("result", "{}"))
        r["ozet"] = "kaynak=%s aday=%s" % (_i.get("kaynak"),
                                          _i.get("aday_sayisi"))
    except Exception:
        r["ozet"] = "JSON donusu alinamadi"
    print("      ->", r["ozet"])
    rapor["olcumler"].append(r)

    _yaz(rapor)
    _tablo(rapor)
    return 0


def _hazirlik_olc():
    """Sohbet turunun model disi kismi: onbellek + kimlik baglami."""
    from chat import context as ctx
    from chat.kimlik import kullanici_kur
    kullanici_kur("casper")
    ctx.init_cache()
    return ctx.gecmis_pencere([{"role": "user", "content": "merhaba"}])


def _yaz(rapor):
    import os
    yol = os.path.join("data", "gecikme-raporu.json")
    try:
        os.makedirs("data", exist_ok=True)
        with open(yol, "w", encoding="utf-8") as f:
            json.dump(rapor, f, ensure_ascii=False, indent=2)
        print("\nrapor yazildi: %s" % yol)
    except OSError as e:
        print("rapor YAZILAMADI: %s" % e)


def _tablo(rapor):
    print("\n%-22s %8s %10s %10s  %s"
          % ("IS", "SOGUK", "SICAK-ORT", "SICAK-MAX", "DURUM"))
    print("-" * 74)
    for r in rapor["olcumler"]:
        durum = "hata: %s" % r["hata"] if r["hata"] else r.get("ozet", "")
        print("%-22s %7.3fs %9.3fs %9.3fs  %s"
              % (r["ad"], r["soğuk_sn"], r["sicak_ort_sn"],
                 r["sicak_en_fazla_sn"], durum[:28]))
    print("\nNOT: %s" % rapor["NOT"])
    print("Tavan KOYULMADI. Bu bir olcum tablosudur, butce degil.")


if __name__ == "__main__":
    sys.exit(main())