"""P2 görünmez runtime araç çözücüsü.

Amaç:
- 53 gerçek aracın JSON şemalarını her turda modele yığmamak,
- modele yetenek_ac / arac_ara gibi meta araçlar göstermemek,
- görevin o anki bağlamına uygun gerçek araçları görünmez bir ön adımda seçmek,
- araç sonucundan sonra aynı seçimi güncel bağlamla yeniden yapmak.

Seçim model tabanlıdır; kullanıcı metnini sabit kelime/niyet kurallarıyla
eşleştiren bir router yoktur. Dönen adlar her zaman gerçek katalogla
doğrulanır. Çözücü teknik olarak cevap veremezse yetenek kaybı olmasın diye
tam gerçek katalog tek turluk emniyet geri dönüşüdür.
"""

import inspect
import json
import logging

logger = logging.getLogger(__name__)

RUNTIME_AJAN_SOZLESMESI = (
    "AJAN CALISMA SOZLESMESI:\n"
    "- Sana o anda uygun gorulen GERCEK araclar dogrudan sunulur.\n"
    "- Gercek veri veya eylem gerekiyorsa uygun gercek araci cagir; arac "
    "adini tarif etmek is yapilmis sayilmaz.\n"
    "- Arac sonucunu gordukten sonra yeniden karar ver. Gerekirse baska "
    "gercek arac cagir; is bittiyse dogrudan dogal cevabi ver.\n"
    "- Sunulmayan arac adini uydurma.\n"
    "- Basarili arac sonucu olmadan bir eylemi yapilmis gibi soyleme."
)

_RESOLVER_SYSTEM = (
    "Sen Basak'in kullaniciya gorunmeyen runtime tool resolver'isin. "
    "Kullaniciya cevap verme ve gorevi kendin yapma. Bir sonraki ANA MODEL "
    "adimi icin katalogdan gerekli GERCEK arac adaylarini sec. Tek bir "
    "kategoriye veya ilk alt goreve kilitlenme; cok adimli gorevlerde farkli "
    "turdeki gerekli araclari birlikte sec. Yalniz katalogda verilen arac "
    "adlarini kullan. En fazla {limit} arac sec. Gercek arac gerekmiyorsa "
    "bos liste sec. YALNIZ su JSON bicimini dondur: "
    '{{"tools":["arac_1","arac_2"]}}'
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
    """Resolver'a yalniz is icin gerekli son sohbet/tool baglamini tasir."""
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
            adlar = []
            for c in tc:
                ad = _arac_adi(c)
                if ad:
                    adlar.append(ad)
            if adlar:
                icerik = (icerik + " | tool_calls=" + ",".join(adlar)).strip()

        if rol == "tool":
            ad = str(mesaj.get("name") or "").strip()
            if ad:
                icerik = ("tool=%s | " % ad) + icerik

        if not icerik:
            continue
        satirlar.append("%s: %s" % (rol, icerik[:1800]))

    # Uzun araştırmalarda eski sonuçlar resolver çağrısını şişirmesin.
    return "\n".join(satirlar[-10:])[-14000:]


def _yanit_metni(yanit):
    if isinstance(yanit, tuple):
        yanit = yanit[0] if yanit else {}
    if isinstance(yanit, dict):
        return str(yanit.get("content") or "")
    return str(yanit or "")


def _json_coz(metin):
    ham = str(metin or "").strip()
    adaylar = [ham]
    bas = ham.find("{")
    son = ham.rfind("}")
    if bas >= 0 and son > bas:
        adaylar.append(ham[bas:son + 1])
    bas = ham.find("[")
    son = ham.rfind("]")
    if bas >= 0 and son > bas:
        adaylar.append(ham[bas:son + 1])

    for aday in adaylar:
        try:
            veri = json.loads(aday)
        except Exception:
            continue
        if isinstance(veri, dict) and isinstance(veri.get("tools"), list):
            return veri["tools"], True
        if isinstance(veri, list):
            return veri, True
    return [], False


def _resolver_cagir(brain, model, mesajlar, tercih=None):
    kwargs = {}
    try:
        params = inspect.signature(brain.cevapla).parameters
        kwargs_var = any(
            p.kind == inspect.Parameter.VAR_KEYWORD
            for p in params.values()
        )
        if tercih and ("tercih" in params or kwargs_var):
            kwargs["tercih"] = list(tercih)
    except (TypeError, ValueError):
        pass
    return brain.cevapla(mesajlar, model, **kwargs)


def araclari_coz(brain, model, mesajlar, tum_tools, tercih=None, limit=10):
    """Bir sonraki ana model adımı için gerçek araç şemalarını döndürür.

    Başarılı çözümde yalnız modelin seçtiği gerçek araçlar döner.
    Geçerli boş liste, aracın gerekmediği anlamına gelir.
    Resolver teknik olarak cevap veremez/bozuk JSON döndürürse kabiliyeti
    gizlice kaybetmemek için tam gerçek katalog döner.
    """
    katalog = list(tum_tools or [])
    if not katalog:
        return []

    limit = max(1, min(int(limit or 10), 12))
    ad_to_tool = {}
    for arac in katalog:
        ad = _arac_adi(arac)
        if ad:
            ad_to_tool[ad] = arac

    resolver_mesajlari = [
        {
            "role": "system",
            "content": _RESOLVER_SYSTEM.format(limit=limit),
        },
        {
            "role": "user",
            "content": (
                "GUNCEL GOREV BAGLAMI:\n"
                + (_baglam_ozeti(mesajlar) or "(baglam yok)")
                + "\n\nGERCEK ARAC KATALOGU:\n"
                + _katalog_metni(katalog)
            ),
        },
    ]

    try:
        yanit = _resolver_cagir(
            brain, model, resolver_mesajlari, tercih=tercih
        )
        adlar, gecerli = _json_coz(_yanit_metni(yanit))
    except Exception as e:
        logger.warning("Runtime tool resolver calismadi: %s", e)
        return katalog

    if not gecerli:
        logger.warning("Runtime tool resolver gecerli JSON dondurmedi")
        return katalog

    secilen = []
    gorulen = set()
    for ham_ad in adlar:
        ad = str(ham_ad or "").strip()
        if ad in ad_to_tool and ad not in gorulen:
            gorulen.add(ad)
            secilen.append(ad_to_tool[ad])
        if len(secilen) >= limit:
            break

    # Model bir sey secmeye calisti ama tum adlari uydurduysa yetenek kaybi
    # yaratma; yalnız GERCEK boş liste bilinçli "arac gerekmiyor" sayılır.
    if adlar and not secilen:
        logger.warning("Runtime tool resolver katalog disi araclar dondurdu")
        return katalog

    return secilen
