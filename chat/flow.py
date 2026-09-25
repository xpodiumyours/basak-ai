"""chat/flow.py — Basak provider-neutral ajan akisi.

P2 ortak mimari:
  mesaj -> full capability registry -> model-native function calling
                                  -> tool result -> ayni ajan dongusu -> final

Gizli resolver aktif akista YOKTUR. Tool discovery/deferred loading ileride
yalniz provider-native optimizasyon olabilir; desteklenmeyen provider hicbir
araci kaybetmez. tool_policy kullanici metninden tahmin edilmez; acik run
politikasidir (auto|required|none).
"""

import json
import logging

from chat.prompts import MISAFIR_BLOGU, kimlik_blogu
from chat.kimlik import VARSAYILAN_KULLANICI, aktif_kullanici, gorunur_ad
from chat.agent_runtime import (
    AGENT_CONTRACT, AgentRunState, capability_surface,
    emit_run_state, normalize_tool_policy,
)
from chat.output_control import (
    akan_ajan_adimi, akan_final, kesik_cevabi_bildir, kesik_mi,
)
from chat import context as ctx
from chat.gate import temizle as _temizle
from chat import onbellek as _onbellek

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


def _baglam_kur(text, system_prompt, konusmaci, ajan_sozlesmesi="",
                misafir=False):
    """Modele gidecek mesaj listesini kurar.

    2026-09-19: `araclar_acik` parametresi KALDIRILDI. Çağrılıyor ama
    gövdede hiç okunmuyordu — "araç durumuna göre bağlam kur" niyetinin
    yarım kalmış kalıntısıydı. Araç seçimini model yapar; bağlam kurucusu
    ona karışmaz.

    misafir=True ise varsayılan kullanıcıya ait hiçbir veri eklenmez:
    isim, profil, anı ve geçmiş taşınmaz. Bayrak URL'den gelir; metne bakılmaz.
    """
    if misafir:
        return [
            {"role": "system", "content": MISAFIR_BLOGU},
            {"role": "system", "content": system_prompt},
        ]

    # Profil salt-okunur bağlamdır; kullanıcı cümlesinden gizli
    # öğrenme/silme kararı çıkarılmaz.
    kid = aktif_kullanici()
    profil_blogu = ""
    if kid == VARSAYILAN_KULLANICI:
        try:
            from memory.profil import blok
            profil_blogu = blok(ctx.hafiza_al())
        except Exception as e:
            logger.warning("Profil okunamadi: %s", e)

    tam_prompt = system_prompt
    if konusmaci:
        tam_prompt += "\nKonuşan: %s" % konusmaci

    mesajlar = [
        {"role": "system", "content": kimlik_blogu(gorunur_ad(kid))},
        {"role": "system", "content": tam_prompt},
    ]

    # Sabit ajan sozlesmesini dinamik hafiza/profil bloklarindan ONCE koy.
    # Groq/Gemini/Cloudflare prefix caching ayni sistem+arac onekini tekrar
    # isleyebilsin; model davranisi veya baglam icerigi degismez.
    if ajan_sozlesmesi:
        mesajlar.append({"role": "system", "content": ajan_sozlesmesi})

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
        mesajlar.append({
            "role": "system",
            "content": (
                "Hafızadan (GEÇMİŞ KAYDI; KANIT DEĞİL):\n"
                + "\n".join(satirlar)
            ),
        })

    if profil_blogu:
        mesajlar.append({"role": "system", "content": profil_blogu})

    return mesajlar


