"""brain/message_utils.py — Mesaj formatı temizleme yardımcıları.

Tüm bulut adaptörleri bu fonksiyonu kullanarak mesajların
API'ye uygun formatta olduğundan emin olur.

Cloudflare API'si content alanının string olmasını zorunlu kılar.
Diğer OpenAI-uyumlu adaptörler genellikle daha esnektir ama
defensive sanitizasyon her zaman güvenlidir.
"""

import json


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
            # Array content → string'e çevir
            parcalar = []
            for p in icerik:
                if isinstance(p, dict):
                    parcalar.append(p.get("text", str(p)))
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

        temiz.append(kopya)
    return temiz
