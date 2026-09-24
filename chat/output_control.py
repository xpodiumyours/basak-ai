"""P2 çıktı kontrolü: gerçek streaming ve sessiz kesilmeme."""

import json
import logging

logger = logging.getLogger(__name__)

KESIK_BITISLER = {"length", "max_tokens", "model_context_window_exceeded"}


def _j(obj):
    return json.dumps(obj, ensure_ascii=False)


def kesik_mi(yanit):
    return isinstance(yanit, dict) and str(
        yanit.get("_finish_reason") or ""
    ).lower() in KESIK_BITISLER


def kesik_nedeni(yanit):
    if not isinstance(yanit, dict):
        return ""
    return str(yanit.get("_finish_reason") or "")


def kesik_cevabi_tamamla(
        brain, model, mesajlar, yanit, js_callback=None, tercih=None,
        en_fazla_devam=3):
    if not isinstance(yanit, dict):
        return str(yanit or ""), "", True
    tam = str(yanit.get("content") or "")
    neden = kesik_nedeni(yanit)
    kaynak = (tercih or [""])[0] if tercih else ""
    son_mesajlar = list(mesajlar or [])

    for _ in range(max(0, int(en_fazla_devam or 0))):
        if neden.lower() not in KESIK_BITISLER:
            return tam, kaynak, True
        devam_mesajlari = son_mesajlar + [
            {"role": "assistant", "content": tam},
            {"role": "system", "content": (
                "TEKNIK DEVAM: Onceki final yanit teknik cikti sinirinda "
                "kesildi. Yeni iddia/konu acmadan, tekrar etmeden yalniz "
                "kesildigi yerden devam et. Arac cagirma."
            )},
        ]
        try:
            kwargs = {"tercih": [kaynak]} if kaynak else {}
            yeni, yeni_kaynak = brain.cevapla(
                devam_mesajlari, model, **kwargs
            )
        except TypeError:
            yeni, yeni_kaynak = brain.cevapla(devam_mesajlari, model)
        except Exception as e:
            logger.warning("Kesik cevap devam ettirilemedi: %s", e)
            break

        parca = str((yeni or {}).get("content") or "") if isinstance(
            yeni, dict) else str(yeni or "")
        if not parca:
            break
        tam += parca
        if js_callback is not None:
            js_callback("BasakUI.parca(" + _j(parca) + ")")
        kaynak = str(yeni_kaynak or kaynak)
        neden = kesik_nedeni(yeni)
        son_mesajlar = devam_mesajlari

    if neden.lower() in KESIK_BITISLER:
        if js_callback is not None and hasattr(js_callback, "olay"):
            js_callback.olay("truncated", reason=neden or "limit")
        tam += (
            "\n\n[Yanıt teknik çıktı sınırına ulaştı; tamamı üretilemedi.]"
        )
        return tam, kaynak, False
    return tam, kaynak, True


def akan_final(brain, model, mesajlar, js_callback, tercih=None):
    from brain.yayin import SonHata, CikisKesildi
    yayin = getattr(brain, "cevapla_yayin", None)
    if not callable(yayin):
        return "", "", False
    parcalar, kaynak = [], ""
    try:
        for kaynak, parca in yayin(
                mesajlar, model, tercih=tercih, tools=None):
            parca = parca if isinstance(parca, str) else str(parca or "")
            if not parca:
                continue
            parcalar.append(parca)
            js_callback("BasakUI.parca(" + _j(parca) + ")")
        return "".join(parcalar), kaynak or "bulut", True
    except CikisKesildi as e:
        ham = {"content": "".join(parcalar), "_finish_reason": e.neden}
        return kesik_cevabi_tamamla(
            brain, model, mesajlar, ham, js_callback=js_callback,
            tercih=[kaynak] if kaynak else tercih,
        )
    except SonHata as e:
        logger.info("Gercek final akisi acilamadi: %s", e.ozet)
        return "", "", False
