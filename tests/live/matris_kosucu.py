"""tests/live/matris_kosucu.py — DUZEY 2: dinamik GERCEK canli hucre matrisi.

Kabul plani (knowledge/kabul-plani-web-gate.md, DUZEY 2):
- Her hucreye yazilir: saglayici, arac, tur-1 native mi, tur-2 devam mi,
  sure, model, hata. Bicim: data/kabul-matrisi.json (git-disi).
- Kapsam (KAPSAM): yalniz ELDE ANAHTARI OLAN saglayicilar (2026-09-22
  Casper karari). Anahtari olmayacak saglayici kapsama hic girmez;
  boylece kalici SKIP hucreleri matrisi sisirmez. Kapsam icindeki bir
  saglayici anahtarini kaybederse o hucreler yine SKIP yazar (sessiz
  kuculme yok, tahmin yok).
- Kesilince kaldigi yerden surer: YESIL hucreler tekrar kosmaz.
- Kota dostu pace: hucre aralari ile sinirli; tum zincir TEK hucrede
  tamamlanir.
- SAHTE KABUL YASAK (AGENTS.md §9): metin-icindeki JSON tool_call
  SAYILMAZ; arac GERCEKTEN calistirilir (tools.calistir); eski
  sapma donemindeki simulasyon kalintilari BURADA YOKTUR.

Kosum:
  python tests/live/matris_kosucu.py             -> KAPSAM x guncel arac sayisi
  python tests/live/matris_kosucu.py --pilot     -> 7x8 pilot (56 hucre)
  python tests/live/matris_kosucu.py --temizle   -> KIRMIZI/SKIP sil
  python tests/live/matris_kosucu.py --kapsam-temizle -> kapsam disi sil
  python tests/live/matris_kosucu.py groq gemini -> yalniz bu saglayicilar
"""

import json
import os
import sys
import threading
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))

from tests.live import kosucu  # noqa: E402  (ortak hatti yeniden kullanir)

MATRIS = KOK / "data" / "kabul-matrisi.json"
_HUCRE_ARASI_BEKLEME = 2.0   # kota dostu pace (saniye)

# Saglayici bazli pace: saglayicinin İLAN ETTIGI dakikalik/hiz sinirina
# uymak icin (tavan degil, hiz uyumu — AGENTS.md S0-5 tavan yasagi
# modeli daraltan sinirlar icindir, saglayicinin kendi kotasi degil).
#   groq: ucretsiz katman 8000 TPM (2026-09-20 413 kaniti: Requested
#         11125 / Limit 8000). Hucre basi ~1.2K token -> dakikada ~5 hucre.
#   gemini: 10 RPM ucretsiz katman; 3.5 sn guvenli aralik.
#   digerleri: dakika siniri gozlenmedi, 3 sn yeterli.
_PACE = {
    "groq": 11.0,
    "gemini": 3.5,
    "openrouter": 3.0,
    "glm": 3.0,
    "cloudflare": 3.0,
    "cohere": 3.0,
    "kilo": 3.0,
    "nvidia": 3.0,
    # Mistral ucretsiz "Experiment": ~1 istek/sn (60 RPM) — 3 sn guvenli.
    "mistral": 3.0,
}

# DUZEY 2 KAPSAMI (2026-09-22, Casper karari).
#
# Neden degisti: matris "8 saglayici" diye tanimliydi ve icinde cloudflare
# + cohere vardi. Bu ikisinin anahtari 2026-09-20'de "eklenmeyecek" diye
# kararlastirildigi icin 104 hucre KALICI olarak SKIP yaziyordu — yani
# olculen bir sey uretmiyordu, tabloyu sisiriyordu.
#
# Yeni tanim: YALNIZ ELDE ANAHTARI OLAN saglayicilar. Sira
# registry.VARSAYILAN_SIRA ile aynidir (uydurulmaz); cloudflare ve cohere
# kapsamdan cikarildi, anahtari olan MISTRAL kapsama girdi (zincire
# 2026-09-22'de girdi ama matris listesi guncellenmemisti).
#
# Hucre sayisi sabit yazilmaz: len(KAPSAM) x len(TOOL_SEMALARI).
KAPSAM = ("groq", "gemini", "kilo", "nvidia", "glm", "openrouter",
          "mistral")

