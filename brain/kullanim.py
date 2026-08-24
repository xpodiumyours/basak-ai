"""brain/kullanim.py — Token kullanımı çıkarımı (2026-08-24).

Casper'in tespiti: stats.py'de token_in/token_out alanları hazırdı ama
hiçbir adaptör doldurmuyordu; Groq'un 200k/gün limiti "80 istek" diye
tahmin ediliyordu. Gerçek token havuzu yönetiminin ön koşulu, her çağrının
gerçek token tüketimini ölçmektir.

İki yanıt biçimi desteklenir:
- OpenAI-SDK uyumlu: resp.usage.{prompt_tokens, completion_tokens}
  (groq, glm, nvidia, kilo, openrouter, cloudflare, gemini, qwen)
- Cohere yerel SDK: resp.meta.tokens.{input_tokens, output_tokens}
"""


def openai_kullanim(resp):
    """Yanıttan kullanım bilgisini çıkarır; yoksa None döner.

    Dönüş: {"giris": int, "cikis": int}
    """
    u = getattr(resp, "usage", None)
    if u is not None:
        giris = getattr(u, "prompt_tokens", 0) or 0
        cikis = getattr(u, "completion_tokens", 0) or 0
        if isinstance(giris, dict) or isinstance(cikis, dict):
            giris = cikis = 0
    else:
        # Cohere bicimi
        meta = getattr(resp, "meta", None)
        tok = getattr(meta, "tokens", None) if meta is not None else None
        if tok is None:
            if isinstance(resp, dict):
                u = resp.get("usage")
                if u is None:
                    return None
                giris = u.get("prompt_tokens") or 0
                cikis = u.get("completion_tokens") or 0
            else:
                return None
        else:
            giris = getattr(tok, "input_tokens", 0) or 0
            cikis = getattr(tok, "output_tokens", 0) or 0

    try:
        giris, cikis = int(giris), int(cikis)
    except (TypeError, ValueError):
        return None
    if giris <= 0 and cikis <= 0:
        return None
    return {"giris": giris, "cikis": cikis}


def kullanim_ekle(yanit, resp):
    """Adaptör dönüşüne _kullanim bilgisini ekler; yanıtı döndürür."""
    try:
        k = openai_kullanim(resp)
    except Exception:            # olcum hicbir zaman sohbeti bozmasin
        return yanit
    if k:
        yanit["_kullanim"] = k
    return yanit
