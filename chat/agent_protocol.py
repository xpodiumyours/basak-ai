"""chat/agent_protocol.py — Basak'in model-yonetimli yetenek alanlari.

AGENTS.md §0: ilk ajan turunda modele yalniz `yetenek_ac` sunulur; model
ihtiyac duydugu alan(lar)i secince yalniz o alanlarin gercek arac semalari
acilir. Kod kullanici metnini siniflandirmaz, kelime aramaz ve hangi gercek
aracin calisacagina karar vermez.

Resmi dayanak (2026-09-25):
- OpenAI tool search / namespace: model basta yalniz grup adi + aciklamasini
  gorur, grubu yukleyince araclari gelir; yuklenen araclar sonraki turlarda
  tekrar yuklenmeden kullanilir; grup basina 10'dan az arac onerilir.
- Anthropic tool search: yuklenen araclar run boyunca baglamda kalir;
  secim dogrulugu 30-50 aracin ustunde duser.
Bu yuzden: acilan alanlar run boyunca acik kalir, tek cagrida birden fazla
alan acilabilir ve her alanda 10'dan az arac vardir.
"""

from chat.agent_runtime import AGENT_CONTRACT as AJAN_SOZLESMESI  # noqa: F401

YETENEK_AC_ADI = "yetenek_ac"

# 74 gercek arac tek ve benzersiz bir yetenek alaninda yer alir. Bu tablo
# kullanici metnini yorumlamaz; yalniz modelin sectigi alan adini gercek
# arac semalarina ceviren katalogdur.
YETENEK_ALANLARI = {
    "internet_ara": (
        "web_search", "haber_ara", "zamanli_ara", "site_ara",
        "gorsel_ara", "kitap_ara", "sirket_ara", "hava_durumu",
    ),
    "internet_oku": ("derin_oku", "sayfa_oku", "adres_kontrol"),
    "harita": ("harita_goster", "konum_coz", "sube_bul", "harita_dedektif",
               "poi_ara", "mesafe_hesapla", "rota_hesapla", "mesafe_sure",
               "bolge_kaydet"),
    "takip": ("takip_baslat", "takip_listele", "takip_durdur",
              "takip_kontrol", "gorev_devret"),
    "dosyalar": (
        "read_file", "list_files", "belge_ara", "dosya_bilgi",
        "icerik_ara", "write_file_tool",
    ),
    "projeler": (
        "git_durum", "github_durum", "git_gecmis", "git_degisenler",
        "testleri_kos", "saglik_raporu",
    ),
    "gorevler": (
        "get_reminders", "add_task", "list_tasks", "complete_task",
        "update_task_status", "simdi", "hatirlatma_kur",
        "hatirlatma_listele", "hatirlatma_sil",
    ),
    "hafiza": ("hafiza_ara",),
    "gorsel": ("image_analyze", "gorsel_uret"),
    "katalog": (
        "fatura_oku", "katalog_kur", "katalog_getir", "katalog_liste",
        "katalog_fiyat_guncelle", "urun_eslestir",
    ),
    "yayin": (
        "katalog_onayla", "yetki_belgesi_ekle", "yayin_paketi", "cikti_oku",
    ),
    "matris": ("matris_ac", "matris_liste", "matris_durum"),
    "matris_satir": (
        "satir_ekle", "kanit_ekle", "satir_kapat", "satir_ac",
        "satir_sil", "satir_tasi", "satir_duzenle",
    ),
    "masaustu": ("ac_uygulama",),
    "hesap": ("hesapla",),
    "tarayici": ("sayfa_bakis", "sayfa_tikla", "sayfa_yaz", "sayfa_tus",
                 "sayfa_kaydir"),
    "freetools": ("freetools_ara", "freetools_calistir"),
    "ajanlar": ("ajan_modelleri", "alt_ajan", "alt_ajan_sonuclari"),
    "baglantilar": ("baglanti_liste", "baglanti_araclari", "baglanti_cagir"),
    "bulut_calisma": ("kod_dosya", "kod_calistir", "bulut_tarayici"),
}

