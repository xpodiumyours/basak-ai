"""tests/live/matris_kosucu.py — DUZEY 2: 8x52 GERCEK canli hucre matrisi.

Kabul plani (knowledge/kabul-plani-web-gate.md, DUZEY 2):
- Her hucreye yazilir: saglayici, arac, tur-1 native mi, tur-2 devam mi,
  sure, model, hata. Bicim: data/kabul-matrisi.json (git-disi).
- Anahtarsiz saglayicinin hucreleri SKIP yazilir — tahmin DOLDURULMAZ.
- Kesilince kaldigi yerden surer: YESIL hucreler tekrar kosmaz.
- Kota dostu pace: hucre aralari ile sinirli; tum zincir TEK hucrede
  tamamlanir.
- SAHTE KABUL YASAK (AGENTS.md §9): metin-icindeki JSON tool_call
  SAYILMAZ; arac GERCEKTEN calistirilir (tools.calistir); eski
  sapma donemindeki simulasyon kalintilari BURADA YOKTUR.

Kosum:
  python tests/live/matris_kosucu.py             -> tam 416 hucre
  python tests/live/matris_kosucu.py --pilot     -> 8x8 pilot (64 hucre)
  python tests/live/matris_kosucu.py --temizle   -> KIRMIZI/SKIP sil
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

# Pilot 8 temsilci arac: 2 kontrol + 6 temsilci (kapsam sozlesmesi:
# pilot BU kosuda gecerli; tam 416'a geciste tum 52 arac acilir).
PILOT_ARACLAR = ("simdi", "hesapla", "git_durum", "sayfa_oku",
                 "list_files", "dosya_bilgi", "github_durum", "add_task")

# Arac temizligi: add_task koşumundan sonra kendi test satirini kapatir
# (gorevler.json beyaz kare kalir; complete_task idempotent degildir ama
# yalniz DUZEY2-Pilot: onekli satirlara dokunur).
_TEMIZLENECEKLER = {"add_task": ("DUZEY2-Pilot:",)}

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
        t0 = time.time()
        yanit1 = istemci.cevapla(
            [{"role": "user", "content":
              "%s aracini simdi kullanmalisin. Sonucu degerlendir ve tek "
              "cumle soyle." % arac}],
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
        if not isinstance(sonuc, dict) or "error" in sonuc:
            raise RuntimeError("arac hatasi: %s" % str(sonuc)[:150])

        icerik = json.dumps(sonuc, ensure_ascii=False)
        tur2 = [{"role": "user", "content":
                 "%s aracini simdi kullanmalisin. Sonucu degerlendir ve "
                 "tek cumle soyle." % arac},
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
        kayit["sure"] = round(time.time() - basla, 2)
    except Exception as e:
        kayit["durum"] = "KIRMIZI"
        kayit["hata"] = str(e)[:250]
        kayit["sure"] = round(time.time() - basla, 2)
    _hucre_yaz(saglayici, arac, kayit)
    return kayit


def kos_tumu(saglayicilar=None, pilot=False, bekleme=_HUCRE_ARASI_BEKLEME):
    """Matris kosusu. Donus: ozet dict. Kesilirse YESIL'ler yerinde kalir."""
    m = _yukle()
    hedefler = list(saglayicilar or kosucu.SEKIZLER)
    ozet = {"toplam": 0, "YESIL": 0, "KIRMIZI": 0, "SKIP": 0,
            "saglayicilar": {}}
    for saglayici in hedefler:
        if kosucu._anahtarlar(saglayici) is None:
            n = 0
            for arac in _hedef_araclar(pilot):
                _hucre_yaz(saglayici, arac, {
                    "saglayici": saglayici, "arac": arac, "durum": "SKIP",
                    "hata": "anahtar yok",
                    "zaman": time.strftime("%Y-%m-%d %H:%M:%S")})
                n += 1
            ozet["SKIP"] += n
            ozet["toplam"] += n
            ozet["saglayicilar"][saglayici] = {"SKIP": "anahtar yok"}
            print("[SKIP] %s — anahtar yok (%d hucre)" % (saglayici, n))
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
                time.sleep(bekleme)
        ozet["YESIL"] += sayim["YESIL"]
        ozet["KIRMIZI"] += sayim["KIRMIZI"]
        ozet["saglayicilar"][saglayici] = sayim
        m = _yukle()
    return ozet


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
    if "--temizle" in sys.argv:
        temizle(adlar[0] if adlar else None)
        print("KIRMIZI/SKIP hucreler silindi; tekrar kosuma hazir.")
    else:
        oz = kos_tumu(adlar or None, pilot=pilot)
        print("\nOZET: %d hucre | %d YESIL / %d KIRMIZI / %d SKIP" % (
            oz["toplam"], oz["YESIL"], oz["KIRMIZI"], oz["SKIP"]))
