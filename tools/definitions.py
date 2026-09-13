"""tools/definitions.py — Modele sunulan araç şemaları.

Açıklamalar YALNIZ olguyu söyler: araç ne yapar, hangi parametreyi alır,
ne döndürür, sınırı nedir. Davranış koçluğu ("şunu kullanma", "şöyle
cevapla") buraya YAZILMAZ — o, aracın etrafına sarılmış bir kural
katmanıdır ve 2026-09-13'te bilerek söküldü. Hangi aracı seçeceğine
model karar verir.

Dokuz + dort + bes + dokuz arac: okuyanlar serbest, etkisi olanlar
dar tablolarda (dosya/gorev/tablo yazma, sabit komut, beyaz liste).
"""


def _arac(ad, aciklama, ozellikler, zorunlu):
    return {
        "type": "function",
        "function": {
            "name": ad,
            "description": aciklama,
            "parameters": {
                "type": "object",
                "properties": ozellikler,
                "required": zorunlu,
            },
        },
    }


_PROJE = {"type": "string",
          "description": "basak | vixrex | numeramatch | xses"}

WEB_ARAMA = _arac(
    "web_search",
    "Internette arar; baslik+kisa metin listesi doner.",
    {"query": {"type": "string", "description": "Sorgu"}},
    ["query"],
)

SAYFA_OKU = _arac(
    "sayfa_oku",
    "Sayfayi acar, duz metnini doner (en fazla 5000 karakter). Yalniz "
    "http/https 80/443; ic ag yasak.",
    {"url": {"type": "string", "description": "Adres"}},
    ["url"],
)

DOSYA_OKU = _arac(
    "read_file",
    "Dosya icerigini doner. Sifre (.env/.pem/.key/ayarlar.json) ve "
    "sistem klasorleri yasak.",
    {"path": {"type": "string", "description": "Dosya yolu"}},
    ["path"],
)

KLASOR_LISTELE = _arac(
    "list_files",
    "Klasordekileri doner: ad+boyut. Ad veya tam yol verilir.",
    {"folder": {"type": "string", "description": "Klasor"}},
    ["folder"],
)

GIT_DURUM = _arac(
    "git_durum",
    "Projenin anlik durumu: dal, son commit, kirli dosya sayisi + ilk "
    "10 ad.",
    {"proje": _PROJE},
    ["proje"],
)

BELGE_ARA = _arac(
    "belge_ara",
    "Proje kokundeki .md'lerde arar (alta inmez). Dosya:satir doner.",
    {"proje": _PROJE,
     "sorgu": {"type": "string", "description": "Metin"}},
    ["proje", "sorgu"],
)

DOSYA_BILGI = _arac(
    "dosya_bilgi",
    "Dosya/klasor var mi, boyut, son degisim. Icerigi okumaz.",
    {"proje": _PROJE,
     "yol": {"type": "string", "description": "Koke gore yol"}},
    ["proje", "yol"],
)

GORUNTU_OKU = _arac(
    "image_analyze",
    "Goruntuyu aciklar; soru verilirse ona odaklanir.",
    {"path": {"type": "string", "description": "Goruntu yolu"},
     "soru": {"type": "string", "description": "Soru"}},
    ["path"],
)

DOSYA_YAZ = _arac(
    "write_file_tool",
    "knowledge/ altina yazar, yolu doner. Disi reddedilir.",
    {"path": {"type": "string", "description": "knowledge/ alti yol"},
     "content": {"type": "string", "description": "Icerik"}},
    ["path", "content"],
)

HATIRLATMA_OZET = _arac(
    "get_reminders",
    "Bugunun hatirlatma+gorev ozeti.",
    {},
    [],
)

GOREV_EKLE = _arac(
    "add_task",
    "Listeye gorev ekler; no+metin doner.",
    {"text": {"type": "string", "description": "Gorev"}},
    ["text"],
)

GOREV_LISTELE = _arac(
    "list_tasks",
    "Gorevler: no, metin, durum, tarih.",
    {},
    [],
)

GOREV_BITIR = _arac(
    "complete_task",
    "Nodaki gorevi kapatir.",
    {"task_id": {"type": "integer", "description": "Gorev no"}},
    ["task_id"],
)

