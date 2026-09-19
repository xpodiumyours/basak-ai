"""brain/kilo.py — Kilo Gateway entegrasyonu (anahtarsız).

Ücretsiz modeller için kimlik doğrulama istemez; istekler IP ile
tanınır, saatte 200 istek/IP sınırı vardır.
OpenAI-uyumlu uç: https://api.kilo.ai/api/gateway

DİKKAT — ücretsiz modeller "düşünen" (reasoning) modeller. Düşünme metni
max_tokens bütçesinden yer ve ayrı bir `reasoning` alanında döner.
Bütçe dar tutulursa cevap tamamen BOŞ döner (2026-08-23 ölçümü:
max_tokens=150 → content boş, 150 jetonun 81'i düşünmeye gitti;
max_tokens=1024 → düzgün cevap). Bu yüzden VARSAYILAN_JETON geniştir ve
boş cevap sessizce kullanıcıya gitmez, hata sayılıp zincir devam eder.
"""

import json
import logging

from openai import OpenAI

logger = logging.getLogger(__name__)

from brain.kullanim import kullanim_ekle
from brain.message_utils import reasoning_ayikla

BASE_URL = "https://api.kilo.ai/api/gateway"

# Kilo resmi API'si :free modellerde anonim erişime izin verir.
# OpenAI istemcisi api_key ister; anonim kullanımda HTTP istemcisi
# Authorization başlığını gönderimden hemen önce kaldırır.
YER_TUTUCU_ANAHTAR = "anonymous"

# Düşünme metni bütçeden yediği için dar tutulamaz (dosya başındaki nota bak).
# ARAC-PLANI S5 cizgisi: 4096 (1024'te duzgun cevap olculdu).
VARSAYILAN_JETON = 4096

# kilo-auto/free ücretsiz modeller arasında kendi yönlendirir.
# Tek tek modeller yedek: liste sunucu tarafında değişiyor.
# nvidia/nemotron-3-super düşünme metnini content'e sızdırdığı için yok.
VARSAYILAN_MODEL = "kilo-auto/free"
TERCIH_SIRASI = [
    "kilo-auto/free",
    "stepfun/step-3.7-flash:free",
    "tencent/hy3:free",
    "poolside/laguna-s-2.1:free",
]

# kilo-auto/free "tools" destekliyor ama canli katalogda "tool_choice"
# destekledigini ilan etmiyor. Ajan/protokol turunda yalniz hem tools hem
# tool_choice ilan eden ucretsiz modeller kullanilir. Ilk tercih 2026-09-19
# canli iki turlu tool protokolunde dogrulandi.
ARAC_MODEL_TERCIH_SIRASI = [
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "poolside/laguna-s-2.1:free",
    "nex-agi/nex-n2.5-pro:free",
    "inclusionai/ling-3.0-flash-vl:free",
]


class KiloClient:
    """Kilo Gateway istemcisi — API anahtarı gerektirmez."""

    def __init__(self, model: str = None, api_key: str = None):
        self.model = model or VARSAYILAN_MODEL
        self.api_key = (api_key or "").strip()
        self.client = None
        self._arac_modeli = None
        self._kur()

    def _kur(self):
        try:
            kwargs = {
                "api_key": self.api_key or YER_TUTUCU_ANAHTAR,
                "base_url": BASE_URL,
                "timeout": 60.0,
                "max_retries": 0,
                "default_headers": {
                    "HTTP-Referer": "http://localhost",
                    "X-Title": "Basak",
                },
            }
            if not self.api_key:
                import httpx

                def _anonim_istek(request):
                    request.headers.pop("authorization", None)

                kwargs["http_client"] = httpx.Client(
                    event_hooks={"request": [_anonim_istek]})
            self.client = OpenAI(**kwargs)
        except Exception as e:
            logger.warning("Kilo kurulamadı: %s", e)
            self.client = None

    def musait(self) -> bool:
        return self.client is not None

    def _arac_modeli_sec(self) -> str:
        """Ucretsiz ve tool_choice destekli Kilo modelini canli katalogdan sec."""
        if self._arac_modeli:
            return self._arac_modeli
        try:
            with urllib.request.urlopen(BASE_URL + "/models", timeout=10) as r:
                data = json.load(r)
            models = {
                m.get("id"): m for m in (data.get("data") or [])
                if isinstance(m, dict) and m.get("id")
            }
            for model_id in ARAC_MODEL_TERCIH_SIRASI:
                model = models.get(model_id) or {}
                params = set(model.get("supported_parameters") or [])
                if model.get("isFree") and {"tools", "tool_choice"} <= params:
                    self._arac_modeli = model_id
                    return model_id
        except Exception as e:
            logger.warning("Kilo arac model katalogu okunamadi: %s", e)

        # Katalog gecici okunamazsa son canli kabulde tam iki tur gecen
        # ucretsiz modeli kullan. Bu fallback ucretli modele gecmez.
        self._arac_modeli = ARAC_MODEL_TERCIH_SIRASI[0]
        return self._arac_modeli

    def cevapla(self, messages: list, tools: list = None, yapi=None,
                tool_choice=None) -> dict:
        """Kilo'ya mesaj gönderir. Dönen şekil groq.py ile aynıdır.

        Reasoning alanlari KULLANICIYA gosterilmez ama zincirde KORUNUR
        (P0): arac turunda ayni muhakemeyle devam edilir.
        yapi: sozlesme modu icin; bu saglayici su an yok sayar.
        """
        if not self.client:
            raise RuntimeError("Kilo bağlı değil")

        model = self.model
        if tools and self.model == VARSAYILAN_MODEL:
            model = self._arac_modeli_sec()

        kwargs = {
            "model": model,
            "messages": messages,
            "max_tokens": VARSAYILAN_JETON,
        }
        if tools:
            kwargs["tools"] = tools
            if tool_choice is not None:
                kwargs["tool_choice"] = tool_choice

        resp = self.client.chat.completions.create(**kwargs)
        secim = resp.choices[0]
        msg = secim.message
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
                          "tool_calls": tool_calls, **muhakeme}, resp)

        icerik = msg.content or ""
        if not icerik.strip():
            # Düşünme metni bütçeyi bitirmiş: boş balon gösterme, zincir
            # sıradaki sağlayıcıya geçsin.
            neden = getattr(secim, "finish_reason", None) or "bilinmiyor"
            raise RuntimeError(
                "Kilo bos cevap dondu (finish_reason=%s) — dusunme metni "
                "jeton butcesini bitirmis olabilir" % neden)

        return kullanim_ekle({"content": icerik, **muhakeme}, resp)
