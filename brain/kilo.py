"""brain/kilo.py — Kilo Gateway entegrasyonu (anahtarsız).

Ücretsiz modeller için kimlik doğrulama istemez; istekler IP ile
tanınır, saatte 200 istek/IP sınırı vardır.
OpenAI-uyumlu uç: https://api.kilo.ai/api/gateway/v1

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

BASE_URL = "https://api.kilo.ai/api/gateway/v1"

# openai paketi boş anahtar kabul etmiyor; Kilo'nun ücretsiz katmanı
# Authorization başlığını zaten yok sayıyor — bu bir yer tutucudur.
YER_TUTUCU_ANAHTAR = "anahtarsiz"

# Düşünme metni bütçeden yediği için dar tutulamaz (dosya başındaki nota bak).
VARSAYILAN_JETON = 1500

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


class KiloClient:
    """Kilo Gateway istemcisi — API anahtarı gerektirmez."""

    def __init__(self, model: str = None):
        self.model = model or VARSAYILAN_MODEL
        self.client = None
        self._kur()

    def _kur(self):
        try:
            self.client = OpenAI(
                api_key=YER_TUTUCU_ANAHTAR,
                base_url=BASE_URL,
                timeout=30.0,
                max_retries=0,
                default_headers={
                    "HTTP-Referer": "http://localhost",
                    "X-Title": "Basak",
                },
            )
        except Exception as e:
            logger.warning("Kilo kurulamadı: %s", e)
            self.client = None

    def musait(self) -> bool:
        return self.client is not None

    def cevapla(self, messages: list, tools: list = None) -> dict:
        """Kilo'ya mesaj gönderir. Dönen şekil groq.py ile aynıdır.

        `reasoning` / `reasoning_details` alanları bilerek dışarı
        verilmez — kullanıcı düşünme metnini görmemeli.
        """
        if not self.client:
            raise RuntimeError("Kilo bağlı değil")

        kwargs = {
            "model": self.model,
            "messages": messages,
            "temperature": 0.5,
            "max_tokens": VARSAYILAN_JETON,
        }
        if tools:
            kwargs["tools"] = tools

        resp = self.client.chat.completions.create(**kwargs)
        secim = resp.choices[0]
        msg = secim.message

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
                          "tool_calls": tool_calls}, resp)

        icerik = msg.content or ""
        if not icerik.strip():
            # Düşünme metni bütçeyi bitirmiş: boş balon gösterme, zincir
            # sıradaki sağlayıcıya geçsin.
            neden = getattr(secim, "finish_reason", None) or "bilinmiyor"
            raise RuntimeError(
                "Kilo bos cevap dondu (finish_reason=%s) — dusunme metni "
                "jeton butcesini bitirmis olabilir" % neden)

        return kullanim_ekle({"content": icerik}, resp)