def _kaydet(text, cevap, kaynak, gecmis, js_callback, konusmaci,
            misafir=False, onbellekle=False, arac_kullanildi=False,
            tamamlanmis=True):
    """Cevabı ekrana basar, geçmişe ve kalıcı hafızaya yazar.

    onbellekle=True: yalnız ARAC KOSMAYAN turlar icin gecilir; cevap
    kisa sure icin saklanir ki ayni mesaj tekrar gonderilirse model
    yeniden cagrilmasin (bkz. chat/onbellek.py).
    """
    if misafir:
        # Misafir iz birakmaz: ortak gecmise, oturuma ve hafizaya yazilmaz.
        js_callback("BasakUI.bitir(" + _j(cevap) + ", " + _j(kaynak) + ")")
        return
    gecmis += [
        {"role": "user", "content": text, "oturum": ctx.OTURUM_ID},
        {"role": "assistant", "content": cevap, "oturum": ctx.OTURUM_ID},
    ]
    try:
        ctx.kaydet(ctx.gecmis_yolu(), gecmis)
    except OSError as e:
        # Gecmis yazilamasa da ekran bitmeli (2026-09-15 checkup).
        logger.warning("Gecmis yazilamadi (ekran etkilenmez): %s", e)

    try:
        from chat import oturum
        oturum.kaydet_cift(text, cevap)
    except Exception as e:
        logger.warning("Oturum kaydi atlandi: %s", e)

    js_callback("BasakUI.bitir(" + _j(cevap) + ", " + _j(kaynak) + ")")

    if onbellekle and not misafir and \
            aktif_kullanici() == VARSAYILAN_KULLANICI:
        _onbellek.koy(text, cevap)

    # Ekran güncellendikten SONRA anıyı yaz — cevabı bekletmesin.
    motor = ctx.hafiza_al()
    if motor and cevap and tamamlanmis:
        try:
            hafiza_kaynagi = (
                "sohbet_aracli" if arac_kullanildi else "sohbet_aracsiz"
            )
            motor.episodik_kaydet(
                text, cevap, kaynak=hafiza_kaynagi,
                speaker=konusmaci or "", onem=ctx.onem_puanla(text)
            )
        except Exception as e:
            logger.warning("Ani kaydedilemedi: %s", e)



def _yonlendirme_mesajlari(baglam, mevcut_mesajlar):
    """Dogrulanmis onceki run olaylarini provider-neutral mesaja cevir."""
    if not isinstance(baglam, dict):
        return []
    olaylar = baglam.get("olaylar")
    if not isinstance(olaylar, list):
        return []

    ek = []
    run = next(
        (o for o in olaylar if isinstance(o, dict)
         and o.get("tur") == "runContext"),
        {},
    )
    onceki_istek = str(run.get("metin") or "")
    zaten_var = any(
        isinstance(m, dict)
        and m.get("role") == "user"
        and str(m.get("content") or "") == onceki_istek
        for m in (mevcut_mesajlar or [])
    )
    if onceki_istek and not zaten_var:
        ek.append({"role": "user", "content": onceki_istek})

    turlar = {}
    for olay in olaylar:
        if not isinstance(olay, dict) or olay.get("tur") != "toolDone":
            continue
        try:
            tur = int(olay.get("turn") or 0)
        except (TypeError, ValueError):
            tur = 0
        turlar.setdefault(tur, []).append(olay)

    for tur in sorted(turlar):
        cagrilar = []
        sonuclar = []
        for i, olay in enumerate(turlar[tur]):
            ad = str(olay.get("name") or "")
            cagri_id = str(olay.get("id") or ("handoff_%s_%s" % (tur, i)))
            args = olay.get("args")
            if not isinstance(args, dict):
                args = {}
            if not ad:
                continue
            cagrilar.append({
                "id": cagri_id,
                "type": "function",
                "function": {
                    "name": ad,
                    "arguments": json.dumps(
                        args, ensure_ascii=False, separators=(",", ":")
                    ),
                },
            })
            sonuclar.append({
                "role": "tool",
                "tool_call_id": cagri_id,
                "name": ad,
                "content": str(olay.get("result") or ""),
            })
        if cagrilar:
            ek.append({
                "role": "assistant",
                "content": "",
                "tool_calls": cagrilar,
            })
            ek.extend(sonuclar)

    kismi = "".join(
        str(o.get("metin") or "")
        for o in olaylar
        if isinstance(o, dict) and o.get("tur") == "parca"
    )
    if kismi:
        ek.append({"role": "assistant", "content": kismi})

    son_durum = next(
        (o for o in reversed(olaylar)
         if isinstance(o, dict) and o.get("tur") == "runState"),
        None,
    )
    kaynaklar = [
        str(o.get("url") or "")
        for o in olaylar
        if isinstance(o, dict) and o.get("tur") == "source" and o.get("url")
    ]
    kesilme = next(
        (str(o.get("reason") or "limit") for o in reversed(olaylar)
         if isinstance(o, dict) and o.get("tur") == "truncated"),
        "",
    )
    if son_durum or kaynaklar or kesilme:
        veri = {
            "schema": "p2-handoff-v1",
            "onceki_run": str(run.get("istek") or ""),
            "run_state": son_durum or {},
            "kaynaklar": kaynaklar,
            "truncated_reason": kesilme,
        }
        ek.append({
            "role": "system",
            "content": "YONLENDIRME_DURUMU_JSON:\n" + json.dumps(
                veri, ensure_ascii=False, separators=(",", ":")
            ),
        })
    return ek


