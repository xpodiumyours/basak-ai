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
# Duzey 1 kaniti (2026-09-20 00:07, canli): kilo-auto/free yonlendiricisi
# zorunlu arac turunda GERCEK tool_call uretmıyor (metne yazıyor —
# "[[{"name": "simdi"...}]]"); stepfun/step-3.7-flash:free ayni istekte
# native tool_call + tur-2 devamini 9.3 sn'de tamamladi. Varsayilan bu
# olcume gore sabitlendi (sira olcumle dizilir kurali).
VARSAYILAN_MODEL = "stepfun/step-3.7-flash:free"
TERCIH_SIRASI = [
    "stepfun/step-3.7-flash:free",
    "tencent/hy3:free",
    "poolside/laguna-s-2.1:free",
    "kilo-auto/free",
]


def _kilo_global_kota_mi(hata) -> bool:
    """Kilo'nun IP-geneli 200/saat kotasi mi?"""
    s = str(hata).lower()
    return (
        "rate limit exceeded for free models" in s
        or "200 requests per hour" in s
        or ("per ip" in s and ("rate" in s or "limit" in s))
    )


def _model_yedegi_gerekir_mi(hata) -> bool:
    """Yalniz model/uplink kaynakli gecici arizada diger free modeli dene."""
    if _kilo_global_kota_mi(hata):
        return False
    durum = getattr(hata, "status_code", None)
    if durum is None:
        try:
            durum = getattr(getattr(hata, "response", None), "status_code", None)
        except Exception:
            durum = None
    if durum in (404, 410, 429, 500, 502, 503, 504):
        return True
    s = str(hata).lower()
    return any(k in s for k in (
        "kilo bos cevap", "model not found", "model unavailable",
        "model is unavailable", "no endpoints", "upstream",
        "timed out", "timeout", "connection reset",
        "tool_choice", "tool choice",
    ))


class KiloClient:
    """Kilo Gateway istemcisi — API anahtarı gerektirmez."""

    def __init__(self, model: str = None, api_key: str = None):
        self.model = model or VARSAYILAN_MODEL
        self.api_key = (api_key or "").strip()
        self.client = None
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

    def _tek_model(self, model_adi: str, messages: list,
                   tools: list = None, tool_choice=None) -> dict:
        kwargs = {
            "model": model_adi,
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
            neden = getattr(secim, "finish_reason", None) or "bilinmiyor"
            raise RuntimeError(
                "Kilo bos cevap dondu (finish_reason=%s) — dusunme metni "
                "jeton butcesini bitirmis olabilir" % neden)

        return kullanim_ekle({"content": icerik, **muhakeme}, resp)

    def cevapla(self, messages: list, tools: list = None, yapi=None,
                tool_choice=None) -> dict:
        """Kilo free havuzunda ayni modeli koruyarak cevap verir.

        Aktif model basariliysa degismez. Yalniz model/uplink kaynakli
        gecici arizada diger guncel free modele gecilir. Kilo ortak
        200/saat/IP kotasi dolduysa model degistirilmez; hata Brain katmanina
        birakilir ve saglayici cooldowna girer.
        """
        if not self.client:
            raise RuntimeError("Kilo bağlı değil")

        sirali = []
        if self.model:
            sirali.append(self.model)
        for aday in TERCIH_SIRASI:
            if aday not in sirali:
                sirali.append(aday)

        son_hata = None
        for model_adi in sirali:
            try:
                yanit = self._tek_model(
                    model_adi, messages, tools=tools,
                    tool_choice=tool_choice)
                self.model = model_adi
                return yanit
            except Exception as e:
                son_hata = e
                if _kilo_global_kota_mi(e):
                    raise
                if not _model_yedegi_gerekir_mi(e):
                    raise
                logger.warning(
                    "Kilo %s gecici/model hatasi, siradaki free model: %s",
                    model_adi, str(e))

        raise RuntimeError(
            "Kilo ücretsiz modellerinin hiçbiri cevap vermedi") from son_hata
