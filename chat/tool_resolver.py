"""P2 görünmez runtime araç çözücüsü.

Büyük araç yüzeyini ana modele her tur yığmadan, gerçek araç adaylarını
bağlama göre deferred biçimde hazırlar. Karar sabit kelime/niyet routerı değil
model tabanlıdır.

Güvence:
- Meta araç ana modele gösterilmez.
- Resolver "araç zorunlu" derse ana model tool_choice=required ile çalışır.
- Resolver bozulur veya katalog dışı seçim üretirse yetenek kaybı olmaması için
  tam gerçek katalog fail-open olarak sunulur.
- Araç sonucundan sonra karar güncel bağlamla yeniden verilir.
"""

import inspect
import json
import logging

logger = logging.getLogger(__name__)

RUNTIME_AJAN_SOZLESMESI = (
    "AJAN CALISMA SOZLESMESI:\n"
    "- Sana o anda uygun görülen GERCEK araçlar doğrudan sunulur.\n"
    "- Dış dünya, güncel durum, dosya/proje durumu veya gerçek bir eylem "
    "gerekiyorsa uygun GERCEK aracı çağır; araç adını tarif etmek iş "
    "yapılmış sayılmaz.\n"
    "- Araç sonucunu gördükten sonra yeniden karar ver; gerekirse başka "
    "gerçek araç çağır.\n"
    "- Sunulmayan araç adını uydurma.\n"
    "- Başarılı araç sonucu olmadan bir eylemi yapılmış gibi söyleme.\n"
    "- Hafızadaki eski Başak cevapları kanıt değildir; güncel araç sonucu "
    "ile çelişirse araç sonucu üstündür."
)

_RESOLVER_SYSTEM = (
    "Sen Başak'ın kullanıcıya görünmeyen runtime tool-search katmanısın. "
    "Kullanıcıya cevap verme ve görevi kendin yapma. Bir sonraki ANA MODEL "
    "adımı için katalogdan gerekli GERCEK araç adaylarını seç. Tek kategoriye "
    "kilitlenme; çok adımlı işte farklı tür araçları birlikte seçebilirsin. "
    "Dış dünya/güncel durum/gerçek eylem/dosya-proje ölçümü olmadan güvenilir "
    "cevap verilemeyecekse tool_required=true olmalıdır. Yalnız sabit bilgi, "
    "yaratıcı yazı veya sohbet için tool_required=false olabilir. "
    "Yalnız katalogdaki adları kullan. En fazla {limit} aday seç. "
    "YALNIZ JSON döndür: "
    '{{"tool_required":true,"tools":["arac_1","arac_2"]}}'
)


def _arac_adi(arac):
    if not isinstance(arac, dict):
        return ""
    return str((arac.get("function") or {}).get("name") or "")


def _katalog_metni(tum_tools):
    satirlar = []
    for arac in tum_tools or []:
        if not isinstance(arac, dict):
            continue
        fn = arac.get("function") or {}
        ad = str(fn.get("name") or "").strip()
        if not ad:
            continue
        aciklama = " ".join(str(fn.get("description") or "").split())
        props = ((fn.get("parameters") or {}).get("properties") or {})
        parametreler = ", ".join(str(x) for x in props.keys())
        satir = "- %s: %s" % (ad, aciklama)
        if parametreler:
            satir += " | parametreler: " + parametreler
        satirlar.append(satir)
    return "\n".join(satirlar)


def _baglam_ozeti(mesajlar):
    satirlar = []
    for mesaj in mesajlar or []:
        if not isinstance(mesaj, dict):
            continue
        rol = mesaj.get("role")
        if rol not in ("user", "assistant", "tool"):
            continue
        icerik = mesaj.get("content")
        if isinstance(icerik, list):
            icerik = json.dumps(icerik, ensure_ascii=False)
        icerik = str(icerik or "").strip()
        tc = mesaj.get("tool_calls") or []
        if tc:
            adlar = [_arac_adi(c) for c in tc if _arac_adi(c)]
            if adlar:
                icerik = (icerik + " | tool_calls=" + ",".join(adlar)).strip()
        if rol == "tool":
            ad = str(mesaj.get("name") or "").strip()
            if ad:
                icerik = ("tool=%s | " % ad) + icerik
        if icerik:
            satirlar.append("%s: %s" % (rol, icerik[:2200]))
    return "\n".join(satirlar[-12:])[-18000:]


