"""brain/kilo.py — Kilo Gateway entegrasyonu (anahtarsız).

Ücretsiz modeller için kimlik doğrulama istemez; istekler IP ile
tanınır, saatte 200 istek/IP sınırı vardır.
OpenAI-uyumlu uç: https://api.kilo.ai/api/gateway

DİKKAT — ücretsiz modeller "düşünen" (reasoning) modeller. Uygulama
cevap için yapay bir token tavanı koymaz; sağlayıcının/modelin kendi gerçek
sınırı geçerlidir. Boş cevap sessizce kullanıcıya gitmez, hata sayılıp
zincir devam eder.
"""

import json
import logging
import time

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

# SIRA OLCUMLE DIZILIR (AGENTS.md). Kilo'nun ucretsiz katalogu disaridan
# degisiyor; bu yuzden her elden gecirmede adaylar canli olculur.
#
# 2026-10-12 OLCUMU (Kilo katalogu degisti — eski iki varsayilan 404):
#   Katalogdan KALKANLAR (404, listede tutulmaz):
#     stepfun/step-3.7-flash:free, qwen/qwen3.8-27b:free,
#     apodex/apodex-1.1-mini:free, inclusionai/ling-3.0-flash-sante:free
#   GERCEK tool_call uretenler (auto / required, sn):
#     nvidia/nemotron-3-super-120b-a12b:free      1.36 / 1.00  GECTI
#     nvidia/nemotron-3.5-lightning:free          0.80 / 1.20  GECTI
#     stepfun/step-5-preview-free                 0.65 / 4.08  GECTI (yavas)
#     liquid/lfm-2.5-2.6b:free                    metne yazdi / 4.24  RED
#                                                  (auto turunda arac
#                                                   cagirmadi, metin doktu)
#   REDDEDILENLER (olcum kaydi, geri gelmesin):
#     nvidia/nemotron-3-nano-omni-30b-a3b-reasoning:free -> _tek_model
#       yanitini cozerken patliyor ("NoneType is not subscriptable")
#     poolside/laguna-s-2.1:free -> required turunda upstream 429
#     poolside/laguna-xs-2.1:free -> upstream 429
#   kilo-auto/free yonlendiricisi (2026-09-20 kaniti): zorunlu arac turunda
#   GERCEK tool_call uretmiyor (metne yaziyor — "[[{"name"...}]]"); bu yuzden
#   her zaman EN SONDA durur.
VARSAYILAN_MODEL = "nvidia/nemotron-3.5-lightning:free"
TERCIH_SIRASI = [
    "nvidia/nemotron-3.5-lightning:free",
    "nvidia/nemotron-3-super-120b-a12b:free",
    "stepfun/step-5-preview-free",
    "liquid/lfm-2.5-2.6b:free",
    "kilo-auto/free",
]

# 2026-10-28 OLCUMU: nvidia/nemotron-3-super-120b-a12b:free artik
# "model_not_found" (404) donuyor; 3.5-lightning ayni turda gercek
# tool_call uretti. Yine de katalog disaridan degistigi icin TEK model
# varsaymak yetmez: basarili model surec boyunca hatirlanir, 404 alan
# model 30 dakika denenmez. Boylece her yeni Brain/alt ajan ilk istegi
# bayat modele harcamaz.
_SAGLAM_MODEL = None
_BOZUK_MODELLER = {}
_BOZUK_SURESI = 1800.0


def _saglik_sifirla():
    global _SAGLAM_MODEL
    _SAGLAM_MODEL = None
    _BOZUK_MODELLER.clear()


def _bozuk_mu(model_adi):
    bitis = _BOZUK_MODELLER.get(model_adi)
    if not bitis:
        return False
    if bitis > time.monotonic():
        return True
    _BOZUK_MODELLER.pop(model_adi, None)
    return False


def _model_kayboldu_mu(hata):
    s = str(hata).lower()
    return ("model not found" in s or "does not exist" in s
            or "model unavailable" in s or "no endpoints" in s)


def _isaretle_bozuk(model_adi, hata):
    global _SAGLAM_MODEL
    if not _model_kayboldu_mu(hata):
        return
    _BOZUK_MODELLER[model_adi] = time.monotonic() + _BOZUK_SURESI
    if _SAGLAM_MODEL == model_adi:
        _SAGLAM_MODEL = None


