"""chat/flow.py — Ana sohbet akışı.

2026-09-13 (Casper kararı): ölçü kapısı, orkestra ve araçların etrafına
sarılmış kural katmanları söküldü. Geriye sekiz salt-okunur araç kaldı.

Tek yol var; ayrımı MODEL yapar:

    mesaj → bağlam + araç şeması → zincir → akış başlar
              ├─ düz sohbet ise: kelime kelime akar → ekran
              └─ ölçüm gerekiyorsa: model araç ister → araç koşar
                 → sonuç modele döner → özet → ekran

2026-09-13: araçları kelime listesiyle açıp kapatan katman KALDIRILDI
(Casper kararı) — o liste, araçların etrafına sarılmış bir kural
katmanıydı ve gerekçesi ölçülünce çürüdü: groq/glm/nvidia üçü de
akışla birlikte araç kabul ediyor, bulut zincirinde de "küçük model"
yok. Aracı model seçer.

Sağlayıcı sırası, kota takibi ve "limiti bitince diğerine geç" mantığı
bu dosyada DEĞİL — `brain/` altında. Burası yalnız bağlamı kurar.
"""

import json
import logging
import re

from chat.prompts import KIMLIK_BLOGU
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


def _profil_isle(text, konusmaci):
    """Kalıcı profili günceller. Dönüş: (profil_blogu, ogrenme_notu).

    'benim adım X', 'hatırla: ...' gibi cümleler profile yazılır;
    'unut: X' siler. Öğrenilen şey aynı turun bağlamına not düşülür ki
    model "tamam, adını öğrendim" diyebilsin.
    """
    try:
        from memory.profil import ogren, unut, blok
        motor = ctx.hafiza_al()
        if not motor or not text:
            return "", ""

        silinen = unut(motor, text)
        if silinen == -1:
            not_ = ("Not: Casper hakkındaki tüm profil bilgilerini "
                    "SİLDİN. Bunu doğrula.")
        elif silinen:
            not_ = ("Not: profilden %d kayıt sildin (istek: %s). "
                    "Bunu doğrula." % (silinen, text))
        else:
            yeniler = ogren(motor, text, speaker=konusmaci or "")
            not_ = ""
            if yeniler:
                not_ = ("Not: profile yeni bilgi eklendi: %s. Kısaca "
                        "doğrulayıp sohbete devam et."
                        % "; ".join("%s=%s" % (a, d) for a, d in yeniler))
        return blok(motor), not_
    except Exception as e:
        logger.warning("Profil islenemedi: %s", e)
        return "", ""


def _baglam_kur(text, system_prompt, konusmaci, araclar_acik=False):
    """Modele gidecek mesaj listesini kurar."""
    profil_blogu, ogrenme_notu = _profil_isle(text, konusmaci)

    tam_prompt = system_prompt
    if konusmaci:
        tam_prompt += "\nKonuşan: %s" % konusmaci

    mesajlar = [
        {"role": "system", "content": KIMLIK_BLOGU},
        {"role": "system", "content": tam_prompt},
    ]

    # Hafıza: soruyla ilgili anılar. knowledge/ notlarına erişim de bu
    # yoldan olur — motor o klasörü indeksliyor.
    #
    anilar = ctx.ilgili_anilar(text)
    if anilar:
        blok = "\n".join("- %s" % a["text"] for a in anilar)
        mesajlar.append({"role": "system", "content": "Hafızadan:\n" + blok})

    if profil_blogu:
        mesajlar.append({"role": "system", "content": profil_blogu})
    if ogrenme_notu:
        mesajlar.append({"role": "system", "content": ogrenme_notu})

    return mesajlar


