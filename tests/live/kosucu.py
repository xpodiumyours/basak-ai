"""tests/live/kosucu.py — Duzey 1: 8/8 NATIVE protokol kapisi.

Plana gore (knowledge/kabul-plani-web-gate.md, TEST DUZEYLERI):
- 8 saglayicinin TAMAMI canli tek tur zorunlu arac cagrisina sokulur.
- Gecme olcutu: yanit GERCEK tool_call icermeli (metin-icindeki JSON
  tool_call SAYILMAZ — sahte kabul yasaği) VE tur-2 (tool-result devami)
  tamamlanmali.
- Anahtari olmayan saglayicinin hucresi SKIP yazilir — tahminle
  doldurulmaz.
- Gecen saglayicinin gercek yanit kalibi (fixture) kaydedilir:
  tests/live/fixtures/<saglayici>_native.json — Duzey 0 artik bu
  GERCEK kaliptan dogrulanir.

Kosum: python -m pytest tests/live/test_seviye1_native.py --live -q
"""

import json
import os
import re
import sys
import time
from pathlib import Path

KOK = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(KOK))
FIXTURE_DIR = Path(__file__).resolve().parent / "fixtures"
MATRIS = KOK / "data" / "kabul-matrisi.json"

# 8/8 tam liste — kapsam burada KUCULTULMEZ (kapsam sozlesmesi).
SEKIZLER = ("groq", "gemini", "openrouter", "glm", "cloudflare",
            "cohere", "kilo", "nvidia")

# Anahtar adi -> ayarlar.json alani. cloudflare account_id ister.
ANAHTARLAR = {
    "groq": ["groq_key"],
    "gemini": ["gemini_key"],
    "openrouter": ["openrouter_key"],
    "glm": ["zai_key"],
    "cloudflare": ["cf_account_id", "cf_api_token"],
    "cohere": ["cohere_key"],
    "kilo": [],
    "nvidia": ["nvidia_key"],
}

# Tek kaynak: registry. GercEK ajan modu oradan okunur (kopya tablo yok).
def _zorlama(ad):
    from brain import registry
    return registry.ajan_tool_choice(ad)

ZORLAMA = {ad: _zorlama(ad) for ad in SEKIZLER}


def _anahtarlar(ad):
    a = json.load(open(KOK / "ayarlar.json", encoding="utf-8-sig"))
    degerler = [a.get(k, "").strip() for k in ANAHTARLAR[ad]]
    return degerler if (not degerler or all(degerler)) else None


def _istemci(ad):
    if ad == "groq":
        from brain.groq import GroqClient
        return GroqClient(_anahtarlar("groq")[0])
    if ad == "gemini":
        from brain.gemini import GeminiClient
        return GeminiClient(_anahtarlar("gemini")[0])
    if ad == "openrouter":
        from brain.openrouter import OpenRouterClient
        return OpenRouterClient(_anahtarlar("openrouter")[0])
    if ad == "glm":
        from brain.glm import GLMClient
        return GLMClient(_anahtarlar("glm")[0])
    if ad == "cloudflare":
        from brain.cloudflare import CloudflareClient
        gid, tok = _anahtarlar("cloudflare")
        return CloudflareClient(gid, tok)
    if ad == "cohere":
        from brain.cohere import CohereClient
        return CohereClient(_anahtarlar("cohere")[0])
    if ad == "kilo":
        from brain.kilo import KiloClient
        return KiloClient()
    if ad == "nvidia":
        from brain.nvidia import NvidiaClient
        return NvidiaClient(_anahtarlar("nvidia")[0])
    raise ValueError(ad)


SIMDI_SEMA = {"type": "function", "function": {
    "name": "simdi", "description": "Su anki tarih ve saati doner.",
    "parameters": {"type": "object", "properties": {}}}}

MESAJLAR = [{"role": "user", "content":
             "Su anki tarih ve saati ogrenmek zorundasin. simdi aracini "
             "kullan, sonucu kendine gore degerlendir ve bana tek cumle "
             "soyle."}]

# DUZEY 2: 52 gercEK arac semasi — TEK kaynak tools.TOOLS (kopya yok).
from tools import TOOLS as TOOL_SEMALARI  # noqa: E402

SEMALAR = {t["function"]["name"]: t for t in TOOL_SEMALARI}


def _native_mi(yanit):
    """Gercek tool_call var mi? Metin-icinde-JSON SAYILMAZ (§9)."""
    return bool(yanit.get("tool_calls"))


