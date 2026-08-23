"""_zincir_probe.py — Zincir saglik denetimi (gecici betik).

A) brain.py'nin gercek istemci siniflariyla anahtari olan her saglayiciya
   mini cagri atar: OK (sure) / HATA (neden) / ANAHTAR YOK.
B) NVIDIA NIM'de aday sohbet modellerini pingler; calisanlar zincire
   baglanacak, calismayanlar disarida kalacak.

Kural: zincirde anahtarsiz veya calismayan model kalmaz.
"""

import json
import os
import sys
import time

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from openai import OpenAI

NIM_URL = "https://integrate.api.nvidia.com/v1"

# Bolum A: saglayici denetimi
SAGLAYICILAR = [
    ("groq", "groq_key", "GROQ_API_KEY"),
    ("gemini", "gemini_key", "GEMINI_API_KEY"),
    ("glm", "zai_key", "ZAI_API_KEY"),
    ("cloudflare", "cloudflare_api_token", "CLOUDFLARE_API_TOKEN"),
    ("cohere", "cohere_key", "COHERE_API_KEY"),
    ("nvidia", "nvidia_key", "NVIDIA_API_KEY"),
    ("openrouter", "openrouter_key", "OPENROUTER_API_KEY"),
    ("qwen", "dashscope_key", "DASHSCOPE_API_KEY"),
    ("deepseek", "deepseek_key", "DEEPSEEK_API_KEY"),
]

# Bolum B: NVIDIA aday sohbet modelleri (registry'de henuz yok olanlar)
ADAY_MODELLER = [
    "openai/gpt-oss-120b",
    "poolside/laguna-xs-2.1",
    "thinkingmachines/inkling",
    "moonshotai/kimi-k3",
    "moonshotai/kimi-k2.6",
    "nvidia/nemotron-3-ultra-550b-a55b",
    "google/diffusiongemma-26b-a4b-it",
    "meta/muse-glimmer-30b",
    "mistralai/mistral-large-2-instruct",
    "stepfun-ai/step-3.7-flash",
]


def _anahtar_yukle():
    ayar = {}
    try:
        with open("ayarlar.json", "r", encoding="utf-8-sig") as f:
            ayar = json.load(f)
    except Exception:
        pass

    def al(ayar_ad, env_ad):
        return os.environ.get(env_ad) or ayar.get(ayar_ad) or ""

    return ayar, al


_CF_ACCOUNT = ""


def _istemci_uret(ad, key, ayar):
    from brain.groq import GroqClient
    from brain.gemini import GeminiClient
    from brain.glm import GLMClient
    from brain.cloudflare import CloudflareClient
    from brain.cohere import CohereClient
    from brain.nvidia import NvidiaClient
    from brain.openrouter import OpenRouterClient
    from brain.qwen import QwenClient
    from brain.deepseek import DeepSeekClient
    uret = {
        "groq": lambda: GroqClient(key, ayar.get("groq_model")),
        "gemini": lambda: GeminiClient(key),
        "glm": lambda: GLMClient(key),
        "cloudflare": lambda: CloudflareClient(_CF_ACCOUNT, key),
        "cohere": lambda: CohereClient(key),
        "nvidia": lambda: NvidiaClient(key),
        "openrouter": lambda: OpenRouterClient(key),
        "qwen": lambda: QwenClient(key),
        "deepseek": lambda: DeepSeekClient(key),
    }
    return uret[ad]()


MESAJ = [{"role": "user", "content": "Tek kelime yanit ver: merhaba"}]

