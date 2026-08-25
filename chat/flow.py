"""chat/flow.py — Ana akış orkestrasyonu modülü.

mesaj_isle ve mesaj_isle_orkestra fonksiyonlarının çekirdek mantığı.
Backward compatibility: _chat_legacy.py'den import edilir.

Bağımlılıklar: json, re (standart)
Circular import çözümü: lazy import ile _chat_legacy'den bağımlılıklar alınır.
"""

import json
import logging
import re

logger = logging.getLogger(__name__)


def _j(obj):
    """JSON serialization helper."""
    return json.dumps(obj, ensure_ascii=False)


def mesaj_isle_yeni(text, brain, system_prompt, js_callback, tools):
    """mesaj_isle'nin yeni versiyonu — _chat_legacy.py'den bağımsız.

    Circular import önlemek için _chat_legacy'den bağımlılıklar
    lazy import ile alınır.
    """
    # Lazy imports (circular import önlemi)
    from _chat_legacy import (
        orkestra_aktif_mi, mesaj_isle_orkestra,
        yukle, SETTINGS_FILE, HISTORY_FILE,
        _temizle_history, _SOZLESME_MODU,
        TOOL_YONLENDIRME, OLCU_YONLENDIRME,
        _knowledge_lock, _knowledge_cache,
        _ilgili_anilar, _gecmis_pencere,
        _dinamik_araclar, _TOOL_KELIMELERI,
        _yapi_kwargi, _kapidan_gecir,
        _save_and_reply, _onem_puanla,
    )
    from olcu import PROMPT_BLOGU, SOZLESME_PROMPTU, YEDEK_CUMLE, HAM_BASLIK, ham_olcum_satirlari
    from chat.gate import temizle as _temizle_fn, ingilizce_sizinti_mi
    from chat.tools import tool_calling_multi, ham_tool_call_ayir, TUR_SINIRI
    from tools import calistir

    # ORKESTRA ana yolu
    if orkestra_aktif_mi():
        mesaj_isle_orkestra(text, brain, system_prompt, js_callback,
                            tools, kaydet_acik=True)
        return

    text = (text or "").strip()

    # Konuşmacı bilgisini çıkar
    aktif_konusmaci = None
    konusmaci_eslesme = re.search(r"\[([^\]]+)\]\s*$", text)
    if konusmaci_eslesme:
        aktif_konusmaci = konusmaci_eslesme.group(1)
        text = text[:konusmaci_eslesme.start()].strip()

    js_callback("BasakUI.thinking()")
    if not text:
        js_callback("BasakUI.error(" + _j("Bos mesaj") + ")")
        return

    # Beyin kontrolü
    modeller = brain.yerel_modeller()
    if not modeller and not brain.bulut_musait():
        js_callback("BasakUI.error(" + _j(
            "Hicbir beyin yok: Ollama kapali ve bulut anahtarlari da hazir degil") + ")")
        return

    model = yukle(SETTINGS_FILE, {}).get("model")
    if modeller and model not in modeller:
        model = modeller[0]

    raw_gecmis = [m for m in yukle(HISTORY_FILE, []) if m.get("role") != "system"]
    gecmis = _temizle_history(raw_gecmis)

    # Sözleşme bloğu
    sozlesme_bloku = (PROMPT_BLOGU if _SOZLESME_MODU == "kapali"
                      else SOZLESME_PROMPTU)
    tam_prompt = (system_prompt + TOOL_YONLENDIRME + OLCU_YONLENDIRME
                  + sozlesme_bloku)
    if aktif_konusmaci:
        tam_prompt += "\n\n[ANLIK DURUM] An itibarıyla konuşan kişi: %s. Ona göre hitap et." % aktif_konusmaci
    mesajlar = [{"role": "system", "content": tam_prompt}]

    with _knowledge_lock:
        bilgi = _knowledge_cache
    if bilgi:
        mesajlar.append({
            "role": "system",
            "content": "Casper'in notlari:\n\n" + bilgi,
        })

    anilar = _ilgili_anilar(text)
    if anilar:
        blok = "\n\n".join(
            "- %s (kaynak: %s)" % (a["text"][:500], a["source"] or a["kind"])
            for a in anilar
        )
        mesajlar.append({
            "role": "system",
            "content": (
                "Hafizandaki ilgili anilar ve notlar:\n\n" + blok
            ),
        })

    mesajlar += _gecmis_pencere(gecmis) + [{"role": "user", "content": text}]

    # Dinamik araçlar
    if tools:
        aktif_toollar = _dinamik_araclar(text.lower(), tools)
    else:
        aktif_toollar = None

    # Ölçüm retry
    _OLCUM_KELIMELERI = tuple(_TOOL_KELIMELERI["git_durum"]) + \
        tuple(_TOOL_KELIMELERI["belge_ara"])
    olcum_aktif = any(k in text.lower() for k in _OLCUM_KELIMELERI)
    _GUCLU_MODEL = "openai/gpt-oss-120b"
    _retry = 0
    MAX_RETRY = 1

    while _retry <= MAX_RETRY:
        try:
            override = _GUCLU_MODEL if _retry > 0 and olcum_aktif else None
            yanit, kaynak = brain.cevapla(
                mesajlar, model,
                tools=aktif_toollar if aktif_toollar else None,
                override_model=override, **_yapi_kwargi(brain))
        except Exception as e:
            hata_str = str(e)
            if "429" in hata_str or "rate" in hata_str.lower():
                js_callback("BasakUI.error(" + _j("Cok fazla istek, biraz bekle") + ")")
            else:
                js_callback("BasakUI.error(" + _j("Beyin hatasi: " + hata_str[:100]) + ")")
            return

        tool_calls = yanit.get("tool_calls")
        if not tool_calls and olcum_aktif and _retry < MAX_RETRY:
            _retry += 1
            logger.info("Olcum retry #%d", _retry)
            continue
        break

    # Tool calls yoksa
    if not tool_calls:
        ham_icerik = yanit.get("content", "")
        cevap = _temizle_fn(ham_icerik)

        # Raw tool call yakalama (BUG #1 fix)
        raw_cagri_listesi = ham_tool_call_ayir(ham_icerik)
        if raw_cagri_listesi:
            logger.info("Raw tool call yakalandi: %s",
                        ", ".join(ad for ad, _ in raw_cagri_listesi))
            sahte_tool_calls = []
            for idx, (ad, args) in enumerate(raw_cagri_listesi):
                sahte_tool_calls.append({
                    "id": "raw_%d" % idx,
                    "type": "function",
                    "function": {
                        "name": ad,
                        "arguments": json.dumps(args, ensure_ascii=False),
                    },
                })
            cevap, arac_ciktilari = tool_calling_multi(
                sahte_tool_calls, mesajlar, brain, model, js_callback,
                calistir, aktif_toollar)
            cevap = _temizle_fn(cevap)
            cevap, _kapi = _kapidan_gecir(cevap, arac_ciktilari)
            if cevap.strip() == YEDEK_CUMLE:
                ham = ham_olcum_satirlari(arac_ciktilari)
                if ham:
                    cevap = HAM_BASLIK + "\n" + "\n".join(ham)
            _save_and_reply(text, cevap, kaynak, gecmis, js_callback,
                            speaker=aktif_konusmaci,
                            onem=_onem_puanla(text, arac_ciktilari))
            return

        # Dil kontrolü
        if cevap and ingilizce_sizinti_mi(cevap):
            try:
                telkin = mesajlar + [{
                    "role": "system",
                    "content": "SADECE TURKCE yaz. Ingilizce kelime ve cumle kullanma.",
                }]
                yanit2, kaynak2 = brain.cevapla(telkin, model)
                icerik2 = yanit2.get("content", "") if isinstance(yanit2, dict) else yanit2
                cevap2 = _temizle_fn(icerik2)
                if cevap2 and not ingilizce_sizinti_mi(cevap2):
                    cevap = cevap2
                    kaynak = kaynak2 + " (dil duzeltme)"
            except Exception:
                pass
            if ingilizce_sizinti_mi(cevap):
                logger.info("Ingilizce sizinti telkinden sonra da surdu")
                cevap = YEDEK_CUMLE

        cevap, _kapi = _kapidan_gecir(cevap, [])
        _save_and_reply(text, cevap, kaynak, gecmis, js_callback,
                        speaker=aktif_konusmaci,
                        onem=_onem_puanla(text))
        return

    # Tool calling döngüsü
    cevap, arac_ciktilari = tool_calling_multi(
        tool_calls, mesajlar, brain, model, js_callback, calistir,
        aktif_toollar)
    cevap = _temizle_fn(cevap)
    if cevap and ingilizce_sizinti_mi(cevap):
        logger.info("Ingilizce sizinti: model cevabi atildi")
        ham = ham_olcum_satirlari(arac_ciktilari)
        cevap = (HAM_BASLIK + "\n" + "\n".join(ham)) if ham else YEDEK_CUMLE
        _save_and_reply(text, cevap, kaynak, gecmis, js_callback,
                        speaker=aktif_konusmaci,
                        onem=_onem_puanla(text, arac_ciktilari))
        return
    cevap, _kapi = _kapidan_gecir(cevap, arac_ciktilari)
    if cevap.strip() == YEDEK_CUMLE:
        ham = ham_olcum_satirlari(arac_ciktilari)
        if ham:
            cevap = HAM_BASLIK + "\n" + "\n".join(ham)
    _save_and_reply(text, cevap, kaynak, gecmis, js_callback,
                    speaker=aktif_konusmaci,
                    onem=_onem_puanla(text, arac_ciktilari))