# Pilot 8 temsilci arac: 2 kontrol + 6 temsilci (kapsam sozlesmesi:
# pilot BU kosuda gecerli; tam kosuda guncel TOOL_SEMALARI tamami acilir).
PILOT_ARACLAR = ("simdi", "hesapla", "git_durum", "sayfa_oku",
                 "list_files", "dosya_bilgi", "github_durum", "add_task")

# Arac temizligi: add_task koşumundan sonra kendi test satirini kapatir
# (gorevler.json beyaz kare kalir; complete_task idempotent degildir ama
# yalniz DUZEY2-Pilot: onekli satirlara dokunur).
_TEMIZLENECEKLER = {"add_task": ("DUZEY2-Pilot:",)}

# Soru degerleri: arguman isteyen araclara GERCEK ve guvenli degerler.
# Modelin dogru sorusu kirmizi degil — kosucunun eksik sorusudur (pilot
# 2026-09-20 bulgusu). Gerekli alanlar semadaki 'required'dan gelir.
SORU_DEGERLERI = {
    "simdi": "",
    "hesapla": "ifade=(120*18)/100",
    "git_durum": "proje=basak",
    "git_gecmis": "proje=basak",
    "git_degisenler": "proje=basak&taban=origin/master",
    "dosya_bilgi": "proje=basak&yol=README.md",
    "belge_ara": "proje=basak&sorgu=kabul",
    "list_files": "folder=knowledge",
    "read_file": "path=README.md",
    "sayfa_oku": "url=https://example.com",
    "derin_oku": "url=https://example.com",
    "adres_kontrol": "url=https://example.com",
    "github_durum": "islem=calisma_liste&proje=basak",
    "add_task": "text=DUZEY2-Pilot: otomatik test satiri",
}


def _soru_yaz(arac):
    deger = SORU_DEGERLERI.get(arac, "")
    taban = ("%s aracini simdi kullanmalisin. Sonucu degerlendir ve tek "
             "cumle soyle.")
    return taban % arac + (" Degerler: %s." % deger if deger else "")

# Beyaz liste kurali kosucunun kendi icinde de gecerli (§9).
_KILIT = threading.Lock()


def _guvenli_calistir(ad, args):
    """tools.calistir ile ayni beyaz liste kurali."""
    from tools import TANINMIS_TOOLLAR, calistir
    if ad not in TANINMIS_TOOLLAR:
        return {"error": "beyaz liste disi arac reddedildi: %s" % ad}
    return calistir(ad, args)


def _yukle():
    if MATRIS.exists():
        return json.load(open(MATRIS, encoding="utf-8"))
    return {}


def _yaz(veri):
    MATRIS.parent.mkdir(exist_ok=True)
    tmp = str(MATRIS) + ".tmp"
    with open(tmp, "w", encoding="utf-8") as f:
        f.write(json.dumps(veri, ensure_ascii=False, indent=2))
    os.replace(tmp, MATRIS)


def _hucre_yaz(saglayici, arac, kayit):
    with _KILIT:
        m = _yukle()
        m.setdefault("duzey2", {}).setdefault(saglayici, {})[arac] = kayit
        _yaz(m)


def _hucre_atlandi_mi(m, saglayici, arac):
    kayit = m.get("duzey2", {}).get(saglayici, {}).get(arac, {})
    return kayit.get("durum") == "YESIL"


def _hedef_araclar(pilot):
    if pilot:
        return list(PILOT_ARACLAR)
    return [t["function"]["name"] for t in kosucu.TOOL_SEMALARI]


def _hata_sinifi(mesaj):
    """Kirmizinin SINIFINI yazar (durum DEGISMEZ — yalniz teshis etiketi).

    KOTA: saglayicinin kendi siniri (429/1302/1305/quota/rate limit/TPM).
    ZAMAN_ASIMI: saglayici sure icinde cevap vermedi.
    PROTOKOL: native tool_call donmedi / baska arac secti / bos tur-2.
    SOZLESME: kosucunun kendi kurali (or. SKIP yazilmasi gereken yer).
    Boylece nihai rapor "kac kirmizi protokol, kac kota" diye ayrilir;
    kota kirmizisi kota taze iken yeniden kosulur.
    """
    s = str(mesaj).lower()
    if any(k in s for k in ("429", "rate limit", "quota", "1302", "1305",
                            "overloaded", "tpm", "too large", "413")):
        return "KOTA"
    if any(k in s for k in ("timed out", "timeout", "time out")):
        return "ZAMAN_ASIMI"
    if ("tool_call" in s or "arac secti" in s or "tur-2" in s
            or "bos dondu" in s or "native" in s):
        return "PROTOKOL"
    return "BILINMEYEN"


