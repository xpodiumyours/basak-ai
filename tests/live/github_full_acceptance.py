"""GitHub Issue #4 FULL TEST — Basak'in eksiksiz 8x52 canli ajan matrisi.

Kabul ancak su katmanlarin HEPSI gecerse verilir:
1) Kotasiz test paketi.
2) 52 gercek aracin her biri, 8 saglayicinin her birinde TEK TEK sema/tool-call.
3) Ayni 416 hucrenin her birinde tool sonucu saglayiciya geri verilip ikinci tur kabulu.
4) 10 yetenek alaninin dogal secim testi.
5) Her saglayicida gercek Basak sohbet hatti ve gercek simdi araci.

Bir alandaki tek basarili cagri artik o alandaki butun araclari gecmis SAYMAZ.
Yan etkili 52 arac canlida topluca calistirilmaz; model/protokol/dispatcher yolu
tek tek dogrulanir, gercek guvenli simdi araci ayrica uctan uca calistirilir.
"""

import json
import os
import tempfile
import types

SONUC_DOSYASI = "github-full-acceptance.md"
SAGLAYICILAR = (
    "groq", "gemini", "openrouter", "glm",
    "cloudflare", "cohere", "kilo", "nvidia",
)

ALAN_SORULARI = {
    "internet": "Internette OpenAI resmi sitesini arastir ve uygun araci sec.",
    "dosyalar": "Bilgisayardaki bir dosyanin icerigini okumam gerekiyor; uygun araci sec.",
    "projeler": "Bir Git projesinin durumunu kontrol et; uygun proje aracini sec.",
    "gorevler": "Su anki tarih ve saati kontrol et; uygun araci sec.",
    "hafiza": "Kalici hafizada belirli bir konuyu ara; uygun araci sec.",
    "gorsel": "Yerel bir gorseli analiz etmek gerekiyor; uygun gorsel aracini sec.",
    "katalog": "Mevcut katalog islerini listelemek gerekiyor; uygun katalog aracini sec.",
    "matris": "Mevcut fikir matrislerini listelemek gerekiyor; uygun matris aracini sec.",
    "masaustu": "Beyaz listedeki bir masaustu uygulamasini acmak gerekiyor; uygun araci sec.",
    "hesap": "120 carpi 18 bolu 100 hesabini yap; uygun hesap aracini sec.",
}


def _kisa(metin, sinir=120):
    metin = str(metin or "").replace("|", "/").replace("\n", " ")
    return metin if len(metin) <= sinir else metin[:sinir - 3] + "..."


def _ui_sonucu(olaylar):
    cevap = ""
    kaynak = ""
    hata = ""
    for code in olaylar:
        if code.startswith("BasakUI.bitir("):
            ic = code[code.index("(") + 1: code.rindex(")")]
            try:
                degerler = json.loads("[" + ic + "]")
                cevap = str(degerler[0] or "")
                kaynak = str(degerler[1] or "") if len(degerler) > 1 else ""
            except Exception:
                cevap = code
        elif code.startswith("BasakUI.error("):
            ic = code[code.index("(") + 1: code.rindex(")")]
            try:
                degerler = json.loads("[" + ic + "]")
                hata = str(degerler[0] or "")
            except Exception:
                hata = code
    return cevap, kaynak, hata


def _tek_provider_zinciri(beyin, provider):
    asil_zincir = beyin._bulut_zinciri

    def tek_zincir(self, tools=False, tool_required=False):
        return [
            (ad, istemci)
            for ad, istemci in asil_zincir(
                tools=tools, tool_required=tool_required)
            if ad == provider
        ]

    return asil_zincir, types.MethodType(tek_zincir, beyin)