if __name__ == "__main__":
    ayar, _al = _anahtar_yukle()
    globals()["_CF_ACCOUNT"] = (
        os.environ.get("CLOUDFLARE_ACCOUNT_ID")
        or ayar.get("cloudflare_account_id") or ""
    )

    if len(sys.argv) > 1 and sys.argv[1] == "tekrar":
        print("=" * 60)
        print("BOLUM C - BELIRSIZ KALANLAR (duzgun parametrelerle)")
        print("=" * 60)

        # cloudflare: betik hatasi duzelince tekrar
        key = _al("cloudflare_api_token", "CLOUDFLARE_API_TOKEN")
        t0 = time.time()
        try:
            from brain.cloudflare import CloudflareClient
            istemci = CloudflareClient(_CF_ACCOUNT, key)
            r = istemci.cevapla(MESAJ)
            print("cloudflare                    | OK %.1fs | %s"
                  % (time.time() - t0, (r.get("content") or "")[:40]))
        except Exception as e:
            print("cloudflare                    | HATA %.1fs | %s"
                  % (time.time() - t0, str(e)[:90]))

        # agir/dusunen modeller: tek sans daha, 60 sn cap
        nkey = _al("nvidia_key", "NVIDIA_API_KEY")
        nim = OpenAI(api_key=nkey, base_url=NIM_URL, timeout=60, max_retries=0)
        for mid in ["openai/gpt-oss-120b"]:
            t0 = time.time()
            try:
                r = nim.chat.completions.create(
                    model=mid, messages=MESAJ,
                    temperature=0, max_tokens=1024)
                icerik = ((r.choices[0].message.content or "")
                          .strip().replace("\n", " "))
                print("%-30s | OK %.1fs | %s"
                      % (mid.split("/")[-1], time.time() - t0,
                         icerik[:40] or "(bos)"))
            except Exception as e:
                print("%-30s | HATA %.1fs | %s"
                      % (mid.split("/")[-1], time.time() - t0, str(e)[:70]))

        # reasoning modelleri bos döndu: token butcesini buyut
        for mid in ["thinkingmachines/inkling", "meta/muse-glimmer-30b"]:
            t0 = time.time()
            try:
                r = nim.chat.completions.create(
                    model=mid, messages=MESAJ,
                    temperature=0, max_tokens=2048)
                msg = r.choices[0].message
                icerik = ((msg.content or "").strip().replace("\n", " "))
                print("%-30s | OK %.1fs | %s"
                      % (mid.split("/")[-1], time.time() - t0,
                         icerik[:40] or "(bos icerik)"))
            except Exception as e:
                print("%-30s | HATA %.1fs | %s"
                      % (mid.split("/")[-1], time.time() - t0, str(e)[:70]))
        sys.exit(0)

    print("=" * 60)
    print("BOLUM A - SAGLAYICI DENETIMI (gercek istemci sinifiyla)")
    print("=" * 60)
    for ad, ayar_ad, env_ad in SAGLAYICILAR:
        key = _al(ayar_ad, env_ad)
        if not key:
            print("%-11s | ANAHTAR YOK -> zaten zincirde degil" % ad)
            continue
        t0 = time.time()
        try:
            istemci = _istemci_uret(ad, key, ayar)
            if not istemci.musait():
                raise RuntimeError("istemci kurulamadi")
            r = istemci.cevapla(MESAJ)
            icerik = (r.get("content") or "").strip()
            print("%-11s | OK %.1fs | %s" % (ad, time.time() - t0,
                                             icerik[:40].replace("\n", " ")))
        except Exception as e:
            print("%-11s | HATA %.1fs | %s"
                  % (ad, time.time() - t0, str(e)[:90]))

    print()
    print("=" * 60)
    print("BOLUM B - NVIDIA ADAY SOHBET MODELLERI")
    print("=" * 60)
    nkey = _al("nvidia_key", "NVIDIA_API_KEY")
    if not nkey:
        print("nvidia_key yok, Bolum B atlandi")
        sys.exit(0)
    nim = OpenAI(api_key=nkey, base_url=NIM_URL, timeout=45, max_retries=0)
    for mid in ADAY_MODELLER:
        t0 = time.time()
        try:
            r = nim.chat.completions.create(
                model=mid, messages=MESAJ,
                temperature=0, max_tokens=256)
            icerik = ((r.choices[0].message.content or "")
                      .strip().replace("\n", " "))
            print("%-42s | OK %.1fs | %s"
                  % (mid, time.time() - t0, icerik[:40]))
        except Exception as e:
            print("%-42s | HATA %.1fs | %s"
                  % (mid, time.time() - t0, str(e)[:70]))