def _add_task_temizle():
    """Koşumdan ONCE eski pilot test satirlarini kapatir (beyaz kare)."""
    try:
        from tools import tasks
        yol = str(KOK / "gorevler.json")
        gorevler = json.load(open(yol, encoding="utf-8-sig"))
        for g in gorevler:
            if str(g.get("text", "")).startswith("DUZEY2-Pilot:") \
                    and g.get("durum") != "tamamlandi":
                tasks.complete_task(g["id"], yol)
    except Exception:
        pass  # temizlik hata yolunu etkilemez; hucre gercekten olculur


def _hucre_kos(saglayici, arac, sema, istemci):
    """Tek hucre: tur-1 zorunlu cagri -> GERCEK arac koşumu -> tur-2."""
    basla = time.time()
    kayit = {"saglayici": saglayici, "arac": arac,
             "model": getattr(istemci, "model", ""),
             "zaman": time.strftime("%Y-%m-%d %H:%M:%S")}
    try:
        zorlama = kosucu.ZORLAMA[saglayici]
        soru = _soru_yaz(arac)
        t0 = time.time()
        yanit1 = istemci.cevapla(
            [{"role": "user", "content": soru}],
            tools=[sema], tool_choice=zorlama)
        kayit["sure_t1"] = round(time.time() - t0, 2)
        if not yanit1.get("tool_calls"):
            raise RuntimeError(
                "native tool_call donmedi (metin-icinde-JSON sayilmaz): "
                + (yanit1.get("content") or "")[:150])
        cagri = yanit1["tool_calls"][0]
        secilen = cagri["function"]["name"]
        if secilen != arac:
            raise RuntimeError("model baska arac secti: %s" % secilen)

        args = json.loads(cagri["function"]["arguments"] or "{}")
        t1 = time.time()
        sonuc = _guvenli_calistir(arac, args)
        kayit["sure_arac"] = round(time.time() - t1, 2)
        arac_hatasi = (not isinstance(sonuc, dict)) or "error" in sonuc
        # ARAC-HATA POLITIKASI (pilot 2026-09-20 karari): arac error'u
        # gercek bir sonuctur — modelin cagrisi dogru uretildiyse hucre
        # tur-2 ile olculur; tur-2 tamamlanirsa YESIL.
        icerik = json.dumps(sonuc, ensure_ascii=False)
        tur2 = [{"role": "user", "content": soru},
                {"role": "assistant", "content": yanit1.get("content") or "",
                 "tool_calls": yanit1["tool_calls"]},
                {"role": "tool", "tool_call_id": cagri["id"], "name": arac,
                 "content": icerik}]
        # Reasoning/imza zinciri (P0): sonraki turun tasimasi icin korunur.
        for alan in ("reasoning_content", "reasoning", "reasoning_details",
                     "thinking", "reasoning_text", "tool_plan"):
            if alan in yanit1:
                tur2[-2][alan] = yanit1[alan]

        t2 = time.time()
        yanit2 = istemci.cevapla(tur2, tools=[sema], tool_choice=zorlama)
        kayit["sure_t2"] = round(time.time() - t2, 2)
        if not (yanit2.get("content") or "").strip():
            raise RuntimeError("tur-2 bos dondu")

        kayit["durum"] = "YESIL"
        kayit["tur1"] = "native"
        kayit["tur2"] = "tamam"
        if arac_hatasi:
            kayit["arac_hatasi"] = str(sonuc)[:150]   # kanitli, kirmizi degil
        kayit["sure"] = round(time.time() - basla, 2)
    except Exception as e:
        kayit["durum"] = "KIRMIZI"
        kayit["hata"] = str(e)[:250]
        kayit["sinif"] = _hata_sinifi(e)   # kota/zaman asimi/protokol
        kayit["sure"] = round(time.time() - basla, 2)
    _hucre_yaz(saglayici, arac, kayit)
    return kayit


