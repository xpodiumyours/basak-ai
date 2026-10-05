"""brain/llm7.py — LLM7.io bulut entegrasyonu.

Resmi belgeler (docs.llm7.io, 2026-10-02 okundu):

  Base URL — api-reference/introduction.md:
    "## Base URL  https://api.llm7.io/v1"
    "The API uses Bearer tokens for authentication."

  Ucretsiz katman — limits.md:
    "| Free token | 1 | 60 | 250 |"   (1 sn / 1 dk / 1 saat)
    "| Free token | 100,000 tokens per 24 hours |"
    "Token usage is counted as input tokens plus output tokens."
    "Free-token quotas are provided at no charge and may be reduced
     without notice based on demand, service capacity, model
     availability, fair-use calculations, abuse-prevention controls,
     and other operational factors."
    Gunluk ISTEK limiti YOK — yalniz 24 saatlik token kotasi var.
    Bu, SLA degildir: yukaridaki "may be reduced without notice"
    sarti nedeniyle her zaman 100K olmayabilir.

  Tool calling — guides/function-calling.md:
    "Function calling depends on the selected model. Use the Models
     API to find models with `tools_calling: true`."
    "`tool_choice: \"auto\"`: Lets the model decide whether to call
     your tool or answer directly."
    BELGELENEN TEK tool_choice DEGERI "auto". "required"/"none"
    hicbir resmi sayfada belgelenmemis; openapi.json'da /chat/completions
    yolu ve tool_choice alani YOK. Bu yuzden ajan_tool_mode
    "auto_enforced"tir: Basak zorunlu ajan turunda duz metni basari
    saymaz, siradaki saglayiciya gecer. Duz metne dokunulmaz.

  Kimlik dogrulama — limits.md'de "credit card"/"payment"/"phone"/"SMS"
    kelimeleri GEÇMIYOR. Resmi metinde kart veya telefon sartı YOK
    denebilir; bu yuzden kart kapisi ACILIR (otomatik_ucretsiz=True).

  Veri saklama — BULUNAMADI. 19 URL'lik sitemap ve 49 KB llms-full.txt
    taranmasi rağmen privacy/retention/training kelimeleri sifir.
    llm7.io ana sitesinde de yasal sayfa YOK. Bu yuzden registry karti
    "dogrulanmadi" der — ASLA "kaydetmez" varsayilmaz (registry.py kurali).
    Kullanan kullaniciya bu durum gosterilir; saglayici otomatik kapatilmaz.
"""

import json
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

from brain.kullanim import kullanim_ekle
from brain.message_utils import reasoning_ayikla

BASE_URL = "https://api.llm7.io/v1"

# Varsayilan model: canli /v1/models katalogundan DOGRULANDI
# (2026-10-02, https://api.llm7.io/v1/models):
#   id="DeepSeek-V4-Flash-0731", tier="turbo", tools_calling=true,
#   context_window 400.000, json_mode=true, reasoning=true,
#   availability_last_hour_percent=80.09
# tier="turbo" = ucretsiz katmana erisebilen aile (limits.md'de
# "turbo tier" ucretsiz katmana erisebilen modeller olarak anilir;
# tier="pro" modeller ucretlidir).
# Baska bir turbo + tools_calling=true model: "GLM-5.3-Flash".
VARSAYILAN_MODEL = "DeepSeek-V4-Flash-0731"
# NOT: availability_last_hour_percent=80.09 — model zaman zaman
# kapasiteye takilir. 429 donerse Brain zincirdeki siradaki
# saglayiciya gecer; hata metnine bakilmaz (resmi HTTP kodu okunur).


class Llm7Client:
    """LLM7.io API istemcisi (OpenAI-uyumlu uc)."""

    def __init__(self, api_key: str, model: str = None):
        if not api_key or not api_key.strip():
            raise ValueError("LLM7 API anahtarı boş olamaz")
        self.api_key = api_key.strip()
        self.model = model or VARSAYILAN_MODEL
        self.client = None
        self._kur()

    def _kur(self):
        try:
            self.client = OpenAI(
                api_key=self.api_key,
                max_retries=0,
                base_url=BASE_URL,
            )
        except Exception as e:
            logger.warning("LLM7 kurulamadı: %s", e)
            self.client = None

    def musait(self) -> bool:
        return self.client is not None

    def cevapla(self, messages: list, tools: list = None,
                model: str = None, yapi=None, tool_choice=None) -> dict:
        """Diger istemcilerle birebir ayni sozlesme.

        LLM7'de tool_choice icin yalniz "auto" belgeli. "required" gonderilirse
        saglayici 400 donme riski nedeniyle OTOMATIK DUSURULUR ve "auto"
        gonderilir — model metin yazarsa bu Brain'de basarisiz sayilir
        (ajan_tool_mode=auto_enforced) ve zincir siradaki saglayiciya gecer.
        Bu bir model kisitlamasi DEGIL, resmi API sozlesmesine uyumdur.
        """
        if not self.client:
            raise RuntimeError("LLM7 bağlı değil")

        kwargs = {
            "model": model or self.model,
            "messages": messages,
        }
        if tools:
            kwargs["tools"] = tools
            if tool_choice is not None:
                # Yalniz belgelenmis deger gonderilir.
                gonderilecek = tool_choice if tool_choice == "auto" else "auto"
                kwargs["tool_choice"] = gonderilecek
        if yapi is not None:
            kwargs["response_format"] = {"type": "json_object"}

        resp = self.client.chat.completions.create(**kwargs)
        msg = resp.choices[0].message
        muhakeme = reasoning_ayikla(msg)

        if msg.tool_calls:
            tool_calls = []
            for tc in msg.tool_calls:
                args = tc.function.arguments
                if not isinstance(args, str):
                    args = json.dumps(args) if args else "{}"
                tool_calls.append({
                    "id": tc.id,
                    "type": "function",
                    "function": {
                        "name": tc.function.name,
                        "arguments": args,
                    }
                })
            return kullanim_ekle({"content": msg.content or "",
                                  "tool_calls": tool_calls,
                                  **muhakeme}, resp)

        return kullanim_ekle({"content": msg.content or "",
                              **muhakeme}, resp)