UYGULAMA_AC = _arac(
    "ac_uygulama",
    "Beyaz listedekini acar: tarayici, notepad, calculator, "
    "file_manager, vscode. Disi reddedilir.",
    {"uygulama": {"type": "string", "description": "Ad"},
     "parametre": {"type": "string", "description": "Adres/yol"}},
    ["uygulama"],
)

ICERIK_ARA = _arac(
    "icerik_ara",
    "Projenin her yerinde arar; dosya:satir doner (en fazla 8). Sifre "
    "dosyalari acilmaz, anahtarlar maskelenir.",
    {"proje": _PROJE,
     "sorgu": {"type": "string", "description": "Metin"},
     "uzanti": {"type": "string", "description": "Orn. .py"}},
    ["proje", "sorgu"],
)

GITHUB_DURUM = _arac(
    "github_durum",
    "PR/CI okur (salt-okunur): liste, detay veya son 5 kosu. Yazan "
    "komut yok.",
    {"islem": {"type": "string",
               "description": "pr_liste | pr_goruntule | calisma_liste"},
     "proje": _PROJE,
     "no": {"type": "integer", "description": "PR no"},
     "durum": {"type": "string",
               "description": "open, closed, merged, all"}},
    ["islem", "proje"],
)

GIT_GECMIS = _arac(
    "git_gecmis",
    "Son commitler (en fazla 30).",
    {"proje": _PROJE,
     "dosya": {"type": "string", "description": "Tek dosya suzgeci"},
     "adet": {"type": "integer", "description": "Kac commit"}},
    ["proje"],
)

GIT_DEGISENLER = _arac(
    "git_degisenler",
    "Taban ile HEAD arasi ozet (diff --stat).",
    {"proje": _PROJE,
     "taban": {"type": "string", "description": "Orn. origin/master"}},
    ["proje"],
)

ADRES_KONTROL = _arac(
    "adres_kontrol",
    "Adres canli mi: durum kodu, sure, son adres. Govde inmez; ic ag "
    "yasak.",
    {"url": {"type": "string", "description": "Adres"}},
    ["url"],
)

TEST_KOS = _arac(
    "testleri_kos",
    "Proje testlerini kosturur, ozet doner. Komut sabit; vixrex yok.",
    {"proje": {"type": "string",
               "description": "basak | numeramatch | xses"}},
    ["proje"],
)

MATRIS_AC = _arac(
    "matris_ac",
    "Fikir tablosu acar, numarasini doner. Agac canlidir.",
    {"baslik": {"type": "string", "description": "Baslik"},
     "fikir": {"type": "string", "description": "Fikir ozeti"}},
    ["baslik"],
)

MATRIS_LISTE = _arac(
    "matris_liste",
    "Tablolar + skorlari.",
    {},
    [],
)

SATIR_EKLE = _arac(
    "satir_ekle",
    "Satira ekler, numarasini doner. ust bos=kok. bagli: once "
    "bitecekler.",
    {"matris": {"type": "integer", "description": "Tablo no"},
     "tur": {"type": "string",
             "description": "arastirma | katman | adim | detay"},
     "metin": {"type": "string", "description": "Satir"},
     "ust": {"type": "integer", "description": "Ust no (bos=kok)"},
     "neden": {"type": "string", "description": "Ne ise yaradigi"},
     "bagli": {"type": "array", "description": "Once bitecek no'lar"}},
    ["matris", "tur", "metin"],
)

KANIT_EKLE = _arac(
    "kanit_ekle",
    "Satira kanit yazar. Kanitsiz kapanmaz.",
    {"matris": {"type": "integer", "description": "Tablo no"},
     "satir": {"type": "integer", "description": "Satir no"},
     "kanit": {"type": "string", "description": "Kanit"}},
    ["matris", "satir", "kanit"],
)

SATIR_KAPAT = _arac(
    "satir_kapat",
    "Kanitli kapatir. Kanitsiz veya baglisi bitmemisse red.",
    {"matris": {"type": "integer", "description": "Tablo no"},
     "satir": {"type": "integer", "description": "Satir no"}},
    ["matris", "satir"],
)