def _kaydet(text, cevap, kaynak, gecmis, js_callback, konusmaci):
    """Cevabı ekrana basar, geçmişe ve kalıcı hafızaya yazar."""
    gecmis += [
        {"role": "user", "content": text, "oturum": ctx.OTURUM_ID},
        {"role": "assistant", "content": cevap, "oturum": ctx.OTURUM_ID},
    ]
    ctx.kaydet(ctx.HISTORY_FILE, gecmis)

    try:
        from chat import oturum
        oturum.kaydet_cift(text, cevap)
    except Exception as e:
        logger.warning("Oturum kaydi atlandi: %s", e)

    js_callback("BasakUI.bitir(" + _j(cevap) + ", " + _j(kaynak) + ")")

    # Ekran güncellendikten SONRA anıyı yaz — cevabı bekletmesin.
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

    # Yerel model YOKSA ve bulut da yoksa duracağız. Yalnız yerelin
    # kapalı olması sohbeti kesmez — bulut zinciri ayakta olabilir.
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
        # Yerel model yok — ayarlardaki ad bulut zincirine taşınmasın.
        model = None

    gecmis = ctx.temizle_history(
        [m for m in ctx.yukle(ctx.HISTORY_FILE, [])
         if m.get("role") != "system"])

    # 2026-09-13 (Casper karari): kelime listesiyle tetikleme KALKTI.
    # O liste, araclarin etrafina sarilmis bir kural katmaniydi — bu
    # gece soktugumuz seyin aynisi. Gerekcesi de olculunce curudu:
    # (a) groq/glm/nvidia ucu de akisla birlikte tools kabul ediyor,
    # (b) bulut zincirinde "kucuk model" yok; tek kucuk olan yerel
    # qwen2.5:7b ve o zaten son care. Artik araci MODEL secer.
    arac_acik = bool(tools)
    mesajlar = _baglam_kur(text, system_prompt, konusmaci, arac_acik)

    mesajlar += ctx.gecmis_pencere(gecmis) + [{"role": "user",
                                               "content": text}]

    # ── Akan cevap ──────────────────────────────────────────────────
    # Cevap kelime kelime gelsin ("dondu mu?" hissi olmasın). Akış
    # açılamazsa tek seferlik yola düşülür.
    from brain.yayin import AracIstegi, SonHata

    # Akis ARACLARLA birlikte kosar: model duz sohbette metin akitir,
    # olcum gerekiyorsa arac ister (AracIstegi) ve asagidaki tam yola
    # dusulur. Karari model verir, kod degil.
    yayin = getattr(brain, "cevapla_yayin", None)
    if yayin is not None:
        try:
            parcalar = []
            kaynak = ""
            for kaynak, parca in yayin(mesajlar, model, tools=tools):
                parcalar.append(parca)
                js_callback("BasakUI.parca(" + _j(parca) + ")")
            # Bazi saglayicilar sayi/None parca dondurur — join patlamasin.
            tam = _temizle("".join(
                p if isinstance(p, str) else str(p) if p is not None else ""
                for p in parcalar))
            if tam:
                _kaydet(text, tam, kaynak or "bulut", gecmis, js_callback,
                        konusmaci)
                return
            logger.info("Akis bos dondu, tek seferlik yola dusuluyor")
        except AracIstegi:
            logger.info("Model arac istedi — tam yola dusuluyor")
        except SonHata as e:
            logger.info("Akis acilamadi (%s) — tek seferlik yol", e.ozet)

    # ── Tek seferlik yol ────────────────────────────────────────────
    # Akış hiç açılamadıysa buraya düşülür. Akış açılamadığı için
    # sağlayıcıdan başarılı çağrı gerçekleşmedi — kota yenmedi.
    try:
        yanit, kaynak = brain.cevapla(
            mesajlar, model, tools=(tools if arac_acik else None))
    except Exception as e:
        hata = str(e)
        if "429" in hata or "rate" in hata.lower():
            js_callback("BasakUI.error(" + _j(
                "Cok fazla istek, biraz bekle") + ")")
        else:
            js_callback("BasakUI.error(" + _j(
                "Beyin hatasi: " + hata) + ")")
        return

    # ── Araç turu ───────────────────────────────────────────────────
    # Model araç istediyse kod çalıştırır, sonucu modele geri verir,
    # model özetler. Beyaz liste dışı ad buraya kadar gelse bile koşmaz.
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
