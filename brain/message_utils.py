"""brain/message_utils.py — Mesaj formatı temizleme yardımcıları.

Tüm bulut adaptörleri bu fonksiyonu kullanarak mesajların
API'ye uygun formatta olduğundan emin olur.

Cloudflare API'si content alanının string olmasını zorunlu kılar.
Diğer OpenAI-uyumlu adaptörler genellikle daha esnektir ama
defensive sanitizasyon her zaman güvenlidir.
"""

import json


_REASONING_ALANLARI = ("reasoning_content", "reasoning",
                       "reasoning_details", "thinking",
                       "reasoning_text")


def reasoning_ayikla(msg) -> dict:
    """Saglayici yanitindaki reasoning alanlarini dict olarak dondurur.

    OpenAI-uyumlu yanitlarda reasoning baska adlarda gelebilir:
    reasoning_content (GLM/DeepSeek), reasoning_details (OpenRouter),
    reasoning (genel). Varsa aynen tasinir, yoksa bos dict.
    """
    out = {}
    for alan in _REASONING_ALANLARI:
        try:
            deger = getattr(msg, alan, None)
        except Exception:
            deger = None
        if deger not in (None, "", [], {}):
            out[alan] = deger
    return out


def mesajlari_temizle(messages: list) -> list:
    """Mesaj listesini API-uyumlu formata dönüştürür.

    Tüm content alanlarının string olduğundan emin olur.
    None content → boş string
    Array content → string'e çevir
    Dict content → string'e çevir

    Dönüş: Temizlenmiş mesaj listesi (orijinali değiştirmez).
    """
    temiz = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        kopya = {"role": m.get("role", "user")}
        icerik = m.get("content")

        if icerik is None:
            kopya["content"] = ""
        elif isinstance(icerik, str):
            kopya["content"] = icerik
        elif isinstance(icerik, list):
            # Array content → string'e çevir. 2026-09-10: parca icindeki
            # "text" her zaman string DEGILDIR (bazi saglayicilar sayi/
            # None/karisik blok doner) — join patliyordu ("sequence item
            # N: expected str instance"). Hepsi zorla stringe cevrilir.
            parcalar = []
            for p in icerik:
                if isinstance(p, dict):
                    t = p.get("text", "")
                    parcalar.append(t if isinstance(t, str) else str(t)
                                    if t is not None else "")
                elif isinstance(p, str):
                    parcalar.append(p)
                elif p is None:
                    parcalar.append("")
                else:
                    parcalar.append(str(p))
            kopya["content"] = " ".join(parcalar)
        else:
            kopya["content"] = str(icerik)

        # Tool calls ve tool_call_id korunur
        if "tool_calls" in m:
            kopya["tool_calls"] = m["tool_calls"]
        if "tool_call_id" in m:
            kopya["tool_call_id"] = m["tool_call_id"]
        if "name" in m:
            kopya["name"] = m["name"]

        # Reasoning zinciri korunur (P0): modelin ilk muhakemesi arac
        # turundan sonra kaybolmamali. Destekleyen saglayici alanlari
        # aynen tasinir; desteklemeyen yok sayar. Guvenlik disiplini
        # degil, model verisi tasimadir.
        for alan in ("reasoning_content", "reasoning",
                     "reasoning_details", "thinking",
                     "reasoning_text"):
            if alan in m and alan not in kopya:
                kopya[alan] = m[alan]

        temiz.append(kopya)
    return temiz