def mesaj_isle(text, brain, system_prompt, js_callback, tools=None,
               misafir=False, gecmis_override=None,
               yonlendirme_baglami=None, tool_policy="auto",
               run_state=None):
    """Bir mesajı baştan sona işler."""
    text, konusmaci = _konusmaci_ayir((text or "").strip())

    js_callback("BasakUI.thinking()")
    if not text:
        js_callback("BasakUI.error(" + _j("Bos mesaj") + ")")
        return

    # Ozgu-ajan (Faz 2): SADECE bulut zinciri. Yerel model yok.
    # Bulut musait degilse dur; baska on kosul yok.
    # 2026-09-22: "hicbir beyin yok" tek cumleydi ve iki AYRI durumu ayni
    # sozle anlatiyordu: (1) anahtar hic yok, (2) anahtar var ama zincir
    # kurulamiyor. Kullanici metnine BAKILMAZ (chatbot yasagi); yalniz
    # beyin nesnesinin durumu okunur.
    if not brain.bulut_musait():
        _saglayicilar = getattr(brain, "_providers", None)
        if _saglayicilar is not None and not _saglayicilar:
            _mesaj = ("Hicbir beyin yok: hicbir saglayici anahtari "
                      "kurulmadi. ayarlar.json'a bir anahtar yaz."
                      " Kontrol: python doktor.py")
        else:
            _mesaj = ("Hicbir beyin yok: saglayici zinciri kurulamadi "
                      "(anahtar, baglanti veya kota). Kontrol: python "
                      "doktor.py")
        js_callback("BasakUI.error(" + _j(_mesaj) + ")")
        return

    # Zincirdeki bulut saglayici kendi modelini secer; disaridan
    # model adi tasiyarak karistirma.
    model = None

    if gecmis_override is not None:
        gecmis = ctx.temizle_history(list(gecmis_override or []))
    else:
        gecmis = [] if misafir else ctx.temizle_history(
            [m for m in ctx.yukle(ctx.gecmis_yolu(), [])
             if m.get("role") != "system"])

    # Araçlar kapalıysa kısa süreli düz-sohbet önbelleği kullanılabilir.
    # Araçlı run önbellekle bypass edilmez.
    def _onbellekten_don():
        if misafir or aktif_kullanici() != VARSAYILAN_KULLANICI:
            return False
        tekrar = _onbellek.al(text, gecmis)
        if not tekrar:
            return False
        _kaydet(
            text, tekrar, "onbellek", gecmis, js_callback, konusmaci,
            arac_kullanildi=False, tamamlanmis=True,
        )
        return True

    # Capability karari kullanici metninden cikmaz. Run politikasini
    # cagirici acikca verir; varsayilan auto'dur. "none" disinda tum gercek
    # katalog modele aciktir — hidden resolver / kategori kapisi yok.
    tool_policy = normalize_tool_policy(tool_policy)
    etkin_tools = capability_surface(tools, tool_policy)
    arac_acik = bool(etkin_tools)
    state = run_state or AgentRunState(
        run_id=str(getattr(js_callback, "istek", "") or ctx.OTURUM_ID),
        tool_policy=tool_policy,
    )
    emit_run_state(js_callback, state)
    mesajlar = _baglam_kur(
        text, system_prompt, konusmaci,
        AGENT_CONTRACT if arac_acik else "", misafir=misafir)

    model_gecmisi, pencere_bilgi = ctx.gecmis_model_penceresi(gecmis)
    if pencere_bilgi.get("compact") and hasattr(js_callback, "olay"):
        js_callback.olay(
            "contextStatus",
            atlanan=int(pencere_bilgi.get("atlanan_mesaj") or 0),
            toplam_token=int(pencere_bilgi.get("toplam_token") or 0),
            modele_giden_token=int(
                pencere_bilgi.get("modele_giden_token") or 0
            ),
        )
    mesajlar += model_gecmisi
    mesajlar += _yonlendirme_mesajlari(
        yonlendirme_baglami, mesajlar
    )
    mesajlar.append({"role": "user", "content": text})

    # ── Provider-neutral ajan yolu ───────────────────────────────────
    if arac_acik and hasattr(brain, "ajan_musait"):
        ajan_tools = list(etkin_tools)
        secim = tool_policy
        yanit = None
        kaynak = ""

        # auto: model-native stream hem metin hem native tool_call uretebilir.
        # required: tool_choice gercekten provider'a zorlanir; once tool-call
        # alinmadan final metin kabul edilmez.
        if secim == "auto":
            yanit, kaynak, _akis_acildi = akan_ajan_adimi(
                brain, model, mesajlar, js_callback, ajan_tools
            )

        try:
            if yanit is None:
                yanit, kaynak = brain.cevapla(
                    mesajlar, model, tools=ajan_tools, tool_choice=secim)
        except Exception as e:
            state.fail()
            emit_run_state(js_callback, state)
            hata = str(e)
            if "429" in hata or "rate" in hata.lower():
                js_callback("BasakUI.error(" + _j(
                    "Cok fazla istek, biraz bekle") + ")")
            else:
                js_callback("BasakUI.error(" + _j(
                    "Ajan beyni hatasi: " + hata) + ")")
            return

        state.provider_set(kaynak)
        tool_calls = (
            yanit.get("tool_calls") if isinstance(yanit, dict) else None
        )

        if not tool_calls:
            if secim == "required":
                state.fail()
                emit_run_state(js_callback, state)
                js_callback("BasakUI.error(" + _j(
                    "Bu run required modunda fakat gercek arac cagrisi "
                    "olusmadi; duz cevap final kabul edilmedi.") + ")")
                return

            tamam = bool(
                yanit.get("_tamam", True)
                if isinstance(yanit, dict) else True
            )
            if isinstance(yanit, dict) and yanit.get("_streamed"):
                cevap = _temizle(yanit.get("content", ""))
            elif kesik_mi(yanit):
                cevap, kaynak, tamam = kesik_cevabi_bildir(
                    yanit, js_callback=js_callback,
                    tercih=[kaynak] if kaynak else None,
                )
                if not tamam:
                    state.truncate(
                        yanit.get("_finish_reason") or "limit"
                    )
                    emit_run_state(js_callback, state)
            else:
                cevap = _temizle(
                    yanit.get("content", "") if isinstance(yanit, dict)
                    else yanit)
            if cevap:
                state.complete(kaynak)
                emit_run_state(js_callback, state)
                _kaydet(
                    text, _temizle(cevap), kaynak, gecmis, js_callback,
                    konusmaci, misafir=misafir, onbellekle=False,
                    arac_kullanildi=False, tamamlanmis=tamam,
                )
                return
            state.fail()
            emit_run_state(js_callback, state)
            js_callback("BasakUI.error(" + _j("Model bos cevap dondu") + ")")
            return

        from chat.tools import arac_dongusu
        from tools import calistir
        # Ilk required kararinin isi ilk tool-call'i garanti etmektir.
        # Tool sonucu sonraki model turu compositional olarak AUTO devam eder;
        # aksi halde final cevap vermesi sonsuza kadar yasaklanmis olur.
        state.phase_set("tools")
        emit_run_state(js_callback, state)
        cevap, kosan = arac_dongusu(
            tool_calls, mesajlar, brain, model, js_callback, calistir,
            tools=ajan_tools, yanit=yanit, tool_choice="auto",
            tercih=[kaynak] if kaynak else None, run_state=state)
        cevap = _temizle(cevap)
        if cevap:
            tamam = not bool(state.truncated_reason)
            state.complete(state.provider or kaynak)
            emit_run_state(js_callback, state)
            _kaydet(
                text, cevap, state.provider or kaynak, gecmis, js_callback,
                konusmaci, misafir=misafir, arac_kullanildi=kosan > 0,
                tamamlanmis=tamam,
            )
            return

        state.fail()
        emit_run_state(js_callback, state)
        logger.info("Ajan turu final cevap vermedi (%d arac kostu)", kosan)
        js_callback("BasakUI.error(" + _j(
            "Bu sefer araclardan sonuc alamadim, tekrar dene") + ")")
        return

    if not arac_acik and _onbellekten_don():
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
            for kaynak, parca in yayin(mesajlar, model, tools=(etkin_tools or None)):
                parcalar.append(parca)
                js_callback("BasakUI.parca(" + _j(parca) + ")")
            # Bazi saglayicilar sayi/None parca dondurur — join patlamasin.
            tam = _temizle("".join(
                p if isinstance(p, str) else str(p) if p is not None else ""
                for p in parcalar))
            if tam:
                # Akis tamamlandi => hicbir arac kosmadi (arac istendiyse
                # AracIstegi yukarida yakalanirdi). Onbelleklenebilir.
                _kaydet(text, tam, kaynak or "bulut", gecmis, js_callback,
                        konusmaci, misafir=misafir, onbellekle=True)
                return
            logger.info("Akis bos dondu, tek seferlik yola dusuluyor")
        except AracIstegi as istek:
            # P0: streaming sirasinda modelin sectigi arac ve argumanlar
            # korunur; ayni soru ikinci kez modele dusundurulmez.
            # Dogrudan calistir, sonucu ayni zincirden devam ettir.
            _tc = getattr(istek, "tool_calls", None) or []
            _muh = getattr(istek, "muhakeme", None) or {}
            if _tc and etkin_tools:
                from chat.tools import arac_dongusu
                from tools import calistir
                logger.info("Model akista arac istedi — dogrudan calisiyor")
                try:
                    cevap, kosan = arac_dongusu(
                        _tc, mesajlar, brain, model, js_callback,
                        calistir, tools=etkin_tools,
                        yanit={"tool_calls": _tc, **_muh})
                except Exception as e:
                    logger.warning("Akis-arac turu basarisiz: %s", e)
                    cevap, kosan = "", 0
                cevap = _temizle(cevap)
                if cevap:
                    _kaydet(text, cevap, kaynak or "bulut", gecmis,
                            js_callback, konusmaci, misafir=misafir)
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
            _kaydet(text, cevap, kaynak, gecmis, js_callback, konusmaci,
                     misafir=misafir)
            return
        logger.info("Arac turu bos dondu (%d arac kostu)", kosan)

    cevap = _temizle(yanit.get("content", "") if isinstance(yanit, dict)
                     else yanit)
    if not cevap:
        js_callback("BasakUI.error(" + _j("Model bos cevap dondu") + ")")
        return

    # Arac kosan turun sonucu yeniden kullanilmaz (yan etkisi olabilir);
    # yalniz duz sohbet cevabi onbelleklenir.
    _kaydet(text, cevap, kaynak, gecmis, js_callback, konusmaci,
            misafir=misafir, onbellekle=not (tool_calls and tools))
