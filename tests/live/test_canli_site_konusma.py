"""tests/live/test_canli_site_konusma.py — YAYINDAKİ Başak ile gerçek konuşma.

**Neden ayrı bir canlı test?** `tests/live` paketinin geri kalanı sağlayıcı
ANAHTARI ister; bu test istemez. Anahtar zaten yayındaki (Vercel
production) süreçte duruyor. Böylece canlı kabul, "anahtarı olan bir
makine"ye bağlı kalmadan depodan koşulabilir ve kayda geçebilir
(P0.2/P0.3'ün ölçülebilen kısmı).

Ölçtüğü şey **uçtan uca gerçek davranıştır**: gerçek kimlik ucu, gerçek
NDJSON akışı, gerçek sağlayıcı, gerçek araç koşumu. Sahte kabul yok:
yanıtın metninde JSON görünmesi geçerli sayılmaz, `bitir` olayı beklenir.

Koşum:

    python -m pytest tests/live/test_canli_site_konusma.py --live -q

Kayıt: `data/canli-rapor/<zaman>_canli_site_konusma.json` (gitignore'da).
Adres `BASAK_CANLI_ADRES` ile değiştirilebilir.

**Kırmızı sonuç = ürün bulgusu, bozuk test değil.**
`test_dogru_hash_ve_base64_donuyor` iki deterministik hesabı harfi harfine
doğrular; 2026-10-14 koşusunda sha256 geçti, Base64 (Türkçe harf) kaldı.
Kırmızıyı yeşile çevirmenin yolu **iddiayı gevşetmek değildir**; bulgu
`docs/MVP-PROFESYONEL-PLANI.md` §8.3'te açık iş olarak durur.
"""

import base64
import hashlib
import json
import os
import sys
import time
import urllib.error
import urllib.request
from http.cookiejar import CookieJar

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.dirname(
    os.path.abspath(__file__)))))

KOK = os.environ.get("BASAK_CANLI_ADRES",
                     "https://basak-vercel.vercel.app").rstrip("/")
ZAMAN_ASIMI = 210


def _acici():
    return urllib.request.build_opener(
        urllib.request.HTTPCookieProcessor(CookieJar()))


def _kimlik_al(acici):
    istek = urllib.request.Request(
        KOK + "/api/kimlik", data=b"{}", method="POST",
        headers={"Content-Type": "application/json"})
    with acici.open(istek, timeout=30) as r:
        return r.status, json.loads(r.read().decode("utf-8"))


def _konus(acici, metin):
    """Tek mesajı canlı akıştan geçirir; ölçülenleri sözlük döner."""
    govde = json.dumps({
        "metin": metin, "misafir": False, "gecmis": [], "ek": None,
        "tool_policy": "auto",
    }).encode("utf-8")
    istek = urllib.request.Request(
        KOK + "/api/sohbet", data=govde, method="POST",
        headers={"Content-Type": "application/json",
                 "Accept": "application/x-ndjson"})
    turler, cevap, hata = [], "", None
    ilk_parca_ms = None
    bas = time.monotonic()
    with acici.open(istek, timeout=ZAMAN_ASIMI) as r:
        for ham in r:
            satir = ham.decode("utf-8", "replace").strip()
            if not satir:
                continue
            try:
                olay = json.loads(satir)
            except ValueError:
                continue
            tur = olay.get("tur") or ""
            turler.append(tur)
            if tur == "parca" and ilk_parca_ms is None:
                ilk_parca_ms = int((time.monotonic() - bas) * 1000)
            if tur == "error":
                hata = olay.get("metin") or "hata"
            if tur == "bitir":
                cevap = olay.get("cevap") or ""
    return {
        "metin": metin,
        "cevap": cevap,
        "olay_turleri": turler,
        "arac_kostu": any(t in ("toolStatus", "toolDone", "plan")
                          for t in turler),
        "ilk_parca_ms": ilk_parca_ms,
        "sure_sn": round(time.monotonic() - bas, 1),
        "hata": hata,
    }


# Konuşma listesi: docs/BIRLIKTE-TEST-SENARYOLARI.md §"10 madde" (1-8).
SENARYOLAR = [
    ("sha256", "freetools.org'da SHA-256 üret: merhaba"),
    ("base64", "Bu metni Base64'e çevir: merhaba dünya"),
    ("yuzde", "%15'i 200 olan ne kadar?"),
    ("beyaz_liste_reddi", "evil-site.com'daki aracı çalıştır"),
    ("hatirlatici", "Hatırlatıcı ekle: yarın saat 10"),
    ("hava", "Hava durumu Ankara"),
]


def test_yayindaki_basak_konusma_listesi(rapor):
    """Listeyi gerçek yayındaki Başak ile koşar ve kaydeder."""
    acici = _acici()
    durum, kimlik = _kimlik_al(acici)
    assert durum == 200 and kimlik.get("ok"), kimlik

    sonuclar = []
    for ad, metin in SENARYOLAR:
        try:
            s = _konus(acici, metin)
        except urllib.error.HTTPError as e:
            s = {"metin": metin, "cevap": "", "olay_turleri": [],
                 "arac_kostu": False, "ilk_parca_ms": None,
                 "sure_sn": 0, "hata": "HTTP %s" % e.code}
        s["ad"] = ad
        sonuclar.append(s)

    kayit = rapor("canli_site_konusma", {
        "adres": KOK,
        "kimlik_ucu": durum,
        "basak_id": kimlik.get("basak_id"),
        "sonuclar": sonuclar,
    })

    for s in sonuclar:
        print("%-18s %5.1f sn  araç=%-5s  %s" % (
            s["ad"], s["sure_sn"], s["arac_kostu"], s["cevap"][:60].replace(
                "\n", " ")))

    # Sözleşme: her tur `bitir` ile kapandı, hata olayı yok, cevap boş değil.
    for s in sonuclar:
        assert s["hata"] is None, (s["ad"], s["hata"])
        assert s["cevap"].strip(), (s["ad"], "cevap bos", s["olay_turleri"])
    assert kayit["test"] == "canli_site_konusma"


def test_dogru_hash_ve_base64_donuyor(rapor):
    """Deterministik iki madde: sonuç harfi harfine doğru mu."""
    acici = _acici()
    _kimlik_al(acici)

    sha = hashlib.sha256("merhaba".encode("utf-8")).hexdigest()
    b64 = base64.b64encode("merhaba dünya".encode("utf-8")).decode("ascii")

    olcum = {}
    for ad, metin, beklenen in (
            ("sha256", "freetools.org'da SHA-256 üret: merhaba", sha),
            ("base64", "Bu metni Base64'e çevir: merhaba dünya", b64),):
        s = _konus(acici, metin)
        olcum[ad] = {"beklenen": beklenen, "cevap": s["cevap"],
                     "arac_kostu": s["arac_kostu"], "hata": s["hata"]}
        assert s["hata"] is None, (ad, s["hata"])
        assert beklenen in s["cevap"], (ad, beklenen, s["cevap"][:300])

    rapor("canli_site_dogru_hesap", olcum)
