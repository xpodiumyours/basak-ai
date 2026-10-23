"""tools/definitions.py — Modele sunulan araç şemaları.

Açıklamalar YALNIZ olguyu söyler: araç ne yapar, hangi parametreyi alır,
ne döndürür, sınırı nedir. Davranış koçluğu ("şunu kullanma", "şöyle
cevapla") buraya YAZILMAZ — o, aracın etrafına sarılmış bir kural
katmanıdır ve 2026-09-13'te bilerek söküldü. Hangi aracı seçeceğine
model karar verir.

Okuyanlar serbest, etkisi olanlar dar tablolarda (dosya/gorev/tablo
yazma, sabit komut, beyaz liste).
(2026-09-15: toplam 52; ara-toplam formulu bayat oldugu icin kaldirildi.
2026-09-23: hava_durumu eklendi — 53. 2026-10-01: harita_goster eklendi —
56; ayni gun konum_coz eklendi — 57; 2026-10-17: update_task_status
eklendi — 58; 2026-10-20: sube_bul eklendi; 2026-10-21: sayfa_bakis
eklendi — 60; ayni gun sayfa_tikla + sayfa_yaz eklendi — 62; 2026-10-22:
harita_dedektif eklendi (zincir) — guncel toplam 74 (2026-10-23: poi_ara + mesafe_hesapla + rota_hesapla + bolge_kaydet + gorev_devret + 4 takip); sayi testlerle
kilitli,
bak: tests/test_seviye0_sozlesme.py + tests/test_agent_protocol.py.)
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
    "Uzun sayfayi parca/cursor ile okur. Her cagrida en fazla 50000 "
    "karakter doner; meta.sonraki_baslangic varsa ayni URL'yi o "
    "baslangicla devam ettir. Kaynak erisim tavani 500000 karakterdir; "
    "tavan asilirsa meta bunu acikca soyler. Yalniz http/https 80/443.",
    {
        "url": {"type": "string", "description": "Adres"},
        "baslangic": {"type": "integer", "description": "Karakter offseti"},
        "uzunluk": {"type": "integer",
                    "description": "1-50000, varsayilan 40000"},
    },
    ["url"],
)

SAYFA_OKU = _arac(
    "sayfa_oku",
    "Sayfayi parca/cursor ile okur. Her cagrida en fazla 50000 karakter "
    "doner; meta.sonraki_baslangic varsa ayni URL'yi devam ettir. "
    "Kaynak erisim tavani 200000 karakterdir; tavan asilirsa acik meta "
    "doner. Yalniz http/https 80/443; ic ag yasak.",
    {
        "url": {"type": "string", "description": "Adres"},
        "baslangic": {"type": "integer", "description": "Karakter offseti"},
        "uzunluk": {"type": "integer",
                    "description": "1-50000, varsayilan 30000"},
    },
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

GOREV_GUNCELLE = _arac(
    "update_task_status",
    "Gorev durumunu gunceller (pending/in_progress/paused/done).",
    {"task_id": {"type": "integer", "description": "Gorev no"},
     "status": {"type": "string",
                "enum": ["pending", "in_progress", "paused", "done"],
                "description": "Yeni durum"},
     "note": {"type": "string", "description": "Not (opsiyonel)"}},
    ["task_id", "status"],
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
    "Bu cihazin sistem saatinden dogrulanmis su anki yerel tarih ve saati "
    "doner: gun, ay, yil, haftanin gunu, saat.",
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
    "Aciklamadan gorsel uretir, kaydeder. Doner: /gorsel/<ad> goreli adresi.",
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
    "Kayitli fatura fotografini OCR/goru ile okur; yazi, aday satirlar ve "
    "ustbilgi doner. Bu arac gercek urun dogrulamasi yapmaz. Faturadan "
    "gercek urune giden bir istekte sonra katalog_kur, ardindan "
    "urun_eslestir(tum_kartlar=true) gerekir. PDF yok.",
    {"fatura_id": {"type": "string",
                   "description": "Yukleme kimligi"}},
    ["fatura_id"],
)

KATALOG_KUR = _arac(
    "katalog_kur",
    "Fatura satirlarindan taslak urun kartlari kurar (en fazla 500 satir); "
    "ayni marka+kod tek kart olur. Bu arac gercek dijital urunu henuz "
    "dogrulamaz. Sonuctaki is_id ile gercek urun tespiti isteniyorsa "
    "urun_eslestir(is_id, tum_kartlar=true) cagir. Donen JSON sonraki "
    "adimi acikca tasir. ustbilgi fatura_oku sonucundan gelir.",
    {"fatura_id": {"type": "string",
                   "description": "Yukleme kimligi"},
     "satirlar": {"type": "array",
                  "description": "Satirlar: marka, kod, urun_adi, barkod, "
                                 "beden, renk, varyant, adet, alis_fiyat, "
                                 "tutar (faturadaki satir toplami), "
                                 "kategori"},
     "ustbilgi": {"type": "object",
                  "description": "fatura_oku ustbilgi alani (fis_no, "
                                 "ettn, tarih, saat, firma, alici, vkn, "
                                 "alici_vkn, vergi_dairesi, "
                                 "alici_vergi_dairesi, mersis_no, "
                                 "kdv_oran, ara_toplam, kdv_tutar, "
                                 "toplam, para_birimi)"}},
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
    "Bir karti veya tum katalog kartlarini marka listesine bagli kalmadan "
    "kamuya acik webde cozer. Barkod/GTIN, SKU/MPN, marka, Schema.org "
    "Product verisi ve kaynak rolunu kanit olarak kullanir; uydurma yapmaz. "
    "tum_kartlar=true ise kartlari sinirli paralellikle topluca eslestirir. "
    "Fatura -> gercek urun zincirinin resmi urun dogrulama asamasi budur.",
    {"is_id": {"type": "string", "description": "Is kimligi"},
     "kart_id": {"type": "string",
                 "description": "Tek kart kimligi; tum kartlarda bos birak"},
     "tum_kartlar": {"type": "boolean",
                     "description": "Katalogdaki tum kartlari eslestir"}},
    ["is_id"],
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

HAVA_DURUMU = _arac(
    "hava_durumu",
    "Sehir icin anlik hava durumunu Open-Meteo'dan okur. Doner: sicaklik, "
    "hava etiketi,ruzgar, saat + kaynak. Secili sehir bulunamazsa hata "
    "doner; anahtar gerekmez.",
    {"sehir": {"type": "string", "description": "Sehir adi (orn. Ankara)"}},
    ["sehir"],
)

HARITA_GOSTER = _arac(
    "harita_goster",
    "Konum icin Google Maps baglantisini uretir: haritada arama veya yol "
    "tarifi. Doner: konum, mod, baglanti, kaynak. Ag cagrisi yapmaz, API "
    "anahtari ve kota gerektirmez; yalniz baglanti metni uretir. Bos konum "
    "veya bilinmeyen mod hata doner.",
    {"konum": {"type": "string",
               "description": "Adres, yer adi veya 'enlem,boylam'"},
     "mod": {"type": "string",
             "description": "ara | yol (bossa yol)"}},
    ["konum"],
)

KONUM_COZ = _arac(
    "konum_coz",
    "Adres veya yer adini enlem/boylam koordinatina cevirir. Once Photon "
    "(OpenStreetMap), olmazsa Open-Meteo geocoding denenir. Doner: adres, "
    "enlem, boylam, gosterim_adi, kaynak, aday_sayisi, adaylar (her adayda "
    "gosterim_adi, tip, osm_id, posta_kodu, ulke_kodu), denenen_hatlar "
    "(her hattin durumu ve varsa hata sebebi). Photon bulanik eslestirir: "
    "sorguyla birebir ortusmeyen aday da donebilir, hangi eslesmenin "
    "alindigi aday listesinden gorulur. Ikisi de acik veri kullanir: kapı "
    "numarasi seviyesindeki Turkiye adresleri cogu zaman bulunamaz, "
    "mahalle/ilce seviyesi bulunur (2026-10-01 olcumu). Hicbir hat sonuc "
    "bulamazsa hata doner ve hata mesaji denenen hatlari yazar; koordinat "
    "uydurulmaz. Anahtar gerekmez; istek SSRF denetiminden gecer.",
    {"adres": {"type": "string",
               "description": "Adres veya yer adi (orn. Kadikoy Moda, "
                              "Istanbul)"}},
    ["adres"],
)

SUBE_BUL = _arac(
    "sube_bul",
    "Markanin bir bolgedeki kayitli subelerini OpenStreetMap (Overpass) "
    "uzerinden bulur. Doner: marka, merkez (enlem, boylam, gosterim_adi, "
    "kaynak), yaricap_km, sube_sayisi, subeler (ad, enlem, boylam, adres, "
    "tip, telefon, website, mesafe_km; en yakin ilk) ve OSM atfi. Anahtar "
    "gerekmez. sube_sayisi=0 hata degildir: sube OSM'de kayitli olmayabilir, "
    "bu ayrim `not` alaninda yazilir; sube UYDURULMAZ. Merkez "
    "konum_coz ile bulunur; bulunamazsa hata doner.",
    {"marka": {"type": "string", "description": "Marka adi (orn. BIM)"},
     "konum": {"type": "string",
               "description": "Merkez: 'enlem,boylam' ya da adres/yer adi"},
     "yaricap_km": {"type": "number",
                    "description": "Arama yaricapi km (5-25, bossa 5)"}},
    ["marka", "konum"],
)

HARITA_DEDEKTIF = _arac(
    "harita_dedektif",
    "Harita zincirini tek cagrida calistirir: merkez cozulur (konum_coz), "
    "markanin kayitli subeleri aranir (OpenStreetMap) ve her sube icin "
    "harita baglantisi uretilir; yol modunda baglanti merkezden sube "
    "gider. Doner: marka, merkez (enlem, boylam, gosterim_adi, kaynak), "
    "yaricap_km, mod, sube_sayisi, subeler (ad, enlem, boylam, adres, tip, "
    "telefon, website, mesafe_km, baglanti, ara_baglanti; en yakin ilk), "
    "baglantilar (merkez), veri_kaynagi, atif, not, denenen_hatlar, "
    "zincir. Anahtar gerekmez. sube_sayisi=0 hata degildir: sube OSM'de "
    "kayitli olmayabilir, bu ayrim `not` alaninda yazilir; sube ve "
    "baglanti UYDURULMAZ. Merkez bulunamazsa ya da OpenStreetMap servisine "
    "ulasilamazsa hata doner.",
    {"marka": {"type": "string", "description": "Marka adi (orn. BIM)"},
     "konum": {"type": "string",
               "description": "Merkez: 'enlem,boylam' ya da adres/yer adi"},
     "yaricap_km": {"type": "number",
                    "description": "Arama yaricapi km (5-25, bossa 5)"},
     "adet": {"type": "number",
              "description": "En fazla kac sube donulsun (0 = hepsi, 20)"},
     "mod": {"type": "string",
             "description": "Sube baglantisi: yol (merkezden tarifi) | ara"}},
    ["marka", "konum"],
)

POI_ARA = _arac(
    "poi_ara",
    "Etiket + bolge ile OpenStreetMap'te kayitli noktalari bulur. Doner: "
    "etiket, merkez, yaricap_m, sonuc_sayisi, sonuclar (ad, enlem, boylam, "
    "mesafe_km, osm_id), atif, not. Anahtar gerekmez. Sonuc 0 hata degildir.",
    {"etiket": {"type": "string",
               "description": "anahtar=deger (orn. amenity=cafe)"},
     "yer": {"type": "string",
             "description": "Merkez adres/yer adi (bossa enlem+boylam)"},
     "enlem": {"type": "number", "description": "Merkez enlemi"},
     "boylam": {"type": "number", "description": "Merkez boylami"},
     "yaricap_m": {"type": "number",
                   "description": "Yaricap metre (bossa 1500, en fazla 10000)"}},
    ["etiket"],
)

MESAFE_HESAPLA = _arac(
    "mesafe_hesapla",
    "Iki koordinat arasi duz mesafeyi hesaplar (kus ucusu). Doner: "
    "duz_mesafe_km, duz_mesafe_m, not. Ag cagrisi yok, anahtar gerekmez. "
    "Yol mesafesi degil.",
    {"enlem1": {"type": "number", "description": "Birinci nokta enlem"},
     "boylam1": {"type": "number", "description": "Birinci nokta boylam"},
     "enlem2": {"type": "number", "description": "Ikinci nokta enlem"},
     "boylam2": {"type": "number", "description": "Ikinci nokta boylam"}},
    ["enlem1", "boylam1", "enlem2", "boylam2"],
)

ROTA_HESAPLA = _arac(
    "rota_hesapla",
    "Iki nokta arasi yol mesafesi ve suresi hesaplar (OpenRouteService). "
    "Doner: yol_mesafe_km/m, sure_sn/metni, kaynak. Anahtar yoksa hata "
    "doner; kota/ret gelirse Turkce ret doner.",
    {"baslangic": {"type": "string",
                   "description": "Baslangic: 'enlem,boylam' ya da adres"},
     "bitis": {"type": "string",
               "description": "Bitis: 'enlem,boylam' ya da adres"}},
    ["baslangic", "bitis"],
)

BOLGE_KAYDET = _arac(
    "bolge_kaydet",
    "Bolge analizini .md dosyaya yazar (mevcut semantic indeks okur). "
    "Doner: yol, marka, sube_sayisi, atif. Uzanti .md; episodik kayit "
    "kullanilmaz.",
    {"marka": {"type": "string", "description": "Marka adi"},
     "konum": {"type": "string",
               "description": "Merkez: 'enlem,boylam' ya da adres"},
     "yaricap_km": {"type": "number",
                    "description": "Yaricap km (bossa 5, en fazla 25)"}},
    ["marka", "konum"],
)

GOREV_DEVRET = _arac(
    "gorev_devret",
    "Web sohbetindeki tarayici gorevini panele devir paketi uretir. Doner: "
    "gorev, adres, adimlar, not. Disk yazimi yok; paket panel tarafindan "
    "okunur.",
    {"gorev": {"type": "string",
              "description": "Panelde surdurulecek gorev metni"},
     "adres": {"type": "string",
               "description": "Hedef sayfa adresi (bossa acik sekme)"}},
    ["gorev"],
)

TAKIP_BASLAT = _arac(
    "takip_baslat",
    "Firmayi takibe alir (marka + adres). Doner: marka, site, durum. "
    "Ayni marka ikinci kez eklenmez.",
    {"marka": {"type": "string", "description": "Marka adi"},
     "adres": {"type": "string",
               "description": "Izlenen sayfa adresi (bossa sirket_ara bulur)"}},
    ["marka"],
)

TAKIP_LISTELE = _arac(
    "takip_listele",
    "Takiplistekileri sayar. Doner: adet, takipler (marka, site, baslangic). "
    "Ag cagrisi yok.",
    {},
    [],
)

TAKIP_DURDUR = _arac(
    "takip_durdur",
    "Takibi durdurur ve kaydi siler. Doner: marka, durum. Bulunamazsa hata.",
    {"marka": {"type": "string", "description": "Marka adi"}},
    ["marka"],
)

TAKIP_KONTROL = _arac(
    "takip_kontrol",
    "Takipteki firmanin kartini yeniden uretir ve alan bazinda degisimi "
    "yazar. Doner: marka, degisen, degismeyen, kart. Kaynak siniri acik veri.",
    {"marka": {"type": "string", "description": "Marka adi"}},
    ["marka"],
)

SIRKET_ARA = _arac(
    "sirket_ara",
    "Markanın resmi sitesini ve iletişim/vergi bilgilerini arar; "
    "JSON doner: marka, site, unvan, telefonlar, eposta, adresler, "
    "vergi_no, kaynak, dogrulandi, eksik. Bilgiler once sayfanin "
    "schema.org Organization/PostalAddress verisinden, eksik kalanlar "
    "duz metinden okunur; bulunamayan alan eksik listesinde yazar ve "
    "uydurma yok. Okunan sayfa markaya ait dogrulanamazsa `dogrulandi` "
    "false olur, alanlar bos kalir ve `not` sebebini yazar. "
    "Salt-okunur: disk yazimi yok.",
    {"marka": {"type": "string", "description": "Marka adı (örn. Tutku)"}},
    ["marka"],
)

FREETOOLS_ARA = _arac(
    "freetools_ara",
    "freetools.org arac katalogunu arar; eslesen araclarin adini, "
    "kategorisini ve tam adresini doner (en fazla 20 sonuc). Katalog "
    "yereldir; ag baglantisi gerekmez. Sorgu bossa kategorileri ve toplam "
    "arac sayisini doner.",
    {"sorgu": {"type": "string", "description": "Arac adi/anahtar kelime"},
     "kategori": {"type": "string",
                  "description": "Kategori filtresi (orn. text-tools); "
                                 "bossa tumu"},
     "adet": {"type": "integer",
              "description": "Sonuc sayisi (1-20, bossa 8)"}},
    ["sorgu"],
)

FREETOOLS_CALISTIR = _arac(
    "freetools_calistir",
    "freetools.org adresindeki araci calistirir ve sonucu metin olarak "
    "doner. Yalniz *.freetools.org adresleri; beyaz liste disi site "
    "calistirilmaz. Ayni girdi icin onbellek kullanir; gunluk istek "
    "siniri vardir; kopru/yerel hesap calismazsa hata doner ve diger "
    "araclari etkilemez. Sunucuda tarayici yokken ayni islemi standart "
    "algoritmayla yerelde hesaplar ve bu durumu acikca yazar. Donen "
    "sonucta [Arac sayfasi: <adres>] satiri olur; kullaniciya o adresi "
    "ver ki araci yeni sekmede kendisi de acabilsin. form bos "
    "birakilirsa sonuc uydurmaz, 'Girdi eksik' hatasi doner.",
    {"adres": {"type": "string",
               "description": "Arac sayfasi adresi (freetools_ara doner)"},
     "form": {"type": "array",
              "items": {"type": "string"},
              "description": "Sirayla doldurulacak giris degerleri "
                             "(en fazla 8); ilk deger aracin girdisidir"}},
    ["adres", "form"],
)

SAYFA_BAKIS = _arac(
    "sayfa_bakis",
    "Kullanicinin acik sekmesindeki sayfayi okur. Doner: sayfa (url, "
    "baslik, nesil), ogeler (ref, rol, ad, deger, kapali, secenekler) ve sayfalama "
    "(toplam, baslangic, donen, sonraki_baslangic). sayfalama."
    "sonraki_baslangic varsa ayni arac o degerle surdurulur; oge sayisinda "
    "tavan yoktur. Bagli tarayici istemcisi yoksa hata doner ve hata "
    "eklentinin kurulum adresini tasir. secenekler yalniz acilir listede "
    "bulunur: {deger, etiket, kapali} listesi, en cok 20 secenek. "
    "ogeler cerceve kimligi de tasir (0 = ana sayfa, digerleri iframe): "
    "ref cerceveyi tasidigi icin eylem dogru cerceveye gider. "
    "Sayfada tiklama ve yazma yapmaz.",
    {"baslangic": {"type": "integer",
                    "description": "Oge sirasi (bossa 0)"},
     "adet": {"type": "integer",
              "description": "Sayfa basina oge sayisi (1-200, bossa 60)"}},
    [],
)

SAYFA_TIKLA = _arac(
    "sayfa_tikla",
    "Acik sekmede, sayfa_bakis'in dondurdugu ref'teki ogeye tiklar. "
    "Ref sayfanin o anki gozlemine baglidir; sayfa degistiyse ya da oge "
    " artik yoksa hata doner. Gorunmeyen ve kapali (disabled) ogeye "
    "tiklanmaz. Eylem kullanicinin onayindan gecer: eklenti panelde "
    "sorar, onay gelmezse uygulanmaz. Doner: yapildi, sira, rol, ad, url, "
    "baslik, degisti (tiklamadan sonra sayfa degisti mi), bekleme_nedeni "
    "(adres | dom | bekleme), hazir (document.readyState). Tiklamadan "
    "sonra en cok 1,2 sn bekler; sayfayi yeniden okumaz.",
    {"ref": {"type": "string",
             "description": "sayfa_bakis'in verdigi oge referansi"}},
    ["ref"],
)

SAYFA_YAZ = _arac(
    "sayfa_yaz",
    "Acik sekmede, sayfa_bakis'in dondurdugu ref'teki alana metin yazar "
    "(input, textarea, select, contenteditable). Yazarken alanin "
    "input/change olaylari tetiklenir; cerev dokusu (React/Vue) degeri "
    "gorur. Eylem kullanicinin onayindan gecer: eklenti panelde sorar, "
    "onay gelmezse uygulanmaz. Sifre ve dosya secimi alanina YAZMAZ. "
    "select alaninda metin once secenek DEGERI, sonra secenek ETIKETI ile "
    "birebir aranir (harf duyarli); eslesme yoksa hata doner ve mevcut "
    "secenekler hata metninde listelenir. Yazma sonrasi alanin okudugu "
    "DEGER karsilastirilir; sayfa degeri tutmadiysa basari donmez. Doner: "
    "yapildi, sira, rol, ad, uzunluk, dogrulandi, secili (select ise secilen "
    "etiket), url. Yazdiktan sonra sayfayi kendisi yeniden okumaz.",
    {"ref": {"type": "string",
             "description": "sayfa_bakis'in verdigi alan referansi"},
     "metin": {"type": "string",
               "description": "Alana yazilacak metin"}},
    ["ref", "metin"],
)

SAYFA_TUS = _arac(
    "sayfa_tus",
    "Acik sekmede klavye tusu gonderir. Enter: ogenin formu GERCEKTEN "
    "gonderilir (eylem kullanicinin onayindan gecer). Tab: odak bir sonraki "
    "odaklanabilir ogeye tasinir. Escape, oklar ve bosluk yalniz keydown+keyup "
    "olayi olarak gonderilir; sayfanin kendi dinleyicisi ne yaparsa o olur. "
    "Doner: yapildi, tus, sira, rol, ad, gonderildi (form gonderildi mi), "
    "odak (Tab sonrasi odaklanan ogenin adi), engellendi (sayfa keydown'u "
    "durdurdu mu), url.",
    {"ref": {"type": "string",
             "description": "sayfa_bakis'in verdigi oge referansi"},
     "tus": {"type": "string",
             "description": "enter, tab, escape, bosluk, yukari, asagi, sola, saga"}},
    ["ref", "tus"],
)

SAYFA_KAYDIR = _arac(
    "sayfa_kaydir",
    "Acik sekmede sayfayi kaydirir. ref verilirse oge gorunur alana "
    "getirilir; ref verilmezse sayfa miktar kadar kaydirilir (bossa 600 px). "
    "Sayfa verisini degistirmez ve onay istemez. Doner: yapildi, sira, ad, "
    "konum (scrollY), yukseklik (scrollHeight), son (sayfa sonunda mi), url.",
    {"ref": {"type": "string",
             "description": "sayfa_bakis'in verdigi oge referansi (istege bagli)"},
     "miktar": {"type": "integer",
                "description": "Kaydirma miktari (px; bossa 600)"}},
    [],
)

TOOLS = [WEB_ARAMA, HABER_ARA, ZAMANLI_ARA, SITE_ARA, GORSEL_ARA,
          KITAP_ARA, DERIN_OKU, SAYFA_OKU, DOSYA_OKU, KLASOR_LISTELE, GIT_DURUM,
         BELGE_ARA, DOSYA_BILGI, GORUNTU_OKU, DOSYA_YAZ,
         HATIRLATMA_OZET, GOREV_EKLE, GOREV_LISTELE, GOREV_BITIR, GOREV_GUNCELLE,
         UYGULAMA_AC, ICERIK_ARA, GITHUB_DURUM,
         GIT_GECMIS, GIT_DEGISENLER, ADRES_KONTROL, TEST_KOS,
         MATRIS_AC, MATRIS_LISTE, SATIR_EKLE, KANIT_EKLE,
         SATIR_KAPAT, SATIR_AC, SATIR_SIL, SATIR_TASI,
         MATRIS_DURUM, GORSEL_URET, SAGLIK_RAPORU, SATIR_DUZENLE,
          SIMDI, HESAPLA, HAFIZA_ARA, SIRKET_ARA, HAVA_DURUMU, HARITA_GOSTER,
         KONUM_COZ, SUBE_BUL, HARITA_DEDEKTIF, POI_ARA, MESAFE_HESAPLA,
         ROTA_HESAPLA, BOLGE_KAYDET, GOREV_DEVRET, TAKIP_BASLAT,
         TAKIP_LISTELE, TAKIP_DURDUR, TAKIP_KONTROL,
         FATURA_OKU, KATALOG_KUR, KATALOG_GETIR, KATALOG_LISTELE,
         KATALOG_FIYAT, KATALOG_ONAYLA, YETKI_BELGESI, URUN_ESLESTIR,
         YAYIN_PAKETI, CIKTI_OKU,
         FREETOOLS_ARA, FREETOOLS_CALISTIR,
         SAYFA_BAKIS, SAYFA_TIKLA, SAYFA_YAZ, SAYFA_TUS, SAYFA_KAYDIR]

# Beyaz liste: model bu adlarin disinda bir arac uydurursa CALISMAZ.
# Yetkiyi kod verir, model kendine yetki yazamaz.
TANINMIS_TOOLLAR = frozenset(t["function"]["name"] for t in TOOLS)
