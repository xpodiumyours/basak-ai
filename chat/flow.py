"""chat/flow.py — Ana sohbet ve ajan akışı.

Kullanıcı mesajını kelime/niyet tablosuyla sınıflandıran bir router yoktur.
TOOLS verildiginde LLM önce `yetenek_ac` veya `son_cevap` seçer. Bir
yetenek alanı açılırsa yalnız o alanın gerçek araçları modele sunulur;
araç sonucunu gören model gerekirse yeni alan/araç seçerek devam eder.

    mesaj → LLM
              ├─ salt sohbet → son_cevap → ekran
              └─ gerçek iş → yetenek_ac → gerçek araç → sonuç → LLM
                                   ↑                       │
                                   └──── gerekirse devam ──┘

Araç/alan kararını kod değil model verir. Sağlayıcı uygunluğu, ücretsiz
kullanım ve kota/fallback mantığı `brain/` altındadır.
"""

import json
import logging
import re

from chat.prompts import KIMLIK_BLOGU
from chat.agent_protocol import AJAN_SOZLESMESI, baslangic_araclari
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
    """Kalıcı profili okur. Dönüş: (profil_blogu, ogrenme_notu).

    2026-09-13 sonrasi: ogrenme kapisi stub'dur (memory.profil.ogren
    hep [], unut hep 0) — cumle profili buyutmez/kucultmez; yalniz
    kayitli blok baglama tasinir. ogrenme_notu pratikte bostur.
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


def _baglam_kur(text, system_prompt, konusmaci):
    """Modele gidecek mesaj listesini kurar.

    2026-09-19: `araclar_acik` parametresi KALDIRILDI. Çağrılıyor ama
    gövdede hiç okunmuyordu — "araç durumuna göre bağlam kur" niyetinin
    yarım kalmış kalıntısıydı. Araç seçimini model yapar; bağlam kurucusu
    ona karışmaz.
    """
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
    # P1 provenance (2026-09-15): her aninin kaynagi/turu modele tasinir.
    # Kullanici sozu ile Basak'in eski cevabi ayni metinde karismaz;
    # kayit "sohbet gecmisi" olarak etiketlenir, kanit olarak degil.
    # Davranis talimati eklenmez — yalniz olgu etiketi.
    anilar = ctx.ilgili_anilar(text)
    if anilar:
        satirlar = []
        for a in anilar:
            _kaynak = (a.get("source") or "").strip()
            _tur = (a.get("kind") or "").strip()
            _etiket = "/".join([x for x in (_kaynak, _tur) if x])
            _metin = (a.get("text") or "").strip()
            if _etiket:
                satirlar.append("- [%s] %s" % (_etiket, _metin))
            else:
                satirlar.append("- %s" % _metin)
        mesajlar.append({"role": "system",
                         "content": "Hafızadan:\n" + "\n".join(satirlar)})

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
    try:
        ctx.kaydet(ctx.HISTORY_FILE, gecmis)
    except OSError as e:
        # Gecmis yazilamasa da ekran bitmeli (2026-09-15 checkup).
        logger.warning("Gecmis yazilamadi (ekran etkilenmez): %s", e)

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

    # Ozgu-ajan (Faz 2): SADECE bulut zinciri. Yerel model yok.
    # Bulut musait degilse dur; baska on kosul yok.
    if not brain.bulut_musait():
        js_callback("BasakUI.error(" + _j(
            "Hicbir beyin yok: bulut anahtarlari hazir degil") + ")")
        return

    # Zincirdeki bulut saglayici kendi modelini secer; disaridan
    # model adi tasiyarak karistirma.
    model = None

    gecmis = ctx.temizle_history(
        [m for m in ctx.yukle(ctx.HISTORY_FILE, [])
         if m.get("role") != "system"])

    # 2026-09-13 (Casper karari): kelime listesiyle tetikleme KALKTI.
    # O liste, araclarin etrafina sarilmis bir kural katmaniydi — bu
    # gece soktugumuz seyin aynisi. Gerekcesi de olculunce curudu:
    # (a) groq/glm/nvidia ucu de akisla birlikte tools kabul ediyor,
    # (b) zincirde kucuk/yerel model yok. Artik araci MODEL secer.
    arac_acik = bool(tools)
    mesajlar = _baglam_kur(text, system_prompt, konusmaci)

    if arac_acik:
        mesajlar.append({"role": "system", "content": AJAN_SOZLESMESI})

    mesajlar += ctx.gecmis_pencere(gecmis) + [{"role": "user",
                                               "content": text}]

    # ── Gercek ajan yolu ────────────────────────────────────────────
    # Uretim Brain'i ajan protokolunu destekliyorsa model her turda
    # function call yapmak zorundadir: gercek bir arac veya son_cevap.
    # Kelime/niyet siniflandiricisi YOKTUR; hangi araci kullanacagini
    # model secer. Zorunlu tool protokolunu dogrulamadigimiz saglayiciya
    # sessizce dusulmez — aksi halde sistem yeniden chatbot gibi davranir.
    if arac_acik and hasattr(brain, "ajan_musait"):
        if not brain.ajan_musait():
            js_callback("BasakUI.error(" + _j(
                "Ajan modu icin dogrulanmis arac protokollu ucretsiz "
                "bir beyin bagli degil") + ")")
            return

        ajan_tools = baslangic_araclari()
        try:
            yanit, kaynak = brain.cevapla(
                mesajlar, model, tools=ajan_tools, tool_choice="required")
        except Exception as e:
            hata = str(e)
            if "429" in hata or "rate" in hata.lower():
                js_callback("BasakUI.error(" + _j(
                    "Cok fazla istek, biraz bekle") + ")")
            else:
                js_callback("BasakUI.error(" + _j(
                    "Ajan beyni hatasi: " + hata) + ")")
            return

        tool_calls = (yanit.get("tool_calls")
                      if isinstance(yanit, dict) else None)
        if not tool_calls:
            # required protokolunde duz metin kabul edilmez. Bu kapi,
            # arac gerektiren isi yalniz anlatarak gecistirmeyi engeller.
            js_callback("BasakUI.error(" + _j(
                "Ajan protokolu bozuldu: model arac veya son_cevap "
                "cagirmadi") + ")")
            return

        from chat.tools import arac_dongusu
        from tools import calistir
        cevap, kosan = arac_dongusu(
            tool_calls, mesajlar, brain, model, js_callback, calistir,
            tools=ajan_tools, yanit=yanit, tool_choice="required",
            tum_tools=tools)
        cevap = _temizle(cevap)
        if cevap:
            _kaydet(text, cevap, kaynak, gecmis, js_callback, konusmaci)
            return

        logger.info("Ajan turu final cevap vermedi (%d arac kostu)", kosan)
        js_callback("BasakUI.error(" + _j(
            "Ajan gorevi final cevaba baglayamadi") + ")")
        return

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
        except AracIstegi as istek:
            # P0: streaming sirasinda modelin sectigi arac ve argumanlar
            # korunur; ayni soru ikinci kez modele dusundurulmez.
            # Dogrudan calistir, sonucu ayni zincirden devam ettir.
            _tc = getattr(istek, "tool_calls", None) or []
            _muh = getattr(istek, "muhakeme", None) or {}
            if _tc and tools:
                from chat.tools import arac_dongusu
                from tools import calistir
                logger.info("Model akista arac istedi — dogrudan calisiyor")
                try:
                    cevap, kosan = arac_dongusu(
                        _tc, mesajlar, brain, model, js_callback,
                        calistir, tools=tools,
                        yanit={"tool_calls": _tc, **_muh})
                except Exception as e:
                    logger.warning("Akis-arac turu basarisiz: %s", e)
                    cevap, kosan = "", 0
                cevap = _temizle(cevap)
                if cevap:
                    _kaydet(text, cevap, kaynak or "bulut", gecmis,
                            js_callback, konusmaci)
                    return
                logger.info("Akis-arac turu bos dondu (%d arac kostu)",
                            kosan)
                # Bos donduyse tek seferlik yola dusme: ayni soruyu
                # yeniden dusundurmek kota yer. Hata goster, cik.
                js_callback("BasakUI.error(" + _j(
                    "Model bos cevap dondu") + ")")
                return
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
            tools=tools, yanit=yanit)
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