def _tek_mesaj(beyin, provider, mesaj, beklenen_arac):
    from chat.flow import mesaj_isle
    from chat import context as ctx
    from tools import TOOLS
    import tools as tools_mod

    asil_zincir, tek_zincir = _tek_provider_zinciri(beyin, provider)
    beyin._bulut_zinciri = tek_zincir
    asil_calistir = tools_mod.calistir
    kosulan = []

    def kayitli_calistir(ad, args):
        kosulan.append(ad)
        return asil_calistir(ad, args)

    tools_mod.calistir = kayitli_calistir
    olaylar = []
    yakalanan_hata = ""

    try:
        with tempfile.TemporaryDirectory() as td:
            ctx.HISTORY_FILE = os.path.join(td, "gecmis.json")
            ctx.SETTINGS_FILE = os.path.join(td, "ayar.json")
            ctx._hafiza = False
            try:
                mesaj_isle(
                    mesaj, beyin, "Sen Basak'sin. Turkce konus.",
                    olaylar.append, TOOLS,
                )
            except Exception as e:
                yakalanan_hata = str(e)
    finally:
        tools_mod.calistir = asil_calistir
        beyin._bulut_zinciri = asil_zincir

    cevap, kaynak, hata = _ui_sonucu(olaylar)
    if not cevap:
        return False, {
            "hata": hata or yakalanan_hata or "final cevap yok",
            "araclar": kosulan, "kaynak": kaynak,
        }
    if kaynak != provider:
        return False, {
            "hata": "cevap baska saglayicidan geldi",
            "araclar": kosulan, "kaynak": kaynak,
        }
    if beklenen_arac is None:
        if kosulan:
            return False, {
                "hata": "salt sohbette gereksiz GERCEK arac calisti",
                "araclar": kosulan, "kaynak": kaynak,
            }
    elif beklenen_arac not in kosulan:
        return False, {
            "hata": "%s araci calismadi" % beklenen_arac,
            "araclar": kosulan, "kaynak": kaynak,
        }
    return True, {"cevap": cevap, "araclar": kosulan, "kaynak": kaynak}


def _required_eksik(schema, args):
    params = ((schema.get("function") or {}).get("parameters") or {})
    required = params.get("required") or []
    if not isinstance(required, list):
        return ["<required-listesi-bozuk>"]
    return [k for k in required if k not in args]


def _arac_protokol_hucresi(beyin, provider, istemci, schema):
    """Tek araci tek basina gercek API'ye ver, cagriyi ve ikinci turu dogrula."""
    fn = schema.get("function") or {}
    ad = fn.get("name") or ""
    soru = (
        "Bu bir ajan protokol dogrulama testidir. Sana yalnizca '%s' araci "
        "verildi. Metinle cevap verme; bu araci cagir. Semadaki zorunlu "
        "alanlari gecerli ornek degerlerle doldur." % ad
    )
    try:
        yanit = beyin._tek_cagri(
            istemci, provider,
            [{"role": "user", "content": soru}],
            [schema], None, None, tool_choice="required",
        )
    except Exception as e:
        return {
            "schema_ok": False, "roundtrip_ok": False,
            "hata": "ilk cagri: " + _kisa(e),
        }

    cagrilar = (
        yanit.get("tool_calls") if isinstance(yanit, dict) else None
    ) or []
    if not cagrilar:
        return {
            "schema_ok": False, "roundtrip_ok": False,
            "hata": "tool_call yok",
        }

    hatalar = []
    parsed = []
    for c in cagrilar:
        func = c.get("function") or {}
        if func.get("name") != ad:
            hatalar.append("yanlis arac=%s" % func.get("name"))
            continue
        try:
            args = json.loads(func.get("arguments") or "{}")
        except Exception:
            hatalar.append("arguments gecerli JSON degil")
            continue
        if not isinstance(args, dict):
            hatalar.append("arguments object degil")
            continue
        eksik = _required_eksik(schema, args)
        if eksik:
            hatalar.append("required eksik=" + ",".join(eksik))
            continue
        parsed.append((c, args))

    if hatalar or not parsed:
        return {
            "schema_ok": False, "roundtrip_ok": False,
            "hata": _kisa("; ".join(hatalar) or "gecerli cagri yok"),
        }

    assistant = {
        "role": "assistant", "content": "",
        "tool_calls": cagrilar,
    }
    for alan in (
        "reasoning_content", "reasoning", "reasoning_details",
        "thinking", "reasoning_text", "tool_plan",
    ):
        if isinstance(yanit, dict) and alan in yanit:
            assistant[alan] = yanit[alan]

    tarihce = [
        {"role": "user", "content": soru},
        assistant,
    ]
    for c in cagrilar:
        tarihce.append({
            "role": "tool",
            "tool_call_id": c.get("id") or "call_test",
            "name": (c.get("function") or {}).get("name") or ad,
            "content": '{"result":"PROTOKOL_TEST_OK"}',
        })

    try:
        ikinci = beyin._tek_cagri(
            istemci, provider, tarihce,
            None, None, None, tool_choice=None,
        )
        icerik = (
            ikinci.get("content", "") if isinstance(ikinci, dict) else ""
        )
        roundtrip_ok = bool(str(icerik or "").strip())
        roundtrip_hata = "" if roundtrip_ok else "ikinci tur final metni yok"
    except Exception as e:
        roundtrip_ok = False
        roundtrip_hata = "ikinci tur: " + _kisa(e)

    return {
        "schema_ok": True,
        "roundtrip_ok": roundtrip_ok,
        "hata": roundtrip_hata,
    }


