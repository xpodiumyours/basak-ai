"""GitHub Issue #4 FULL TEST icin 8/8 canli saglayici kabul sinavi."""

import json
import os
import tempfile
import types

SONUC_DOSYASI = "github-full-acceptance.md"
SAGLAYICILAR = (
    "groq", "gemini", "openrouter", "glm",
    "cloudflare", "cohere", "kilo", "nvidia",
)


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


def _tek_mesaj(beyin, provider, mesaj, beklenen_arac):
    from chat.flow import mesaj_isle
    from chat import context as ctx
    from tools import TOOLS
    import tools as tools_mod

    asil_zincir = beyin._bulut_zinciri

    def tek_zincir(self, tools=False, tool_required=False):
        return [
            (ad, istemci)
            for ad, istemci in asil_zincir(
                tools=tools, tool_required=tool_required)
            if ad == provider
        ]

    beyin._bulut_zinciri = types.MethodType(tek_zincir, beyin)

    asil_calistir = tools_mod.calistir
    kosulan = []

    def kayitli_calistir(ad, args):
        kosulan.append(ad)
        return asil_calistir(ad, args)

    tools_mod.calistir = kayitli_calistir
    olaylar = []

    try:
        with tempfile.TemporaryDirectory() as td:
            ctx.HISTORY_FILE = os.path.join(td, "gecmis.json")
            ctx.SETTINGS_FILE = os.path.join(td, "ayar.json")
            ctx._hafiza = False
            mesaj_isle(
                mesaj,
                beyin,
                "Sen Başak'sın. Türkçe konuş.",
                olaylar.append,
                TOOLS,
            )
    finally:
        tools_mod.calistir = asil_calistir
        beyin._bulut_zinciri = asil_zincir

    cevap, kaynak, hata = _ui_sonucu(olaylar)
    if not cevap:
        return False, {
            "hata": hata or "final cevap yok",
            "araclar": kosulan,
            "kaynak": kaynak,
        }
    if kaynak != provider:
        return False, {
            "hata": "cevap baska saglayicidan geldi",
            "araclar": kosulan,
            "kaynak": kaynak,
        }
    if beklenen_arac is None:
        if kosulan:
            return False, {
                "hata": "salt sohbette gereksiz gercek arac calisti",
                "araclar": kosulan,
                "kaynak": kaynak,
            }
    elif beklenen_arac not in kosulan:
        return False, {
            "hata": "%s araci calismadi" % beklenen_arac,
            "araclar": kosulan,
            "kaynak": kaynak,
        }
    return True, {
        "cevap": cevap,
        "araclar": kosulan,
        "kaynak": kaynak,
    }


def main():
    from brain import Brain

    b = Brain()
    mevcut = dict(b._bulut_zinciri(tools=True, tool_required=True))

    satirlar = []
    basarili = 0
    eksik = 0
    hatali = 0

    for ad in SAGLAYICILAR:
        if ad not in mevcut:
            satirlar.append(
                "| %s | ❌ YOK | - | - | GitHub ortaminda ajan olarak hazir degil |"
                % ad
            )
            eksik += 1
            continue

        sohbet_ok, sohbet = _tek_mesaj(
            b, ad,
            "Sadece kısa bir selam ver. Dış bilgiye veya işleme ihtiyacın yok.",
            None,
        )
        arac_ok, arac = _tek_mesaj(
            b, ad,
            "Şu an tarih ve saati gerçek araçla kontrol et ve bana söyle.",
            "simdi",
        )

        if sohbet_ok and arac_ok:
            durum = "✅ GEÇTİ"
            basarili += 1
            not_ = "salt sohbet + simdi araci + final cevap"
        else:
            durum = "❌ KALDI"
            hatali += 1
            nedenler = []
            if not sohbet_ok:
                nedenler.append("sohbet: " + str(sohbet.get("hata", "")))
            if not arac_ok:
                nedenler.append("arac: " + str(arac.get("hata", "")))
            not_ = "; ".join(nedenler)

        satirlar.append(
            "| %s | %s | %s | %s | %s |"
            % (
                ad,
                durum,
                "✅" if sohbet_ok else "❌",
                "✅" if arac_ok else "❌",
                not_.replace("|", "/"),
            )
        )

    pytest_ozet = "doğrulanamadı"
    try:
        with open("full-pytest.txt", encoding="utf-8", errors="replace") as f:
            temiz = [x.strip() for x in f.readlines() if x.strip()]
            if temiz:
                pytest_ozet = temiz[-1]
    except OSError:
        pass

    tam = basarili == len(SAGLAYICILAR) and eksik == 0 and hatali == 0

    rapor = [
        "### Başak FULL TEST",
        "",
        "**Kotasız tam test paketi:** " + pytest_ozet,
        "",
        "**Canlı sağlayıcı sonucu:** %d/8 geçti · %d eksik · %d kaldı"
        % (basarili, eksik, hatali),
        "",
        "| Sağlayıcı | Sonuç | Salt sohbet | Gerçek araç | Not |",
        "|---|---|---|---|---|",
        *satirlar,
        "",
        "**Kabul:** " + (
            "✅ 8/8 canlı sağlayıcı geçti."
            if tam else
            "❌ 8/8 canlı sağlayıcı kanıtlanmadı; FULL TEST tamamlanmış sayılmaz."
        ),
        "",
        "Kotasız paket ayrıca 52/52 araç yüzeyini ve 8×52=416 ajan "
        "sağlayıcı-arac yolunu denetler.",
    ]

    with open(SONUC_DOSYASI, "w", encoding="utf-8") as f:
        f.write("\n".join(rapor) + "\n")

    if not tam:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