def _resolver_cagir(brain, model, mesajlar, tercih=None):
    kwargs = {}
    try:
        params = inspect.signature(brain.cevapla).parameters
        kwargs_var = any(
            p.kind == inspect.Parameter.VAR_KEYWORD for p in params.values()
        )
        if tercih and ("tercih" in params or kwargs_var):
            kwargs["tercih"] = list(tercih)
    except (TypeError, ValueError):
        pass
    return brain.cevapla(mesajlar, model, **kwargs)


def _yanit_ayir(yanit):
    kaynak = ""
    if isinstance(yanit, tuple):
        if len(yanit) > 1:
            kaynak = str(yanit[1] or "")
        yanit = yanit[0] if yanit else {}
    if isinstance(yanit, dict):
        return str(yanit.get("content") or ""), kaynak
    return str(yanit or ""), kaynak


def _karar_json(metin):
    ham = str(metin or "").strip()
    adaylar = [ham]
    bas, son = ham.find("{"), ham.rfind("}")
    if bas >= 0 and son > bas:
        adaylar.append(ham[bas:son + 1])
    for aday in adaylar:
        try:
            veri = json.loads(aday)
        except Exception:
            continue
        if not isinstance(veri, dict) or not isinstance(veri.get("tools"), list):
            continue
        gerekli = veri.get("tool_required")
        if gerekli is None:
            gerekli = bool(veri.get("tools"))
        if not isinstance(gerekli, bool):
            continue
        return {"tool_required": gerekli, "tools": veri["tools"]}, True
    return {}, False


def arac_karari_coz(brain, model, mesajlar, tum_tools, tercih=None, limit=14):
    katalog = list(tum_tools or [])
    if not katalog:
        return {
            "tools": [], "tool_required": False, "verified": True,
            "fail_open": False, "resolver_provider": "",
        }

    limit = max(1, min(int(limit or 14), 20))
    ad_to_tool = {
        _arac_adi(arac): arac for arac in katalog if _arac_adi(arac)
    }
    resolver_mesajlari = [
        {"role": "system", "content": _RESOLVER_SYSTEM.format(limit=limit)},
        {"role": "user", "content": (
            "GUNCEL GOREV BAGLAMI:\n"
            + (_baglam_ozeti(mesajlar) or "(baglam yok)")
            + "\n\nGERCEK ARAC KATALOGU:\n"
            + _katalog_metni(katalog)
        )},
    ]

    try:
        ham, kaynak = _yanit_ayir(_resolver_cagir(
            brain, model, resolver_mesajlari, tercih=tercih
        ))
        karar, gecerli = _karar_json(ham)
    except Exception as e:
        logger.warning("Runtime tool resolver calismadi: %s", e)
        return {
            "tools": katalog, "tool_required": False, "verified": False,
            "fail_open": True, "resolver_provider": "",
        }

    if not gecerli:
        logger.warning("Runtime tool resolver gecerli karar JSON'u dondurmedi")
        return {
            "tools": katalog, "tool_required": False, "verified": False,
            "fail_open": True, "resolver_provider": kaynak,
        }

    adlar = karar["tools"]
    gerekli = bool(karar["tool_required"])
    secilen, gorulen = [], set()
    katalog_disi = False
    for ham_ad in adlar:
        ad = str(ham_ad or "").strip()
        if ad not in ad_to_tool:
            katalog_disi = True
            continue
        if ad in gorulen:
            continue
        gorulen.add(ad)
        secilen.append(ad_to_tool[ad])
        if len(secilen) >= limit:
            break

    if gerekli and not secilen:
        secilen = katalog
    fail_open = bool(katalog_disi and adlar and not secilen)
    if fail_open:
        secilen = katalog

    return {
        "tools": secilen,
        "tool_required": gerekli,
        "verified": True,
        "fail_open": fail_open,
        "resolver_provider": kaynak,
    }


def araclari_coz(brain, model, mesajlar, tum_tools, tercih=None, limit=14):
    return arac_karari_coz(
        brain, model, mesajlar, tum_tools, tercih=tercih, limit=limit
    )["tools"]