def _tum_arac_protokol_testi(beyin, provider, istemci):
    from tools import TOOLS

    sonuc = {}
    for schema in TOOLS:
        ad = ((schema.get("function") or {}).get("name")) if isinstance(schema, dict) else ""
        if not ad:
            continue
        sonuc[ad] = _arac_protokol_hucresi(
            beyin, provider, istemci, schema)
    if len(sonuc) != 52:
        raise AssertionError("Beklenen 52 gercek arac, bulunan %d" % len(sonuc))
    return sonuc


def _alan_secim_testi(beyin, provider, istemci):
    """10 alanda model dogru alan icinden bir arac secebiliyor mu?"""
    from chat.agent_protocol import YETENEK_ALANLARI
    from tools import TOOLS

    tum = {t["function"]["name"]: t for t in TOOLS}
    sonuclar = {}
    for alan, adlar in YETENEK_ALANLARI.items():
        semalar = [tum[ad] for ad in adlar]
        try:
            yanit = beyin._tek_cagri(
                istemci, provider,
                [{"role": "user", "content": ALAN_SORULARI[alan]}],
                semalar, None, None, tool_choice="required",
            )
            cagrilar = (
                yanit.get("tool_calls")
                if isinstance(yanit, dict) else None
            ) or []
            secilen = [
                ((c.get("function") or {}).get("name"))
                for c in cagrilar if isinstance(c, dict)
            ]
            gecersiz = [x for x in secilen if x not in adlar]
            sonuclar[alan] = {
                "ok": bool(secilen) and not gecersiz,
                "secilen": secilen,
                "hata": "" if secilen and not gecersiz else (
                    "tool_call yok" if not secilen
                    else "alan disi arac: " + ",".join(gecersiz)
                ),
            }
        except Exception as e:
            sonuclar[alan] = {
                "ok": False, "secilen": [], "hata": _kisa(e),
            }
    return sonuclar


def _pytest_ozeti():
    try:
        with open("full-pytest.txt", encoding="utf-8", errors="replace") as f:
            temiz = [x.strip() for x in f.readlines() if x.strip()]
            if temiz:
                return temiz[-1]
    except OSError:
        pass
    return "dogrulanamadi"


