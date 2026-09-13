"""chat/flow.py — Ana sohbet akışı.

Araçlar her normal turda modele sunulur. Hangi aracın gerekip gerekmediğine,
hangisinin kullanılacağına ve araçtan sonra ne yapılacağına model karar verir.
Kullanıcı metnini sınıflandıran araç filtresi veya araç için ayrı bağlam yoktur.
"""

import json
import logging

from chat.prompts import (KIMLIK_BLOGU, OLCU_YONLENDIRME,
                          BIKIMLONDIRME_YONLENDIRME)
from chat import context as ctx
from chat.gate import temizle as _temizle

logger = logging.getLogger(__name__)


def _j(obj):
    return json.dumps(obj, ensure_ascii=False)


def _konusmaci_ayir(text):
    """Sesli girişte metnin sonuna eklenen [İsim] etiketini ayırır."""
    import re
    eslesme = re.search(r"\[([^\]]+)\]\s*$", text)
    if not eslesme:
        return text, None
    return text[:eslesme.start()].strip(), eslesme.group(1)


def _profil_blogu():
    """Mevcut kalıcı profili bağlama ekler; kullanıcı metnini yorumlamaz."""
    try:
        from memory.profil import blok
        motor = ctx.hafiza_al()
        return blok(motor) if motor else ""
    except Exception as e:
        logger.warning("Profil okunamadi: %s", e)
        return ""


def _baglam_kur(text, system_prompt, konusmaci):
    """Modele gidecek sistem ve kişisel bağlamı kurar."""
    tam_prompt = system_prompt + OLCU_YONLENDIRME + BIKIMLONDIRME_YONLENDIRME
    if konusmaci:
        tam_prompt += "\nKonuşan: %s" % konusmaci

    mesajlar = [
        {"role": "system", "content": KIMLIK_BLOGU},
        {"role": "system", "content": tam_prompt},
    ]

    anilar = ctx.ilgili_anilar(text)
    if anilar:
        blok = "\n".join("- %s" % a["text"] for a in anilar)
        mesajlar.append({"role": "system", "content": "Hafızadan:\n" + blok})

    profil_blogu = _profil_blogu()
    if profil_blogu:
        mesajlar.append({"role": "system", "content": profil_blogu})

    return mesajlar


def _kaydet(text, cevap, kaynak, gecmis, js_callback, konusmaci):
    """Cevabı ekrana basar, geçmişe ve kalıcı hafızaya yazar."""
    gecmis += [
        {"role": "user", "content": text, "oturum": ctx.OTURUM_ID},
        {"role": "assistant", "content": cevap, "oturum": ctx.OTURUM_ID},
    ]
    ctx.kaydet(ctx.HISTORY_FILE, gecmis[-40:])

    try:
        from chat import oturum
        oturum.kaydet_cift(text, cevap)
    except Exception as e:
        logger.warning("Oturum kaydi atlandi: %s", e)

    js_callback("BasakUI.bitir(" + _j(cevap) + ", " + _j(kaynak) + ")")

    motor = ctx.hafiza_al()
    if motor and cevap:
        try:
            motor.episodik_kaydet(text, cevap, speaker=konusmaci or "",
                                  onem=ctx.onem_puanla(text))
        except Exception as e:
            logger.warning("Ani kaydedilemedi: %s", e)


def mesaj_isle(text, brain, system_prompt, js_callback, tools=None):
    """Bir mesajı baştan sona işler."""
    text, konusmaci = _konusmaci_ayir((text or "").strip())

    js_callback("BasakUI.thinking()")
    if not text:
        js_callback("BasakUI.error(" + _j("Bos mesaj") + ")")
        return

    modeller = brain.yerel_modeller()
    if not modeller and not brain.bulut_musait():
        js_callback("BasakUI.error(" + _j(
            "Hicbir beyin yok: Ollama kapali ve bulut anahtarlari da "
            "hazir degil") + ")")
        return

    model = ctx.yukle(ctx.SETTINGS_FILE, {}).get("model")
    if modeller:
        if model not in modeller:
            model = modeller[0]
    else:
        model = None

    gecmis = ctx.temizle_history(
        [m for m in ctx.yukle(ctx.HISTORY_FILE, [])
         if m.get("role") != "system"])

    araclar_var = bool(tools)
    mesajlar = _baglam_kur(text, system_prompt, konusmaci)
    mesajlar += ctx.gecmis_pencere(gecmis) + [
        {"role": "user", "content": text}]

    from brain.yayin import AracIstegi, SonHata

    yayin = None if araclar_var else getattr(brain, "cevapla_yayin", None)
    if yayin is not None:
        try:
            parcalar = []
            kaynak = ""
            for kaynak, parca in yayin(mesajlar, model):
                parcalar.append(parca)
                js_callback("BasakUI.parca(" + _j(parca) + ")")
            tam = _temizle("".join(
                p if isinstance(p, str) else str(p) if p is not None else ""
                for p in parcalar))
            if tam:
                _kaydet(text, tam, kaynak or "bulut", gecmis, js_callback,
                        konusmaci)
                return
            logger.info("Akis bos dondu, tek seferlik yola dusuluyor")
        except AracIstegi:
            logger.info("Model arac istedi — tek seferlik yola dusuluyor")
        except SonHata as e:
            logger.info("Akis acilamadi (%s) — tek seferlik yol", e.ozet)

    try:
        yanit, kaynak = brain.cevapla(
            mesajlar, model, tools=(tools if araclar_var else None))
    except Exception as e:
        hata = str(e)
        if "429" in hata or "rate" in hata.lower():
            js_callback("BasakUI.error(" + _j(
                "Cok fazla istek, biraz bekle") + ")")
        else:
            js_callback("BasakUI.error(" + _j(
                "Beyin hatasi: " + hata[:150]) + ")")
        return

    tool_calls = yanit.get("tool_calls") if isinstance(yanit, dict) else None
    if tool_calls and tools:
        from chat.tools import arac_dongusu
        from tools import calistir

        cevap, kosan = arac_dongusu(
            tool_calls, mesajlar, brain, model, js_callback, calistir,
            tools=tools)
        cevap = _temizle(cevap)
        if cevap:
            _kaydet(text, cevap, kaynak, gecmis, js_callback, konusmaci)
            return
        logger.info("Arac turu bos dondu (%d arac kostu)", kosan)

    cevap = _temizle(yanit.get("content", "") if isinstance(yanit, dict)
                     else yanit)
    if not cevap:
        js_callback("BasakUI.error(" + _j("Model bos cevap dondu") + ")")
        return

    _kaydet(text, cevap, kaynak, gecmis, js_callback, konusmaci)
