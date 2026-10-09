# -*- coding: utf-8 -*-
"""scripts/olcum/_ilk_token_olcum.py — ilk-token (TTFT) olcum tabani.

Kullanım: python scripts/olcum/_ilk_token_olcum.py [taban_url] [senaryolar]

Ne ölçer (her tur için) — /api/sohbet NDJSON canli akisi uzerinden:
  - ilk_olay_sn: ilk olaya kadar (istek kabul + "dusunuyor" belirtisi)
  - ilk_icerik_sn: ilk icerik ilerlemesine kadar (parca/toolStatus/bitir) —
    kullanicinin GERCEKTEN gordugu ilk hareket (asıl TTFT)
  - toplam_sn (cevap bitene kadar)
  - failover sayisi: "durum" olaylarindaki atlama bildirimleri (B isi)
  - kaynak (cevap veren beyin), bos cevap var mi

Çıktı: _ilk_token_sonuc.json + özet. Sır yok, yalnız ölçüm.
"""

import http.cookiejar
import json
import os
import sys
import time
import urllib.request

TABAN = (sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8123")
KOK = os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__))))
CIKTI = os.path.join(KOK, "scripts", "olcum", "_ilk_token_sonuc.json")

SENARYOLAR = [
    ("3_yuzde", "%15'i 200 olan ne kadar?"),
    ("2_base64", "Bu metni Base64'e çevir: merhaba dünya"),
    ("1_sha256", "freetools.org'da SHA-256 üret: merhaba"),
]


def _tur(metin):
    kavanoz = http.cookiejar.CookieJar()
    acar = urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(kavanoz))
    govde = json.dumps({}, ensure_ascii=False).encode("utf-8")
    istek = urllib.request.Request(
        TABAN + "/api/kimlik", data=govde,
        headers={"Content-Type": "application/json",
                 "Accept": "application/json"})
    acar.open(istek, timeout=60).read()
    return acar


def _olcum(acar, metin):
    govde = json.dumps({"metin": metin}, ensure_ascii=False).encode("utf-8")
    istek = urllib.request.Request(
        TABAN + "/api/sohbet", data=govde,
        headers={"Content-Type": "application/json",
                 "Accept": "application/x-ndjson"})
    t0 = time.monotonic()
    ilk_olay = None
    ilk_icerik = None
    olaylar = []
    yanit = acar.open(istek, timeout=300)
    try:
        for satir in yanit:
            simdi = round(time.monotonic() - t0, 2)
            metin_satir = satir.decode("utf-8", "replace").strip()
            if not metin_satir:
                continue
            try:
                olay = json.loads(metin_satir)
            except ValueError:
                continue
            if ilk_olay is None:
                ilk_olay = simdi
            if ilk_icerik is None and olay.get("tur") in (
                    "parca", "toolStatus", "bitir", "error"):
                ilk_icerik = simdi
            olaylar.append(olay)
    finally:
        toplam = round(time.monotonic() - t0, 2)
        yanit.close()

    failover = [o.get("metin", "") for o in olaylar
                if o.get("tur") == "durum"]
    cevap = ""
    kaynak = ""
    for o in olaylar:
        if o.get("tur") == "bitir":
            cevap = str(o.get("cevap") or "")
            kaynak = str(o.get("kaynak") or "")
    return {
        "ilk_olay_sn": ilk_olay,
        "ttft_sn": ilk_icerik,
        "toplam_sn": toplam,
        "failover_sayisi": len(failover),
        "failoverlar": failover,
        "kaynak": kaynak,
        "bos_cevap": not cevap.strip(),
    }


def main():
    secili = None
    if len(sys.argv) > 2 and sys.argv[2].strip():
        secili = {a.strip() for a in sys.argv[2].split(",") if a.strip()}
    sonuc = {"taban": TABAN, "zaman": time.strftime("%Y-%m-%d %H:%M:%S"),
             "turlar": []}
    for ad, metin in SENARYOLAR:
        if secili and ad not in secili:
            continue
        acar = _tur(metin)
        try:
            k = _olcum(acar, metin)
        except Exception as e:
            k = {"hata": str(e)[:200]}
        k["ad"] = ad
        sonuc["turlar"].append(k)
        print("%-10s ilkolay=%-6s ilkicerik=%-6s toplam=%-6s "
              "failover=%-2s bos=%s %s" % (
                  ad, k.get("ilk_olay_sn"), k.get("ttft_sn"),
                  k.get("toplam_sn"),
                  k.get("failover_sayisi"), k.get("bos_cevap"),
                  "HATA:" + k["hata"] if "hata" in k else ""))

    turlar = [t for t in sonuc["turlar"] if t.get("ttft_sn") is not None]
    if turlar:
        ttftler = sorted(t["ttft_sn"] for t in turlar)
        ort = round(sum(ttftler) / len(ttftler), 2)
        medyan = ttftler[len(ttftler) // 2]
        sonuc["ozet"] = {
            "tur": len(turlar),
            "ttft_ort": ort,
            "ttft_medyan": medyan,
            "failover_toplam": sum(t["failover_sayisi"] for t in turlar),
        }
        print("OZET: ilk-icerik ttft ort=%s medyan=%s | failover toplam=%s"
              % (ort, medyan, sonuc["ozet"]["failover_toplam"]))
    with open(CIKTI, "w", encoding="utf-8") as f:
        json.dump(sonuc, f, ensure_ascii=False, indent=2)
    print("SONUC:", CIKTI)
    return 0


if __name__ == "__main__":
    sys.exit(main())
