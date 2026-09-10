"""chat/flow.py — Ana akış orkestrasyonu modülü.

mesaj_isle ve mesaj_isle_orkestra fonksiyonlarının çekirdek mantığı.
Backward compatibility: _chat_legacy.py'den import edilir.

Bağımlılıklar: json, re (standart)
Circular import çözümü: lazy import ile _chat_legacy'den bağımlılıklar alınır.
"""

import json
import logging
import re

from chat.prompts import KIMLIK_BLOGU, OLCU_YONLENDIRME

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
        yukle, kaydet, SETTINGS_FILE, HISTORY_FILE,
        _temizle_history,
        TOOL_YONLENDIRME, BIKIMLONDIRME_YONLENDIRME,
        _ilgili_anilar, _gecmis_pencere,
        _yapi_kwargi,
        _save_and_reply, _onem_puanla,
        _hafiza_al,
    )
    from chat.gate import temizle as _temizle_fn
    from chat.tools import tool_calling_multi, ham_tool_call_ayir
    from tools import calistir
    from brain.kapasite import mod_kapasite

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

    # KALICI PROFIL (2026-09-09, Casper karari): konusarak ogrenme.
    # "benim adim X", "hatirla: ...", "X'i seviyorum" gibi acik
    # cumleler profile yazilir (budanmaz, silinmez). "unut: X" profilden
    # siler. Ogrenilenler/sonuclar ayni turun baglamina not dusulur ki
    # model dogrulayabilsin ("tamam, adini ogrendim" diyebilsin).
    ogrenme_notu = ""
    try:
        from chat.context import hafiza_al as _profil_motoru
        from memory.profil import ogren as _ogren, unut as _unut, blok as _blok
        _motor = _profil_motoru()
        if _motor and text:
            silinen = _unut(_motor, text)
            if silinen == -1:
                ogrenme_notu = ("Not: Casper hakkındaki tüm profil "
                                "bilgilerini SİLDİN. Bunu doğrula.")
            elif silinen:
                ogrenme_notu = ("Not: profilden %d kayıt sildin "
                                "(istek: %s). Bunu doğrula." % (silinen, text))
            else:
                yeniler = _ogren(_motor, text,
                                 speaker=aktif_konusmaci or "")
                if yeniler:
                    ogrenme_notu = ("Not: profile yeni bilgi eklendi: %s. "
                                    "Kısaca doğrulayıp sohbete devam et."
                                    % "; ".join("%s=%s" % (a, d)
                                                for a, d in yeniler))
            _profil_blogu = _blok(_motor)
        else:
            _profil_blogu = ""
    except Exception as e:
        logger.warning("Profil ogrenme atlandi: %s", e)
        ogrenme_notu = ""
        _profil_blogu = ""

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
    if modeller:
        if model not in modeller:
            model = modeller[0]
    else:
        # Yerel model yok — ayarlar.json'daki yerel model adi bulut
        # zincirine tasınmasın; zincir kendi seçsin.
        model = None

    raw_gecmis = [m for m in yukle(HISTORY_FILE, []) if m.get("role") != "system"]
    gecmis = _temizle_history(raw_gecmis)

    mevcut_kaynaklar = [ad for ad, _ in brain._bulut_zinciri()] if hasattr(brain, "_bulut_zinciri") else []
    kap = mod_kapasite(kaynaklar=mevcut_kaynaklar, model_adi=model)

    # 2026-08-26: Prompt zinciri sadelestirildi.
    # System prompt (KISILIK) + tool/bicimlendirme yonnergeleri.
    # ONEMLI: TOOL_YONLENDIRME (arac dayatmasi) HER MODELDE KALIR —
    # ucretsiz modeller araci ellerinde tutsalar da "kullan" talimati
    # almazsa dosya sorularinda arac cagirmaz, kafalarindan uydurur.
    # Hafif mod (kap.kucuk) yalniz token yiyen kisimlari azaltir:
    # hafiza embedding'i atlanir, core arac kucuk tutulur, tool dongusu
    # kisalir. Arac dayatmasi fonksiyoneldir, kesilmez.
    tam_prompt = system_prompt + TOOL_YONLENDIRME + OLCU_YONLENDIRME + BIKIMLONDIRME_YONLENDIRME
    if aktif_konusmaci:
        tam_prompt += "\nKonuşan: %s" % aktif_konusmaci
    mesajlar = [
        {"role": "system", "content": KIMLIK_BLOGU},
        {"role": "system", "content": tam_prompt},
    ]

    # 2026-08-25: hazir not yigini artik her mesaja eklenmiyor.
    # Sebep (olculdu): 2105 karakterlik knowledge dokumu her istege
    # giriyordu; icinde dosya adlari ve profil metni vardi. Araci
    # olmayan model bu metni VERI sanip oradan cevap uretiyordu —
    # "uydurma" diye kaydedilen olayin kaynagi buydu. Casper ayrica
    # kendisini anlatan hazir metni istemiyor: "baştan tanışacağım".
    # Notlar kayboldu degil: belge_ara/read_file ile ARAC uzerinden
    # okunur, boylece model neyin olcum neyin metin oldugunu bilir.

    # Hafiza: ilgili anilari baglama ekle (kisa format)
    # Kucuk modellerde embedding aramasi atlanir (ekstra cagri + baglam).
    if kap.kucuk:
        anilar = []
    else:
        anilar = _ilgili_anilar(text)
    if anilar:
        blok = "\n".join(
            "- %s" % a["text"][:300] for a in anilar[:5]  # max 5 anı
        )
        mesajlar.append({
            "role": "system",
            "content": "Hafızadan:\n" + blok,
        })

    # Kalici profil blogu + ogrenme notu (varsa)
    try:
        if _profil_blogu:
            mesajlar.append({"role": "system", "content": _profil_blogu})
        if ogrenme_notu:
            mesajlar.append({"role": "system", "content": ogrenme_notu})
    except NameError:
        pass

    mesajlar += _gecmis_pencere(gecmis) + [{"role": "user", "content": text}]

    # AKIS (2026-09-10): once aracsiz akis dene — cevap kelime kelime
    # gelsin, "dondu mu?" hissi bitsin. Model arac isterse AracIstegi
    # firlar, asagidaki tam yola dusulur. Akis acilmazsa SonHata ile
    # dogrudan hata gosterilir (tam yol TEKRAR kota yemez).
    from brain.yayin import AracIstegi as _AracIstegi, SonHata as _SonHata
    _yayin = getattr(brain, "cevapla_yayin", None)
    if _yayin is not None:
        try:
            _parcalar = []
            _kaynak = ""
            for _kaynak, _parca in _yayin(mesajlar, model):
                _parcalar.append(_parca)
                js_callback("BasakUI.parca(" + _j(_parca) + ")")
            _tam = _temizle_fn("".join(_parcalar))
            gecmis += [{"role": "user", "content": text},
                       {"role": "assistant", "content": _tam}]
            kaydet(HISTORY_FILE, gecmis[-40:])
            try:
                from chat import oturum as _oturum
                _oturum.kaydet_cift(text, _tam)
            except Exception as e:
                logger.warning("Oturum kaydi atlandi: %s", e)
            js_callback("BasakUI.bitir(" + _j(_tam) + ", "
                        + _j(_kaynak or "bulut") + ")")
            try:
                _motor2 = _hafiza_al()
                if _motor2 and _tam:
                    _motor2.episodik_kaydet(
                        text, _tam, speaker=aktif_konusmaci or "",
                        onem=_onem_puanla(text))
            except Exception as e:
                logger.warning("Akis anisi kaydedilemedi: %s", e)
            return
        except _AracIstegi:
            pass  # tam yola dus: arac + detayli cevap
        except _SonHata as e:
            js_callback("BasakUI.error(" + _j(
                "Beyin hatasi: " + str(e.ozet)[:100]) + ")")
            return

    # 2026-08-26: CORE TOOLS — ucretsiz modeller 18 araci cozemez.
    # Core set (9 arac) her zaman gonderilir; extended tools
    # anahtar kelimeyle tetiklenir. Tam set istenirse ?full yazilir.
    if tools:
        from tools.definitions import CORE_TOOL_NAMES, SMALL_CORE_TOOL_NAMES, EXTENDED_TETIKLERI
        core_names = SMALL_CORE_TOOL_NAMES if kap.kucuk else CORE_TOOL_NAMES
        core = [t for t in tools
                if t["function"]["name"] in core_names]
        # Extended: mesajdaki anahtar kelimelerle tetiklenenler
        text_lower = text.lower()
        for ext_name, tetikler in EXTENDED_TETIKLERI.items():
            if any(t in text_lower for t in tetikler):
                for t in tools:
                    if t["function"]["name"] == ext_name:
                        core.append(t)
                        break
        aktif_toollar = core if core else tools
    else:
        aktif_toollar = None

    try:
        yanit, kaynak = brain.cevapla(
            mesajlar, model,
            tools=aktif_toollar,
            **_yapi_kwargi(brain))
    except Exception as e:
        hata_str = str(e)
        if "429" in hata_str or "rate" in hata_str.lower():
            js_callback("BasakUI.error(" + _j("Cok fazla istek, biraz bekle") + ")")
        else:
            js_callback("BasakUI.error(" + _j("Beyin hatasi: " + hata_str[:100]) + ")")
        return

    tool_calls = yanit.get("tool_calls")

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
            _save_and_reply(text, cevap, kaynak, gecmis, js_callback,
                            speaker=aktif_konusmaci,
                            onem=_onem_puanla(text, arac_ciktilari))
            return

        _save_and_reply(text, cevap, kaynak, gecmis, js_callback,
                        speaker=aktif_konusmaci,
                        onem=_onem_puanla(text))
        return

    # Tool calling döngüsü
    cevap, arac_ciktilari = tool_calling_multi(
        tool_calls, mesajlar, brain, model, js_callback, calistir,
        aktif_toollar)
    cevap = _temizle_fn(cevap)
    _save_and_reply(text, cevap, kaynak, gecmis, js_callback,
                    speaker=aktif_konusmaci,
                    onem=_onem_puanla(text, arac_ciktilari))