SATIR_AC = _arac(
    "satir_ac",
    "Kapanani yeniden acar.",
    {"matris": {"type": "integer", "description": "Tablo no"},
     "satir": {"type": "integer", "description": "Satir no"}},
    ["matris", "satir"],
)

SATIR_SIL = _arac(
    "satir_sil",
    "Arsive kaldirir (skor disi). Altlar bir uste baglanir.",
    {"matris": {"type": "integer", "description": "Tablo no"},
     "satir": {"type": "integer", "description": "Satir no"}},
    ["matris", "satir"],
)

SATIR_TASI = _arac(
    "satir_tasi",
    "Dali tasir. Dongu red.",
    {"matris": {"type": "integer", "description": "Tablo no"},
     "satir": {"type": "integer", "description": "Satir no"},
     "yeni_ust": {"type": "integer", "description": "Yeni ust (bos=kok)"}},
    ["matris", "satir"],
)

SATIR_DUZENLE = _arac(
    "satir_duzenle",
    "Satir yazisini duzeltir. Durum, kanit, baglanti degismez.",
    {"matris": {"type": "integer", "description": "Tablo no"},
     "satir": {"type": "integer", "description": "Satir no"},
     "metin": {"type": "string", "description": "Yeni yazi"},
     "neden": {"type": "string", "description": "Yeni neden"}},
    ["matris", "satir"],
)

SIMDI = _arac(
    "simdi",
    "Su anki tarih ve saati doner: gun, ay, yil, haftanin gunu, saat.",
    {},
    [],
)

HESAPLA = _arac(
    "hesapla",
    "Dort islem yapar: + - * / % ** ve parantez. Doner: sonuc.",
    {"ifade": {"type": "string", "description": "Orn. (120*18)/100"}},
    ["ifade"],
)

HAFIZA_ARA = _arac(
    "hafiza_ara",
    "Hafizada derin arama yapar. Doner: en ilgili kayitlarin tamami.",
    {"sorgu": {"type": "string", "description": "Aranacak konu"}},
    ["sorgu"],
)

MATRIS_DURUM = _arac(
    "matris_durum",
    "Agac + skor, tamami.",
    {"matris": {"type": "integer", "description": "Tablo no"}},
    ["matris"],
)

GORSEL_URET = _arac(
    "gorsel_uret",
    "Aciklamadan gorsel uretir, dosyaya kaydeder. Doner: yol.",
    {"aciklama": {"type": "string", "description": "Ne cizilsin"},
     "genislik": {"type": "integer", "description": "En (256-2048)"},
     "yukseklik": {"type": "integer", "description": "Boy (256-2048)"}},
    ["aciklama"],
)

SAGLIK_RAPORU = _arac(
    "saglik_raporu",
    "Hatlarin durumunu gosterir: deneme, basari, sure, kota. Ag yok.",
    {},
    [],
)

TOOLS = [WEB_ARAMA, SAYFA_OKU, DOSYA_OKU, KLASOR_LISTELE, GIT_DURUM,
         BELGE_ARA, DOSYA_BILGI, GORUNTU_OKU, DOSYA_YAZ,
         HATIRLATMA_OZET, GOREV_EKLE, GOREV_LISTELE, GOREV_BITIR,
         UYGULAMA_AC, ICERIK_ARA, GITHUB_DURUM,
         GIT_GECMIS, GIT_DEGISENLER, ADRES_KONTROL, TEST_KOS,
         MATRIS_AC, MATRIS_LISTE, SATIR_EKLE, KANIT_EKLE,
         SATIR_KAPAT, SATIR_AC, SATIR_SIL, SATIR_TASI,
         MATRIS_DURUM, GORSEL_URET, SAGLIK_RAPORU, SATIR_DUZENLE,
         SIMDI, HESAPLA, HAFIZA_ARA]

# Beyaz liste: model bu adlarin disinda bir arac uydurursa CALISMAZ.
# Yetkiyi kod verir, model kendine yetki yazamaz.
TANINMIS_TOOLLAR = frozenset(t["function"]["name"] for t in TOOLS)
