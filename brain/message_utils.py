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


def _tool_calls_temizle(tool_calls, provider="", kaynak_provider=""):
    """Provider-ozel nested metadata'yi failover'da diger uca sizdirma."""
    sonuc = []
    ayni = bool(
        not kaynak_provider or not provider or kaynak_provider == provider
    )
    for c in tool_calls or []:
        if not isinstance(c, dict):
            continue
        f = c.get("function")
        if not isinstance(f, dict):
            # Eski/gecmis minimal kaydi genisletme; oldugu gibi koru.
            yeni = dict(c)
            if not ayni:
                yeni.pop("extra_content", None)
            sonuc.append(yeni)
            continue
        yeni = {
            "id": c.get("id") or "",
            "type": c.get("type") or "function",
            "function": {
                "name": f.get("name") or "",
                "arguments": f.get("arguments") or "{}",
            },
        }
        if ayni and "extra_content" in c:
            yeni["extra_content"] = c["extra_content"]
        sonuc.append(yeni)
    return sonuc


def mesajlari_temizle(messages: list, provider="") -> list:
    """Mesaj listesini hedef provider'a uyumlu ortak protokole indirger.

    Standard tool_call kimligi/adi/argumani her provider gecisinde korunur.
    Reasoning ve nested provider metadata yalniz kaynagi ayni provider ise
    tasinir; provider yerel provenance alani API'ye ASLA gonderilmez.
    """
    temiz = []
    for m in messages:
        if not isinstance(m, dict):
            continue
        kaynak_provider = str(m.get("_provider") or "")
        ayni_provider = bool(
            not kaynak_provider or not provider or kaynak_provider == provider
        )
        kopya = {"role": m.get("role", "user")}
        icerik = m.get("content")

        if icerik is None:
            kopya["content"] = ""
        elif isinstance(icerik, str):
            kopya["content"] = icerik
        elif isinstance(icerik, list):
            parcalar = []
            for p in icerik:
                if isinstance(p, dict):
                    t = p.get("text", "")
                    parcalar.append(
                        t if isinstance(t, str)
                        else str(t) if t is not None else ""
                    )
                elif isinstance(p, str):
                    parcalar.append(p)
                elif p is None:
                    parcalar.append("")
                else:
                    parcalar.append(str(p))
            kopya["content"] = " ".join(parcalar)
        else:
            kopya["content"] = str(icerik)

        if "tool_calls" in m:
            kopya["tool_calls"] = _tool_calls_temizle(
                m["tool_calls"], provider=provider,
                kaynak_provider=kaynak_provider,
            )
        if "tool_call_id" in m:
            kopya["tool_call_id"] = m["tool_call_id"]
        if "name" in m:
            kopya["name"] = m["name"]

        if ayni_provider:
            for alan in _REASONING_ALANLARI:
                if alan in m:
                    kopya[alan] = m[alan]

        temiz.append(kopya)
    return temiz