def kos_tumu(saglayicilar=None, pilot=False, bekleme=_HUCRE_ARASI_BEKLEME):
    """Matris kosusu. Donus: ozet dict. Kesilirse YESIL'ler yerinde kalir."""
    m = _yukle()
    hedefler = list(saglayicilar or KAPSAM)
    ozet = {"toplam": 0, "YESIL": 0, "KIRMIZI": 0, "SKIP": 0,
            "saglayicilar": {}}
    for saglayici in hedefler:
        if kosucu._anahtarlar(saglayici) is None:
            n = 0
            for arac in _hedef_araclar(pilot):
                _hucre_yaz(saglayici, arac, {
                    "saglayici": saglayici, "arac": arac, "durum": "SKIP",
                    "hata": kosucu.ANAHTAR_YOK,
                    "zaman": time.strftime("%Y-%m-%d %H:%M:%S")})
                n += 1
            ozet["SKIP"] += n
            ozet["toplam"] += n
            ozet["saglayicilar"][saglayici] = {"SKIP": "anahtar yok"}
            print("[SKIP] %s — anahtar yok (%d hucre, TEKRAR DENE)"
                  % (saglayici, n))
            continue
        try:
            istemci = kosucu._istemci(saglayici)
            if not getattr(istemci, "musait", lambda: True)():
                print("[SKIP] %s — istemci kurulamadi" % saglayici)
                ozet["saglayicilar"][saglayici] = {"SKIP": "istemci"}
                continue
        except Exception as e:
            print("[SKIP] %s — %s" % (saglayici, str(e)[:100]))
            ozet["saglayicilar"][saglayici] = {"SKIP": "kurulum"}
            continue

        araclar = _hedef_araclar(pilot)
        sayim = {"YESIL": 0, "KIRMIZI": 0}
        for i, arac in enumerate(araclar):
            if arac == "add_task":
                _add_task_temizle()
            if _hucre_atlandi_mi(m, saglayici, arac):
                sayim["YESIL"] += 1   # onceki kosudan kaliyor
                continue
            sema = kosucu.SEMALAR[arac]
            kayit = _hucre_kos(saglayici, arac, sema, istemci)
            sayim[kayit["durum"]] = sayim.get(kayit["durum"], 0) + 1
            ozet["toplam"] += 1
            print("[%s] %s/%s — %s" % (kayit["durum"], saglayici, arac,
                                       kayit.get("hata",
                                                 "%.1f sn" % kayit["sure"])))
            if i < len(araclar) - 1 and bekleme > 0:
                time.sleep(_PACE.get(saglayici, bekleme))
        ozet["YESIL"] += sayim["YESIL"]
        ozet["KIRMIZI"] += sayim["KIRMIZI"]
        ozet["saglayicilar"][saglayici] = sayim
        m = _yukle()
    return ozet


def kapsam_temizle():
    """Kapsam DISI saglayicilarin hucrelerini matristen siler (2026-09-22).

    Kapsamdan cikan saglayicinin (cloudflare, cohere) kalinti satirlari
    nihai raporun hucre sayimini sisirmesin. Yalniz o saglayicilarin
    duzey2 kayitlarini siler; YESIL hucrelere ve baska anahtarlara
    dokunmaz. Donus: silinen saglayici adlari.
    """
    with _KILIT:
        m = _yukle()
        d2 = m.get("duzey2", {})
        disi = [s for s in d2 if s not in KAPSAM]
        for s in disi:
            d2.pop(s, None)
        _yaz(m)
    return disi


def temizle(saglayici=None):
    """KIRMIZI/SKIP hucreleri siler; YESIL korunur (kesintisiz devam)."""
    with _KILIT:
        m = _yukle()
        d2 = m.get("duzey2", {})
        hedefler = [saglayici] if saglayici else list(d2.keys())
        for s in hedefler:
            for a in [a for a, k in d2.get(s, {}).items()
                      if k.get("durum") != "YESIL"]:
                d2[s].pop(a, None)
        _yaz(m)


if __name__ == "__main__":
    adlar = [a for a in sys.argv[1:] if not a.startswith("--")]
    pilot = "--pilot" in sys.argv
    if "--kapsam-temizle" in sys.argv:
        silinen = kapsam_temizle()
        print("Kapsam disi saglayici hucreleri silindi: %s"
              % (", ".join(silinen) if silinen else "yok"))
    elif "--temizle" in sys.argv:
        temizle(adlar[0] if adlar else None)
        print("KIRMIZI/SKIP hucreler silindi; tekrar kosuma hazir.")
    else:
        oz = kos_tumu(adlar or None, pilot=pilot)
        print("\nOZET: %d hucre | %d YESIL / %d KIRMIZI / %d SKIP" % (
            oz["toplam"], oz["YESIL"], oz["KIRMIZI"], oz["SKIP"]))