def main():
    from brain import Brain

    b = Brain()
    mevcut = dict(b._bulut_zinciri(tools=True, tool_required=True))

    satirlar = []
    detaylar = []
    tam_gecen = 0
    eksik = 0
    kalan = 0

    for ad in SAGLAYICILAR:
        if ad not in mevcut:
            satirlar.append(
                "| %s | X YOK | 0/52 | 0/52 | 0/10 | - | - | canli istemci yok |"
                % ad
            )
            detaylar.append("**%s:** canli istemci yok; 52 hucrenin hicbiri test edilmedi." % ad)
            eksik += 1
            continue

        hucreler = _tum_arac_protokol_testi(b, ad, mevcut[ad])
        schema_ok = sum(1 for x in hucreler.values() if x["schema_ok"])
        roundtrip_ok = sum(1 for x in hucreler.values() if x["roundtrip_ok"])

        alanlar = _alan_secim_testi(b, ad, mevcut[ad])
        alan_ok = sum(1 for x in alanlar.values() if x["ok"])

        sohbet_ok, sohbet = _tek_mesaj(
            b, ad,
            "Sadece kisa bir selam ver. Dis bilgiye veya isleme ihtiyacin yok.",
            None,
        )
        arac_ok, arac = _tek_mesaj(
            b, ad,
            "Su an tarih ve saati gercek aracla kontrol et ve bana soyle.",
            "simdi",
        )

        provider_ok = (
            schema_ok == 52 and roundtrip_ok == 52 and alan_ok == 10
            and sohbet_ok and arac_ok
        )
        if provider_ok:
            tam_gecen += 1
            durum = "GECTI"
            not_ = "52 tekil sema + 52 ikinci tur + 10 alan + sohbet + simdi"
        else:
            kalan += 1
            durum = "KALDI"
            bozuk = [
                "%s:%s/%s %s" % (
                    isim,
                    "S+" if veri["schema_ok"] else "S-",
                    "R+" if veri["roundtrip_ok"] else "R-",
                    _kisa(veri["hata"], 55),
                )
                for isim, veri in hucreler.items()
                if not (veri["schema_ok"] and veri["roundtrip_ok"])
            ]
            alan_bozuk = [
                "%s:%s" % (alan, _kisa(veri["hata"], 45))
                for alan, veri in alanlar.items() if not veri["ok"]
            ]
            neden = []
            if bozuk:
                neden.append("arac=" + "; ".join(bozuk[:3]))
                if len(bozuk) > 3:
                    neden.append("+%d arac daha" % (len(bozuk) - 3))
            if alan_bozuk:
                neden.append("alan=" + "; ".join(alan_bozuk[:2]))
            if not sohbet_ok:
                neden.append("sohbet=" + _kisa(sohbet.get("hata"), 60))
            if not arac_ok:
                neden.append("simdi=" + _kisa(arac.get("hata"), 60))
            not_ = _kisa("; ".join(neden), 220)

        satirlar.append(
            "| %s | %s | %d/52 | %d/52 | %d/10 | %s | %s | %s |"
            % (
                ad, durum, schema_ok, roundtrip_ok, alan_ok,
                "OK" if sohbet_ok else "X",
                "OK" if arac_ok else "X",
                not_,
            )
        )

        detaylar.append("**%s — 52 arac hucresi**" % ad)
        for isim, veri in hucreler.items():
            detaylar.append(
                "- %s: sema=%s · ikinci-tur=%s%s" % (
                    isim,
                    "OK" if veri["schema_ok"] else "X",
                    "OK" if veri["roundtrip_ok"] else "X",
                    (" · " + _kisa(veri["hata"], 90)) if veri["hata"] else "",
                )
            )
        detaylar.append(
            "**%s — alan secimi:** %s" % (
                ad,
                ", ".join(
                    "%s=%s[%s]" % (
                        alan, "OK" if veri["ok"] else "X",
                        ",".join(veri["secilen"]) or _kisa(veri["hata"], 50),
                    )
                    for alan, veri in alanlar.items()
                ),
            )
        )

    pytest_ozet = _pytest_ozeti()
    kotasiz_ok = (
        "passed" in pytest_ozet
        and "failed" not in pytest_ozet.lower()
    )
    tam = (
        kotasiz_ok
        and tam_gecen == len(SAGLAYICILAR)
        and eksik == 0
        and kalan == 0
    )

    rapor = [
        "### Basak FULL TEST — eksiksiz 8x52 ajan matrisi",
        "",
        "#### 1) Kotasiz yapisal dogrulama",
        "",
        "**Sonuc:** " + pytest_ozet,
        "",
        "Bu katman 52/52 arac semasi, dispatcher ve 8x52 baglanti yolunu "
        "kotasiz sinar; canli API kaniti yerine SAYILMAZ.",
        "",
        "#### 2) Gercek saglayici protokolu — 416 tekil hucre",
        "",
        "Her saglayicida 52 arac TEK TEK API'ye verilir. Bir aractaki basari "
        "ayni alandaki diger araclara yazilmaz. Ardindan her basarili tool-call "
        "sonucu ayni saglayiciya geri verilir; ikinci tur protokolu de 52/52 "
        "ayri dogrulanir.",
        "",
        "| Saglayici | Sonuc | Tekil sema | Ikinci tur | Alan secimi | Salt sohbet | Gercek simdi | Not |",
        "|---|---|---:|---:|---:|---|---|---|",
        *satirlar,
        "",
        "**Canli saglayici ozeti:** %d/8 tam gecti · %d eksik · %d kaldi"
        % (tam_gecen, eksik, kalan),
        "",
        "#### 3) Gercekte ne sinandi?",
        "",
        "- 8 saglayici x 52 arac = 416 canli tekil sema/tool-call hucresi.",
        "- Ayni 416 hucrenin tool-result -> ikinci model turu ayrica sinanir.",
        "- 8 saglayici x 10 yetenek alani dogal secim davranisi ayrica sinanir.",
        "- Her saglayicida gercek Basak sohbet hatti calistirilir.",
        "- Her saglayicida gercek simdi araci calistirilip sonucu modele geri verilir.",
        "- Yan etkili araclarin kendileri topluca canli calistirilmaz; dosya yazma, "
        "gorev ekleme, uygulama acma gibi etkiler test ortaminda gercek kullanici "
        "verisine uygulanmaz. Bu rapor boyle bir iddia kurmaz.",
        "",
        "#### 4) 52 arac ayrintisi",
        "",
        *detaylar,
        "",
        "### Kabul",
        "",
        (
            "TAM KABUL: 8/8 saglayicida 52/52 tekil sema + 52/52 ikinci tur "
            "+ 10/10 alan + gercek sohbet + gercek simdi ve kotasiz paket gecti."
            if tam else
            "TAM KABUL YOK: tek bir saglayici/arac hucresi bile eksik veya "
            "kirmiziysa Basak'in tamami canli dogrulandi denemez."
        ),
    ]

    with open(SONUC_DOSYASI, "w", encoding="utf-8") as f:
        f.write("\n".join(rapor) + "\n")

    if not tam:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