ALAN_ACIKLAMALARI = {
    "ajanlar": "mevcut model havuzu, bagimsiz alt gorev olusturma ve alt gorev sonuclari",
    "baglantilar": "kullaniciya ait GitHub, Google, Notion ve MCP baglantilarinin gercek araclari",
    "bulut_calisma": "izole calisma alani dosyalari, kod komutlari ve bulut tarayicisi",
    "internet_ara": "web, haber, tarihli, site, gorsel, kitap, sirket ve "
                    "hava durumu aramasi",
    "internet_oku": "bilinen bir URL'nin sayfasini okuma veya adresin canli "
                    "olup olmadigini kontrol",
    "harita": "adres/yer icin harita baglantisi, yol tarifi, enlem/boylam "
              "koordinati, markanin bolgede kayitli subeleri, iki konum "
              "arasi karayolu mesafesi/sure ve bu parcalarin tek cagrida "
              "baglandigi harita zinciri",
    "dosyalar": "bilgisayardaki dosya/klasor ve proje icerigi; knowledge yazma",
    "projeler": "Git, GitHub, CI, test ve proje hat sagligi",
    "gorevler": "yerel gorevler, zamanli hatirlatmalar ve cihazdan "
                "dogrulanan su anki tarih/saat",
    "hafiza": "Basak'in kalici hafizasinda arama",
    "gorsel": "yerel goruntu analizi veya yeni gorsel uretimi",
    "katalog": "fatura okuma, urun karti kurma/okuma, fiyat ve tedarikci "
               "eslestirme",
    "yayin": "katalogdan Vixrex cikti dosyalari, izin belgesi, yayin paketi "
             "denetimi ve cikti okuma",
    "matris": "fikir/plan tablosu acma, listeleme ve tablonun tamamini okuma",
    "matris_satir": "tablo satiri ekleme, kanit, kapatma, acma, arsivleme, "
                    "tasima ve duzeltme",
    "masaustu": "beyaz listedeki masaustu uygulamasini acma",
    "hesap": "guvenli matematik hesabi",
    "freetools": "freetools.org katalogunda arama ve oradaki bir araci "
                 "tarayicida calistirip sonucunu okuma",
    "tarayici": "kullanicinin acik sekmesindeki sayfayi okuma, ogeye "
                "tikla, alana yazma, klavye tusu gonderme ve sayfayi kaydirma "
                "(eklenti kurulu ve bagli olmali)",
    "takip": "firma takibi baslatma/listeleme/durdurma/kontrol ve web "
             "gorevini panele devretme",
}

_ALAN_METNI = "; ".join(
    "%s=%s" % (ad, ALAN_ACIKLAMALARI[ad]) for ad in YETENEK_ALANLARI
)

YETENEK_AC_ARACI = {
    "type": "function",
    "function": {
        "name": YETENEK_AC_ADI,
        "description": (
            "Bir veya birkac yetenek alanini acar. Acilan alanlarin gercek "
            "arac semalari sonraki turda gelir ve run boyunca acik kalir. "
            "Doner: acik alanlar ve kullanilabilir arac adlari. Alan adlari "
            "arac adi degildir; arac olarak yalniz acilan alandin semalari "
            "cagrilir. Alanlar: "
            + _ALAN_METNI
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "alanlar": {
                    "type": "array",
                    "items": {
                        "type": "string",
                        "enum": list(YETENEK_ALANLARI.keys()),
                    },
                    "minItems": 1,
                    "description": "Acilacak yetenek alanlari",
                }
            },
            "required": ["alanlar"],
        },
    },
}


def baslangic_araclari(katalog=None):
    """Ilk turda modele sunulan tek sema: yetenek_ac."""
    if katalog is None:
        return [YETENEK_AC_ARACI]
    import copy
    names = {t['function']['name'] for t in katalog}
    areas = [area for area, tools in YETENEK_ALANLARI.items() if names.intersection(tools)]
    schema = copy.deepcopy(YETENEK_AC_ARACI)
    schema['function']['parameters']['properties']['alanlar']['items']['enum'] = areas
    schema['function']['description'] = (
        'Bir veya birkac yetenek alanini acar; bu kosudaki gercek arac semalarini doner. Alanlar: ' +
        '; '.join(area + '=' + ALAN_ACIKLAMALARI[area] for area in areas))
    return [schema]


def istenen_alanlar(args):
    """yetenek_ac argumanindan alan adlarini okur (liste veya tek ad)."""
    args = args if isinstance(args, dict) else {}
    ham = args.get("alanlar")
    if ham is None:
        ham = args.get("alan")
    if isinstance(ham, str):
        ham = [ham]
    if not isinstance(ham, (list, tuple)):
        return []
    sonuc = []
    for ad in ham:
        ad = str(ad or "").strip()
        if ad and ad not in sonuc:
            sonuc.append(ad)
    return sonuc


def acik_alan_araclari(katalog, acik_alanlar):
    """Acik alanlarin gercek semalari + yetenek_ac (yeni alan acabilmek icin)."""
    adlar = set()
    for alan in acik_alanlar or ():
        adlar.update(YETENEK_ALANLARI.get(alan, ()))
    secilen = [
        arac for arac in (katalog or [])
        if isinstance(arac, dict)
        and (arac.get("function") or {}).get("name") in adlar
    ]
    from chat.platform_context import current
    return secilen + baslangic_araclari(katalog if current() is not None else None)