def _kilo_global_kota_mi(hata) -> bool:
    """Kilo'nun IP-geneli 200/saat kotasi mi?"""
    s = str(hata).lower()
    return (
        "rate limit exceeded for free models" in s
        or "200 requests per hour" in s
        or ("per ip" in s and ("rate" in s or "limit" in s))
    )


def _model_yedegi_gerekir_mi(hata) -> bool:
    """Model/uplink veya required-tool protokol ihlalinde diger free modeli dene."""
    if _kilo_global_kota_mi(hata):
        return False
    durum = getattr(hata, "status_code", None)
    if durum is None:
        try:
            durum = getattr(getattr(hata, "response", None), "status_code", None)
        except Exception:
            durum = None
    if durum in (402, 403, 404, 410, 429, 500, 502, 503, 504):
        return True
    s = str(hata).lower()
    return any(k in s for k in (
        "kilo bos cevap", "model not found", "model unavailable",
        "model is unavailable", "does not exist", "no endpoints", "upstream",
        "timed out", "timeout", "connection reset",
        "tool_choice", "tool choice", "required tool_call yok",
    ))


def _kilo_mesajlari(messages):
    """Kilo Gateway mesaj semasina uymayan opsiyonel reasoning'i ayikla.

    Gateway reasoning_details alanini varsa dizi bekliyor. Bazi free
    modeller bu alani string dondurebildigi icin ayni modele geri
    gondermek 400 uretiyor. Muhakeme metni content'e eklenmez; yalniz
    gecersiz opsiyonel metadata atilir.
    """
    temiz = []
    for mesaj in messages or []:
        if not isinstance(mesaj, dict):
            continue
        m = dict(mesaj)
        if ("reasoning_details" in m
                and not isinstance(m.get("reasoning_details"), list)):
            m.pop("reasoning_details", None)
        temiz.append(m)
    return temiz


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

    def goru_cevapla(self, messages: list, timeout=None) -> dict:
        """Step 3.7 Flash goruntu girdisi; istege ozel sure siniri alabilir."""
        if not self.client:
            raise RuntimeError("Kilo bağlı değil")
        return self._tek_model(self.model, messages, timeout=timeout)

    def _tek_model(self, model_adi: str, messages: list,
                   tools: list = None, tool_choice=None, timeout=None) -> dict:
        kwargs = {
            "model": model_adi,
            "messages": _kilo_mesajlari(messages),
}
        if tools:
            kwargs["tools"] = tools
            if tool_choice is not None:
                kwargs["tool_choice"] = tool_choice

        istemci = self.client.with_options(timeout=timeout) if timeout is not None else self.client
        resp = istemci.chat.completions.create(**kwargs)
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

        global _SAGLAM_MODEL
        sirali = []

        def _ekle(ad):
            if ad and ad not in sirali and not _bozuk_mu(ad):
                sirali.append(ad)

        # Once bu surecte CALISAN model, sonra istemcinin modeli, sonra
        # katalog sirasi. 404 alan aday 30 dk atlanir (bkz. modul basi).
        _ekle(_SAGLAM_MODEL)
        _ekle(self.model)
        for aday in TERCIH_SIRASI:
            _ekle(aday)

        son_hata = None
        for model_adi in sirali:
            try:
                yanit = self._tek_model(
                    model_adi, messages, tools=tools,
                    tool_choice=tool_choice)
                if (tools and tool_choice == "required"
                        and not (yanit.get("tool_calls")
                                 if isinstance(yanit, dict) else None)):
                    raise RuntimeError("Kilo required tool_call yok")
                self.model = model_adi
                _SAGLAM_MODEL = model_adi
                return yanit
            except Exception as e:
                son_hata = e
                _isaretle_bozuk(model_adi, e)
                if _kilo_global_kota_mi(e):
                    raise
                if not _model_yedegi_gerekir_mi(e):
                    raise
                logger.warning(
                    "Kilo %s gecici/model hatasi, siradaki free model: %s",
                    model_adi, str(e))

        raise RuntimeError(
            "Kilo ücretsiz modellerinin hiçbiri cevap vermedi"
            + (" (son hata: %s)" % son_hata if son_hata else "")
        ) from son_hata
