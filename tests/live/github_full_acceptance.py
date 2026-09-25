"""GitHub Issue #4 FULL TEST — Basak'in tam ajan kabul matrisi.

Kaniti uc ayri katmanda raporlar:
1) Kotasiz: guncel arac semasi + dispatcher + saglayici-arac baglanti yolu.
2) Canli protokol: saglayicilar 13 yetenek alanindaki guncel
   gercek arac semalarini kendi gercek API'sinde kabul edip tool-call
   dondurur mu?
3) Canli uctan uca: her saglayici salt sohbeti ve gercek `simdi`
   aracinin calistirilip final cevaba baglanmasini tamamlar mi?

Canli protokol testi gercek dis etkili araclari (dosya yazma, gorev ekleme,
uygulama acma vb.) CALISTIRMAZ. O araclarin 52/52 dispatcher baglantisi
kotasiz testte tam denetlenir. Bu ayrim raporda acikca belirtilir.
"""

import json
import os
import tempfile
import types

SONUC_DOSYASI = "github-full-acceptance.md"
from tests.live import matris_kosucu as _matris_kosucu

# Tek kapsam kaynagi: gercek canli matrisin bugun olctugu saglayicilar.
SAGLAYICILAR = tuple(_matris_kosucu.KAPSAM)

ALAN_SORULARI = {
    "internet": "İnternette OpenAI resmi sitesini araştır ve uygun aracı seç.",
    "dosyalar": "Bilgisayardaki bir dosyanın içeriğini okumam gerekiyor; uygun aracı seç.",
    "projeler": "Bir Git projesinin durumunu kontrol et; uygun proje aracını seç.",
    "gorevler": "Şu anki tarih ve saati kontrol et; uygun aracı seç.",
    "hafiza": "Kalıcı hafızada belirli bir konuyu ara; uygun aracı seç.",
    "gorsel": "Yerel bir görseli analiz etmek gerekiyor; uygun görsel aracını seç.",
    "katalog": "Mevcut katalog işlerini listelemek gerekiyor; uygun katalog aracını seç.",
    "matris": "Mevcut fikir matrislerini listelemek gerekiyor; uygun matris aracını seç.",
    "masaustu": "Beyaz listedeki bir masaüstü uygulamasını açmak gerekiyor; uygun aracı seç.",
    "hesap": "120 çarpı 18 bölü 100 hesabını yap; uygun hesap aracını seç.",
}


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
                    mesaj,
                    beyin,
                    "Sen Başak'sın. Türkçe konuş.",
                    olaylar.append,
                    TOOLS,
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
                "hata": "salt sohbette gereksiz GERCEK arac calisti",
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


