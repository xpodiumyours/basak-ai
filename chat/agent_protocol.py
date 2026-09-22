"""chat/agent_protocol.py — Basak'in model-yonetimli ajan protokolu.

Kod kullanici metnini siniflandirmaz, kelime aramaz ve hangi gercek aracin
calisacagina karar vermez. Model once ihtiyac duydugu yetenek alanini acar,
sonra o alanin gercek araclarindan birini veya daha fazlasini kendi secer.
"""

SON_CEVAP_ADI = "son_cevap"
YETENEK_AC_ADI = "yetenek_ac"

# 52 gercek arac tek ve benzersiz bir yetenek alaninda yer alir. Bu tablo
# kullanici metnini yorumlamaz; yalniz modelin sectigi alan adini gercek
# arac semalarina ceviren katalogdur.
YETENEK_ALANLARI = {
    "internet": (
        "web_search", "haber_ara", "zamanli_ara", "site_ara",
        "gorsel_ara", "kitap_ara", "derin_oku", "sayfa_oku",
        "adres_kontrol", "sirket_ara",
    ),
    "dosyalar": (
        "read_file", "list_files", "belge_ara", "dosya_bilgi",
        "icerik_ara", "write_file_tool",
    ),
    "projeler": (
        "git_durum", "github_durum", "git_gecmis", "git_degisenler",
        "testleri_kos", "saglik_raporu",
    ),
    "gorevler": (
        "get_reminders", "add_task", "list_tasks", "complete_task", "simdi",
    ),
    "hafiza": ("hafiza_ara",),
    "gorsel": ("image_analyze", "gorsel_uret"),
    "katalog": (
        "fatura_oku", "katalog_kur", "katalog_getir", "katalog_liste",
        "katalog_fiyat_guncelle", "katalog_onayla", "yetki_belgesi_ekle",
        "urun_eslestir", "yayin_paketi", "cikti_oku",
    ),
    "matris": (
        "matris_ac", "matris_liste", "satir_ekle", "kanit_ekle",
        "satir_kapat", "satir_ac", "satir_sil", "satir_tasi",
        "matris_durum", "satir_duzenle",
    ),
    "masaustu": ("ac_uygulama",),
    "hesap": ("hesapla",),
}

ALAN_ACIKLAMALARI = {
    "internet": "harici web, haber, site, sayfa, URL ve sirket arastirmasi",
    "dosyalar": "bilgisayardaki dosya/klasor ve proje icerigi; knowledge yazma",
    "projeler": "Git, GitHub, CI, test ve proje hat sagligi",
    "gorevler": "yerel gorevler, hatirlatmalar ve cihazdan dogrulanan su anki tarih/saat",
    "hafiza": "Basak'in kalici hafizasinda arama",
    "gorsel": "yerel goruntu analizi veya yeni gorsel uretimi",
    "katalog": "fatura, urun karti ve Vixrex katalog/yayin paketi",
    "matris": "fikir/plan agaci, satirlar ve kanitlar",
    "masaustu": "beyaz listedeki masaustu uygulamasini acma",
    "hesap": "guvenli matematik hesabi",
}

_ALAN_METNI = "; ".join(
    "%s=%s" % (ad, ALAN_ACIKLAMALARI[ad])
    for ad in YETENEK_ALANLARI
)

YETENEK_AC_ARACI = {
    "type": "function",
    "function": {
        "name": YETENEK_AC_ADI,
        "description": (
            "Gercek bir arac gerektiginde once ihtiyac duydugun TEK yetenek "
            "alanini acar. Alan secimini kullanicinin amacini anlayarak sen "
            "yaparsin; kod kullanici metnini siniflandirmaz. " + _ALAN_METNI
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "alan": {
                    "type": "string",
                    "enum": list(YETENEK_ALANLARI.keys()),
                    "description": "Bu turda acilacak tek yetenek alani",
                }
            },
            "required": ["alan"],
        },
    },
}

SON_CEVAP_ARACI = {
    "type": "function",
    "function": {
        "name": SON_CEVAP_ADI,
        "description": (
            "Kullaniciya verilecek nihai cevabi teslim eder. Gercek veri veya "
            "eylem gereken istekte gerekli gercek araclar calisip sonuclari "
            "gorulmeden kullanma. Yalniz sohbet/aciklama isteginde dogrudan "
            "kullanilabilir."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "metin": {
                    "type": "string",
                    "description": "Kullaniciya gosterilecek nihai cevap",
                }
            },
            "required": ["metin"],
        },
    },
}

AJAN_SOZLESMESI = (
    "AJAN CALISMA SOZLESMESI:\n"
    "- Sohbet veya aciklama icin gercek arac gerekmiyorsa dogrudan dogal "
    "dille cevap ver; arac cagirmak zorunda degilsin.\n"
    "- Gercek veri veya eylem gerekiyorsa yetenek_ac ile ihtiyac duydugun "
    "alani kendin sec. Bu zorunluluktur: arac gerektiren istekte once "
    "yetenek_ac cagir; araci tarif etmek, adlarini saymak veya 'su araci "
    "kullanabilirim' demek is yapilmis sayilmaz.\n"
    "- Kod kullanici metnini siniflandirmaz; kelime eslestirmesi ve sabit "
    "gorev akisi yoktur.\n"
    "- Alan acilinca o alanin gercek araclari sonraki turda gelir. Uygun "
    "araci veya araclari kendin sec ve calistir.\n"
    "- Arac sonucunu gordukten sonra gerekirse baska arac veya alan sec; "
    "is bittiyse kullaniciya dogrudan dogal cevabi ver.\n"
    "- Bir eylem basarili arac sonucu olmadan yapilmis gibi soylenemez.\n"
    "- Araclarin ne oldugunu ogrenmek veya gostermek isteyen istekte de "
    "once yetenek_ac ile ilgili alani ac, arac listesini ezberden yazma."
)


def baslangic_araclari():
    """Ilk turda model yalniz ihtiyac duyarsa yetenek alani acar.

    Nihai cevap icin ozel bir function-call zorunlulugu yoktur; model
    dogrudan metinle bitirebilir. SON_CEVAP_ARACI geriye uyumluluk icin
    tanimli kalir fakat modele sunulmaz.
    """
    return [YETENEK_AC_ARACI]


def alan_araclari(tum_tools, alan):
    """Modelin sectigi tek alandaki gercek araclari acar."""
    adlar = set(YETENEK_ALANLARI.get(alan, ()))
    secilen = []
    for arac in (tum_tools or []):
        if not isinstance(arac, dict):
            continue
        ad = (arac.get("function") or {}).get("name")
        if ad in adlar:
            secilen.append(arac)
    # Alan degistirme kapisi acik kalir. Nihai cevap icin ozel arac
    # sunulmaz; model dogrudan metinle bitirebilir.
    return secilen + [YETENEK_AC_ARACI]
