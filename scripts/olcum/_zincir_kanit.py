"""_zincir_kanit.py — Harita zincirinin (Z4) canlı kabul probu.

Zincir: `konum_coz` → `sube_bul` → `harita_goster` — üçü de AYRI AYRI
çalışıyordu; bu probu **tek çağrıda** zincirin gerçekten yürüdüğünü
ölçer.

Gerçek dispatcher (`tools.calistir`) + gerçek ağ (Photon / Overpass).
Simülasyon yok: sahte yanıt enjekte edilmez, uydurma çıktı kabul
edilmez. Hata durumunda hata metni de kayda geçer.

Çalıştırma: `python3 scripts/olcum/_zincir_kanit.py`
Çıktı: `_zincir_kanit_sonuc.json` (kök dizin)
"""

import json
import pathlib
import sys
import time

KOK = pathlib.Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

from tools import calistir  # noqa: E402

# Gerçek zincir sıraları: adres merkezli, koordinat merkezli, arama modu.
SENARYOLAR = [
    {"ad": "adres merkezi (Photon) + yol modu",
     "arac": {"marka": "BİM", "konum": "Kadıköy Moda, İstanbul",
              "yaricap_km": 3, "adet": 3, "mod": "yol"}},
    {"ad": "koordinat merkezi + arama modu",
     "arac": {"marka": "Migros", "konum": "41.0111, 29.0254",
              "yaricap_km": 2, "adet": 2, "mod": "ara"}},
    {"ad": "uydurma marka (sonuç 0 — hata DEĞİLDİR)",
     "arac": {"marka": "zzz bilinmeyen marka zzz",
              "konum": "41.0111, 29.0254", "yaricap_km": 1, "adet": 3}},
]

KAYIT = []


def zinciri_calistir(ad, arac):
    """Tek çağrı: dispatcher -> gerçek ağ -> zincir çıktısı."""
    bas = time.time()
    sonuc = calistir("harita_dedektif", arac)
    sure = round(time.time() - bas, 1)
    kayit = {"senaryo": ad, "arac": arac, "sure_sn": sure}
    if "error" in sonuc:
        kayit["hata"] = sonuc["error"]
    else:
        veri = json.loads(sonuc["result"])
        kayit.update({
            "zincir": veri["zincir"],
            "adimlar": veri.get("adimlar", []),
            "merkez": veri["merkez"],
            "mod": veri["mod"],
            "yaricap_km": veri["yaricap_km"],
            "veri_kaynagi": veri["veri_kaynagi"],
            "sube_sayisi": veri["sube_sayisi"],
            "not": veri.get("not", ""),
            "atif": veri["atif"],
            "denenen_hatlar": veri["denenen_hatlar"],
            "subeler": [{
                "ad": s["ad"], "mesafe_km": s["mesafe_km"],
                "adres": s["adres"], "telefon": s.get("telefon", ""),
                "baglanti": s["baglanti"],
            } for s in veri["subeler"]],
            "merkez_baglanti": veri["baglantilar"]["merkez"],
        })
    KAYIT.append(kayit)
    return kayit


for _senaryo in SENARYOLAR:
    _kayit = zinciri_calistir(_senaryo["ad"], _senaryo["arac"])
    print("=" * 70)
    print(_kayit["senaryo"], "| süre:", _kayit["sure_sn"], "sn")
    if "hata" in _kayit:
        print("  HATA:", _kayit["hata"][:400])
        continue
    print("  zincir:", " -> ".join(_kayit["zincir"]))
    for _a in _kayit.get("adimlar", []):
        print("   adim:", _a["ad"], "|", _a["durum"], "|",
              _a["baslik"], "|", _a["ozet"])
    print("  merkez:", _kayit["merkez"])
    print("  veri kaynağı:", _kayit["veri_kaynagi"],
          "| şube:", _kayit["sube_sayisi"])
    for _s in _kayit["subeler"]:
        print("   -", _s["ad"], "|", _s["mesafe_km"], "km |",
              (_s["adres"] or "-")[:60])
        print("     ", _s["baglanti"][:110])
    if _kayit["not"]:
        print("  not:", _kayit["not"][:200])
    for _h in _kayit["denenen_hatlar"]:
        print("   hat:", _h.get("ayna", "?"), "->", _h.get("durum"),
              _h.get("hata", "")[:80])

cikti = KOK / "_zincir_kanit_sonuc.json"
cikti.write_text(json.dumps(KAYIT, ensure_ascii=False, indent=2),
                 encoding="utf-8")
print("\nKAYIT:", cikti)