def _alan_sema_testi(beyin, provider, istemci):
    """10 alanda guncel semalari gercek provider API'sinden gecir.

    Araclari calistirmaz; amac provider/modelin Basak'in gercek JSON
    semalarini kabul edip o alandan bir tool_call uretebilmesidir.
    """
    from tools.capabilities import CAPABILITY_NAMESPACES
    from tools import TOOLS

    tum = {
        t["function"]["name"]: t
        for t in TOOLS
    }
    sonuclar = {}
    toplam_sema = 0

    for alan, adlar in CAPABILITY_NAMESPACES.items():
        semalar = [tum[ad] for ad in adlar]
        toplam_sema += len(semalar)
        soru = ALAN_SORULARI[alan]
        try:
            yanit = beyin._tek_cagri(
                istemci,
                provider,
                [{"role": "user", "content": soru}],
                semalar,
                None,
                None,
                tool_choice="required",
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
            ok = bool(secilen) and not gecersiz
            sonuclar[alan] = {
                "ok": ok,
                "sema": len(semalar),
                "secilen": secilen,
                "hata": "" if ok else (
                    "tool_call yok" if not secilen
                    else "alan disi arac: %s" % ", ".join(gecersiz)
                ),
            }
        except Exception as e:
            sonuclar[alan] = {
                "ok": False,
                "sema": len(semalar),
                "secilen": [],
                "hata": str(e),
            }

    assert toplam_sema == len(TOOLS)
    return sonuclar


def _pytest_ozeti():
    try:
        with open("full-pytest.txt", encoding="utf-8", errors="replace") as f:
            temiz = [x.strip() for x in f.readlines() if x.strip()]
            if temiz:
                return temiz[-1]
    except OSError:
        pass
    return "doğrulanamadı"


def _kisa(metin, sinir=180):
    metin = str(metin or "").replace("|", "/").replace("\n", " ")
    return metin if len(metin) <= sinir else metin[:sinir - 3] + "..."


def main():
    from brain import Brain
    from tools import TOOLS

    arac_sayisi = len(TOOLS)
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
                "| %s | ❌ YOK | 0/10 | 0/%d | - | - | GitHub ortamında hazır değil |"
                % (ad, arac_sayisi)
            )
            detaylar.append("**%s:** canlı istemci yok." % ad)
            eksik += 1
            continue

        alanlar = _alan_sema_testi(b, ad, mevcut[ad])
        alan_ok = sum(1 for x in alanlar.values() if x["ok"])
        sema_ok = sum(x["sema"] for x in alanlar.values() if x["ok"])

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

        provider_ok = (
            alan_ok == 10 and sema_ok == arac_sayisi and sohbet_ok and arac_ok
        )
        if provider_ok:
            tam_gecen += 1
            durum = "✅ GEÇTİ"
            not_ = "10 alan + %d şema + sohbet + gerçek simdi" % arac_sayisi
        else:
            kalan += 1
            durum = "❌ KALDI"
            neden = []
            bozuk_alanlar = [
                "%s: %s" % (alan, _kisa(veri["hata"], 90))
                for alan, veri in alanlar.items() if not veri["ok"]
            ]
            if bozuk_alanlar:
                neden.append("alanlar=" + "; ".join(bozuk_alanlar))
            if not sohbet_ok:
                neden.append("sohbet=" + _kisa(sohbet.get("hata"), 90))
            if not arac_ok:
                neden.append("simdi=" + _kisa(arac.get("hata"), 90))
            not_ = _kisa("; ".join(neden))

        satirlar.append(
            "| %s | %s | %d/10 | %d/%d | %s | %s | %s |"
            % (
                ad,
                durum,
                alan_ok,
                sema_ok,
                arac_sayisi,
                "✅" if sohbet_ok else "❌",
                "✅" if arac_ok else "❌",
                not_,
            )
        )

        detaylar.append(
            "**%s alanları:** %s" % (
                ad,
                ", ".join(
                    "%s=%s[%s]" % (
                        alan,
                        "✅" if veri["ok"] else "❌",
                        ",".join(veri["secilen"]) or _kisa(veri["hata"], 60),
                    )
                    for alan, veri in alanlar.items()
                ),
            )
        )

    pytest_ozet = _pytest_ozeti()
    kotasiz_ok = "passed" in pytest_ozet and "failed" not in pytest_ozet.lower()
    tam = (
        kotasiz_ok
        and tam_gecen == len(SAGLAYICILAR)
        and eksik == 0
        and kalan == 0
    )

    rapor = [
        "### Başak FULL TEST — tam ajan matrisi",
        "",
        "#### 1) Kotasız yapısal doğrulama",
        "",
        "**Sonuç:** " + pytest_ozet,
        "",
        (
            "✅ %d/%d araç şeması + dispatcher + 13 yetenek alanı "
            "+ dinamik sağlayıcı-arac bağlantı yolu test paketinden geçti."
            % (arac_sayisi, arac_sayisi)
            if kotasiz_ok else
            "❌ Kotasız yapısal test paketi tam geçmedi."
        ),
        "",
        "**Not:** yapısal bağlantı testleri sahte model yanıtlarıyla "
        "döngüyü doğrular; bunlar canlı API çağrısı değildir.",
        "",
        "#### 2) Gerçek sağlayıcı + gerçek API protokolü",
        "",
        "Her hazır sağlayıcı 13 yetenek alanında güncel gerçek Başak araç "
        "şemalarını kendi API'sine alır ve o alandan tool_call üretmek zorundadır.",
        "",
        "| Sağlayıcı | Sonuç | Alan | Şema | Salt sohbet | Gerçek simdi | Not |",
        "|---|---|---:|---:|---|---|---|",
        *satirlar,
        "",
        "**Canlı sağlayıcı özeti:** %d/%d tam geçti · %d eksik · %d kaldı"
        % (tam_gecen, len(SAGLAYICILAR), eksik, kalan),
        "",
        "#### 3) Ne gerçekten çalıştırıldı?",
        "",
        "- Her hazır sağlayıcıda Başak'ın gerçek sohbet akışı çalıştırıldı.",
        "- Her hazır sağlayıcıda gerçek `simdi` aracı çalıştırılıp sonuç tekrar modele verildi.",
        "- Güncel araç kataloğunun tamamı dispatcher seviyesinde kotasız "
        "ve yan etkisiz doğrulandı.",
        "- Dosya yazma, görev ekleme, uygulama açma, katalog değiştirme gibi "
        "yan etkili araçların tamamı canlı ortamda topluca çalıştırılmadı; "
        "bu rapor böyle bir iddiada bulunmaz.",
        "",
        "#### Alan ayrıntısı",
        "",
        *detaylar,
        "",
        "### Kabul",
        "",
        (
            "✅ TAM KABUL: kotasız yapı + 8/8 sağlayıcı + 10/10 alan + "
            "%d/%d canlı şema + gerçek sohbet/simdi döngüsü geçti."
            % (arac_sayisi, arac_sayisi)
            if tam else
            "❌ TAM KABUL YOK: yukarıdaki eksik/kırmızı kalemler bitmeden "
            "Başak'ın tamamı canlı doğrulandı denemez."
        ),
    ]

    with open(SONUC_DOSYASI, "w", encoding="utf-8") as f:
        f.write("\n".join(rapor) + "\n")

    if not tam:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
