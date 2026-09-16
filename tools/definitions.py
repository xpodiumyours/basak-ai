"""tools/definitions.py — Modele sunulan araç şemaları.

Açıklamalar YALNIZ olguyu söyler: araç ne yapar, hangi parametreyi alır,
ne döndürür, sınırı nedir. Davranış koçluğu ("şunu kullanma", "şöyle
cevapla") buraya YAZILMAZ — o, aracın etrafına sarılmış bir kural
katmanıdır ve 2026-09-13'te bilerek söküldü. Hangi aracı seçeceğine
model karar verir.

Dokuz + dort + bes + dokuz arac: okuyanlar serbest, etkisi olanlar
dar tablolarda (dosya/gorev/tablo yazma, sabit komut, beyaz liste).
(2026-09-15: toplam 51; ara-toplam formulu bayat oldugu icin kaldirildi.)
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
    "Internette arar; baslik+adres+metin listesi doner (varsayilan 20, "
    "en fazla 30 sonuc).",
    {"query": {"type": "string", "description": "Sorgu"},
     "adet": {"type": "integer",
              "description": "Sonuc sayisi (1-30, bossa 20)"}},
    ["query"],
)

HABER_ARA = _arac(
    "haber_ara",
    "Haber arar; baslik+adres+tarih+metin doner (en fazla 10). Tarih "
    "yoksa tarihsiz yazar.",
    {"query": {"type": "string", "description": "Sorgu"},
     "adet": {"type": "integer",
              "description": "Sonuc sayisi (1-30, bossa 10)"}},
    ["query"],
)

ZAMANLI_ARA = _arac(
    "zamanli_ara",
    "Tarih filtreli arar; yalniz verilen aralik doner (en fazla 10).",
    {"query": {"type": "string", "description": "Sorgu"},
     "aralik": {"type": "string",
                "description": "gun | hafta | ay"},
     "adet": {"type": "integer",
              "description": "Sonuc sayisi (1-30, bossa 10)"}},
    ["query", "aralik"],
)

SITE_ARA = _arac(
    "site_ara",
    "Yalniz verilen sitede arar; baslik+adres+metin doner (en fazla 10).",
    {"site": {"type": "string", "description": "Orn. ornek.com"},
     "sorgu": {"type": "string", "description": "Sorgu"},
     "adet": {"type": "integer",
              "description": "Sonuc sayisi (1-30, bossa 10)"}},
    ["site", "sorgu"],
)

GORSEL_ARA = _arac(
    "gorsel_ara",
    "Gorsel arar; resim adreslerini JSON liste doner (en fazla 10).",
    {"query": {"type": "string", "description": "Sorgu"},
     "adet": {"type": "integer",
              "description": "Sonuc sayisi (1-30, bossa 10)"}},
    ["query"],
)

KITAP_ARA = _arac(
    "kitap_ara",
    "Kitap/katalog/brosur arar; baslik+adres+metin doner (en fazla 10).",
    {"query": {"type": "string", "description": "Sorgu"},
     "adet": {"type": "integer",
              "description": "Sonuc sayisi (1-30, bossa 10)"}},
    ["query"],
)

DERIN_OKU = _arac(
    "derin_oku",
    "Uzun sayfalar icin sayfa okuma; duz metnini doner (en fazla "
    "500000 karakter). Yalniz http/https 80/443; ic ag yasak.",
    {"url": {"type": "string", "description": "Adres"}},
    ["url"],
)

SAYFA_OKU = _arac(
    "sayfa_oku",
    "Sayfayi acar, duz metnini doner (en fazla 200000 karakter). Yalniz "
    "http/https 80/443; ic ag yasak.",
    {"url": {"type": "string", "description": "Adres"}},
    ["url"],
)

DOSYA_OKU = _arac(
    "read_file",
    "Bu bilgisayardaki gercek dosyanin icerigini doner. Sifre "
    "(.env/.pem/.key/ayarlar.json) ve sistem klasorleri yasak.",
    {"path": {"type": "string", "description": "Dosya yolu"}},
    ["path"],
)

KLASOR_LISTELE = _arac(
    "list_files",
    "Bu bilgisayardaki gercek klasorun icindekileri doner: ad+boyut. "
    "Ad veya tam yol verilir.",
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
    "Proje kokundeki .md'lerde arar (alta inmez). Dosya:satir:icerik "
    "doner (en fazla 200).",
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
    "Listeye gorev ekler; no+metin doner. Tarih gerekiyorsa YYYY-MM-DD "
    "olarak date alaniyla verilir.",
    {"text": {"type": "string", "description": "Gorev"},
     "date": {"type": "string",
              "description": "Tarih (YYYY-MM-DD, bossa bugun)"}},
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
    "Projenin her yerinde arar; dosya:satir doner (en fazla 8 eslesme, "
    "toplam 8000 karakter). Sifre dosyalari acilmaz, anahtarlar "
    "maskelenir.",
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
    "Proje testlerini kosturur, ozet doner (son 2000 karakter). Komut "
    "sabit; vixrex yok.",
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
    "Hafizada derin arama yapar. Doner: en ilgili en fazla 5 kayit "
    "(kaynak/tur etiketli).",
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

FATURA_OKU = _arac(
    "fatura_oku",
    "Kayitli fatura fotografini okur; yazi ve aday satirlari JSON doner. "
    "Once yerel goz dener, yoksa bulut; kaynak alanda yazar. PDF yok.",
    {"fatura_id": {"type": "string",
                   "description": "Yukleme kimligi"}},
    ["fatura_id"],
)

KATALOG_KUR = _arac(
    "katalog_kur",
    "Fatura satirlarindan urun kartlari kurar (en fazla 500 satir); ayni "
    "marka+kod tek kart olur, kategori cogunlukla secilir, stok 3 ve "
    "alti az gosterir. Is ozeti JSON doner.",
    {"fatura_id": {"type": "string",
                   "description": "Yukleme kimligi"},
     "satirlar": {"type": "array",
                  "description": "Satirlar: marka, kod, urun_adi, barkod, "
                                 "beden, renk, varyant, adet, alis_fiyat, "
                                 "kategori"}},
    ["fatura_id", "satirlar"],
)

KATALOG_GETIR = _arac(
    "katalog_getir",
    "Katalog isinin tamamini JSON doner.",
    {"is_id": {"type": "string", "description": "Is kimligi"}},
    ["is_id"],
)

KATALOG_LISTELE = _arac(
    "katalog_liste",
    "Katalog islerini listeler: is kimligi, durum, kart sayisi.",
    {},
    [],
)

KATALOG_FIYAT = _arac(
    "katalog_fiyat_guncelle",
    "Kartin satis fiyatini yazar. Fiyat metin veya sayi olur; tam sayi "
    "duz, diger iki ondalik yazilir.",
    {"is_id": {"type": "string", "description": "Is kimligi"},
     "kart_id": {"type": "string", "description": "Kart kimligi"},
     "satis_fiyat": {"type": "string", "description": "Satis fiyati"}},
    ["is_id", "kart_id", "satis_fiyat"],
)

KATALOG_ONAYLA = _arac(
    "katalog_onayla",
    "Katalogdan Vixrex CSV + batch JSON + tam katalog dosyasi uretir, "
    "dosya adlarini doner.",
    {"is_id": {"type": "string", "description": "Is kimligi"}},
    ["is_id"],
)

YETKI_BELGESI = _arac(
    "yetki_belgesi_ekle",
    "Uretici kullanim izni belgesini markaya baglayarak saklar; ayni "
    "markanin sonraki islerini kapsar.",
    {"is_id": {"type": "string", "description": "Is kimligi (bossa baglanmaz)"},
     "b64": {"type": "string", "description": "Belge verisi (base64)"},
     "ad": {"type": "string", "description": "Dosya adi"},
     "marka": {"type": "string",
               "description": "Marka (bossa isten alinir)"}},
    ["b64", "ad"],
)

URUN_ESLESTIR = _arac(
    "urun_eslestir",
    "Karti kayitli tedarikcinin resmi sitesinde arar (su an yalniz "
    "Tutku); kaynak, guven ve gorselleri karta isler. Kayit disi "
    "markada hata doner.",
    {"is_id": {"type": "string", "description": "Is kimligi"},
     "kart_id": {"type": "string", "description": "Kart kimligi"}},
    ["is_id", "kart_id"],
)

YAYIN_PAKETI = _arac(
    "yayin_paketi",
    "Ciktiyi platformun yukleme kurallarina gore denetler; kabul "
    "karari, is uyarilari (fiyatsiz/izinsiz/dusuk guven), dosya adlari "
    "ve izlenecek adimi doner. Yazma yok.",
    {"is_id": {"type": "string", "description": "Is kimligi"},
     "platform": {"type": "string", "description": "vixrex"}},
    ["is_id"],
)

# Model araci DEGIL, giris notu: fatura dosyasi UI/Telegram ile yuklenir
# (fatura_kaydet_b64 semasizdir); model hatta fatura_oku ile baslar.
CIKTI_OKU = _arac(
    "cikti_oku",
    "Onay ciktisinin icerigini metin doner: vixrex_urunler.csv, "
    "vixrex_batch.json veya basak_katalog.json.",
    {"is_id": {"type": "string", "description": "Is kimligi"},
     "dosya": {"type": "string",
               "description": "vixrex_urunler.csv | vixrex_batch.json | "
                              "basak_katalog.json"}},
    ["is_id", "dosya"],
)

TOOLS = [WEB_ARAMA, HABER_ARA, ZAMANLI_ARA, SITE_ARA, GORSEL_ARA,
          KITAP_ARA, DERIN_OKU, SAYFA_OKU, DOSYA_OKU, KLASOR_LISTELE, GIT_DURUM,
         BELGE_ARA, DOSYA_BILGI, GORUNTU_OKU, DOSYA_YAZ,
         HATIRLATMA_OZET, GOREV_EKLE, GOREV_LISTELE, GOREV_BITIR,
         UYGULAMA_AC, ICERIK_ARA, GITHUB_DURUM,
         GIT_GECMIS, GIT_DEGISENLER, ADRES_KONTROL, TEST_KOS,
         MATRIS_AC, MATRIS_LISTE, SATIR_EKLE, KANIT_EKLE,
         SATIR_KAPAT, SATIR_AC, SATIR_SIL, SATIR_TASI,
         MATRIS_DURUM, GORSEL_URET, SAGLIK_RAPORU, SATIR_DUZENLE,
         SIMDI, HESAPLA, HAFIZA_ARA,
         FATURA_OKU, KATALOG_KUR, KATALOG_GETIR, KATALOG_LISTELE,
         KATALOG_FIYAT, KATALOG_ONAYLA, YETKI_BELGESI, URUN_ESLESTIR,
         YAYIN_PAKETI, CIKTI_OKU]

# Beyaz liste: model bu adlarin disinda bir arac uydurursa CALISMAZ.
# Yetkiyi kod verir, model kendine yetki yazamaz.
TANINMIS_TOOLLAR = frozenset(t["function"]["name"] for t in TOOLS)