def _tur1_ve_tur2(ad, istemci):
    """Tur-1 zorunlu cagri + gercek simdi koşumu + tur-2 devami."""
    t0 = time.time()
    yanit1 = istemci.cevapla(MESAJLAR, tools=[SIMDI_SEMA],
                             tool_choice=ZORLAMA[ad])
    if not _native_mi(yanit1):
        raise RuntimeError(
            "native tool_call donmedi (metin-icinde-JSON sayilmaz): "
            + (yanit1.get("content") or "")[:120])

    cagri = yanit1["tool_calls"][0]
    ad_ = cagri["function"]["name"]
    if ad_ != "simdi":
        raise RuntimeError("model baska arac secti: %s" % ad_)

    # GERCEK arac koşumu — simulasyon yok (§9).
    from tools import calistir
    args = json.loads(cagri["function"]["arguments"] or "{}")
    sonuc = calistir(ad_, args)
    icerik = json.dumps(sonuc, ensure_ascii=False)

    tur2_mesajlar = MESAJLAR + [
        {"role": "assistant", "content": yanit1.get("content") or "",
         "tool_calls": yanit1["tool_calls"]},
        {"role": "tool", "tool_call_id": cagri["id"], "name": ad_,
         "content": icerik},
    ]
    # Saglayici zincirinde P0: reasoning/imza alani geri tasınır.
    for alan in ("reasoning_content", "reasoning", "reasoning_details",
                 "thinking", "reasoning_text", "tool_plan"):
        if alan in yanit1:
            tur2_mesajlar[-2][alan] = yanit1[alan]
    if "extra_content" in cagri:
        # cagriyanit_dict seviyesinde korundu; message_utils tasir.
        pass

    yanit2 = istemci.cevapla(tur2_mesajlar, tools=[SIMDI_SEMA],
                             tool_choice=ZORLAMA[ad])
    sure = round(time.time() - t0, 2)
    if not (yanit2.get("content") or "").strip():
        raise RuntimeError("tur-2 bos dondu")
    return sure, yanit1, icerik, yanit2


def _fixture_yaz(ad, yanit1, icerik, yanit2):
    """GercEK yanit kalibini kaydet — Duzey 0 bu kalib dogrulayacak."""
    FIXTURE_DIR.mkdir(exist_ok=True)
    kalip = {
        "saglayici": ad,
        "kayit": time.strftime("%Y-%m-%d %H:%M:%S"),
        "tur1": {
            "content": (yanit1.get("content") or "")[:400],
            "tool_calls": yanit1.get("tool_calls"),
            "reasoning_anahtarlari": [k for k in yanit1.keys()
                                       if k not in ("content", "tool_calls",
                                                    "_kullanim")],
        },
        "arac_sonucu": icerik[:400],
        "tur2_content": (yanit2.get("content") or "")[:400],
    }
    yol = FIXTURE_DIR / ("%s_native.json" % ad)
    yol.write_text(json.dumps(kalip, ensure_ascii=False, indent=2),
                   encoding="utf-8")
    return str(yol)


def _matrise_yaz(ad, durum, sure=None, hata=None):
    MATRIS.parent.mkdir(exist_ok=True)
    m = {}
    if MATRIS.exists():
        m = json.load(open(MATRIS, encoding="utf-8"))
    m.setdefault("duzey1", {})[ad] = {
        "durum": durum, "sure": sure, "hata": (hata or "")[:300],
        "zaman": time.strftime("%Y-%m-%d %H:%M:%S"),
    }
    tmp = str(MATRIS) + ".tmp"
    open(tmp, "w", encoding="utf-8").write(
        json.dumps(m, ensure_ascii=False, indent=2))
    os.replace(tmp, MATRIS)


def saglayici_hucresi(ad):
    """Tek saglayicinin Duzey 1 hucresi. Donus: (durum, mesaj)."""
    if _anahtarlar(ad) is None:
        _matrise_yaz(ad, "SKIP", hata="anahtar yok")
        return "SKIP", "anahtar yok"
    if ad in ("glm",):
        # Zincirde halihazira cooldown'lu; yine de DENENIR — kapsam tam.
        pass
    try:
        istemci = _istemci(ad)
        if not getattr(istemci, "musait", lambda: True)():
            _matrise_yaz(ad, "SKIP", hata="istemci kurulamadi")
            return "SKIP", "istemci kurulamadi"
        sure, y1, icerik, y2 = _tur1_ve_tur2(ad, istemci)
        yol = _fixture_yaz(ad, y1, icerik, y2)
        _matrise_yaz(ad, "YESIL", sure=sure)
        return "YESIL", "%.2f sn, kalip: %s" % (sure, yol)
    except Exception as e:
        mesaj = str(e)[:300]
        _matrise_yaz(ad, "KIRMIZI", hata=mesaj)
        return "KIRMIZI", mesaj


def kos_tumu():
    """8/8 hucreyi kosar; ozet dondurur. Kapsam tam — atlanan yok."""
    sonuc = {}
    for ad in SEKIZLER:
        durum, mesaj = saglayici_hucresi(ad)
        sonuc[ad] = (durum, mesaj)
        print("[%s] %s — %s" % (durum, ad, mesaj[:160]))
    return sonuc


if __name__ == "__main__":
    # Tek saglayici modu: python kosucu.py groq — kota dostu tekrar.
    hedefler = sys.argv[1:] or list(SEKIZLER)
    s = {ad: saglayici_hucresi(ad) for ad in hedefler}
    yesil = sum(1 for d, _ in s.values() if d == "YESIL")
    skip = sum(1 for d, _ in s.values() if d == "SKIP")
    kirmizi = sum(1 for d, _ in s.values() if d == "KIRMIZI")
    print("\nOZET: %d YESIL / %d SKIP / %d KIRMIZI  (hedef 8/8 YESIL)"
          % (yesil, skip, kirmizi))
