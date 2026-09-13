"""tools/definitions.py — Modele sunulan araç şemaları.

Açıklamalar YALNIZ olguyu söyler: araç ne yapar, hangi parametreyi alır,
ne döndürür, sınırı nedir. Davranış koçluğu ("şunu kullanma", "şöyle
cevapla") buraya YAZILMAZ — o, aracın etrafına sarılmış bir kural
katmanıdır ve 2026-09-13'te bilerek söküldü. Hangi aracı seçeceğine
model karar verir.

Dokuz + dort arac: sekizi salt-okunur, biri knowledge/ alti yazma,
dordü hatirlatma/gorev (yerel JSON, ag yok).
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
    "Internette arama yapar. Doner: baslik ve kisa metinlerden olusan "
    "sonuc listesi.",
    {"query": {"type": "string", "description": "Arama sorgusu"}},
    ["query"],
)

SAYFA_OKU = _arac(
    "sayfa_oku",
    "Verilen web adresini acar ve sayfanin metnini doner. HTML "
    "temizlenir, en fazla 5000 karakter. Yalniz http/https ve 80/443 "
    "portu; ic ag adresleri reddedilir.",
    {"url": {"type": "string", "description": "Okunacak adres"}},
    ["url"],
)

DOSYA_OKU = _arac(
    "read_file",
    "Bir dosyanin icerigini doner. Erisim: Casper'in ev klasoru "
    "(Belgeler, Masaustu, Indirilenler) ve C:\\Projects altindaki "
    "projeler. Sir dosyalari (.env, .pem, .key, ayarlar.json) ve "
    "Windows sistem klasorleri reddedilir.",
    {"path": {"type": "string", "description": "Dosya yolu veya adi"}},
    ["path"],
)

KLASOR_LISTELE = _arac(
    "list_files",
    "Bir klasordeki dosya ve alt klasorleri doner: ad + boyut. Klasor "
    "kisa adla (masaustu, belgeler, indirilenler) veya tam yolla "
    "verilebilir.",
    {"folder": {"type": "string", "description": "Klasor adi veya yolu"}},
    ["folder"],
)

GIT_DURUM = _arac(
    "git_durum",
    "Bir yazilim projesinin o ANKI durumunu olcer. Doner: aktif dal "
    "adi, son commit (hash + tarih + mesaj), commit edilmemis dosya "
    "sayisi ve ilk 10 dosyanin adi.",
    {"proje": _PROJE},
    ["proje"],
)

BELGE_ARA = _arac(
    "belge_ara",
    "Bir projenin KOK klasorundeki .md belgelerinde metin arar; alt "
    "klasorlere bakmaz. Doner: eslesen dosya adlari ve satirlar.",
    {"proje": _PROJE,
     "sorgu": {"type": "string", "description": "Aranacak metin"}},
    ["proje", "sorgu"],
)

DOSYA_BILGI = _arac(
    "dosya_bilgi",
    "Bir proje icindeki dosya veya klasorun var olup olmadigini, "
    "boyutunu ve son degisim tarihini doner. Icerigi okumaz.",
    {"proje": _PROJE,
     "yol": {"type": "string",
             "description": "Proje kokune gore dosya veya klasor yolu"}},
    ["proje", "yol"],
)

GORUNTU_OKU = _arac(
    "image_analyze",
    "Bir goruntu veya ekran goruntusu dosyasini inceler. Doner: "
    "goruntude ne oldugunun yazili aciklamasi; soru verilirse o soruya "
    "odaklanir.",
    {"path": {"type": "string", "description": "Goruntu dosyasinin yolu"},
     "soru": {"type": "string",
              "description": "Goruntu hakkinda sorulacak sey"}},
    ["path"],
)

DOSYA_YAZ = _arac(
    "write_file_tool",
    "knowledge/ klasoru altina not dosyasi yazar. Doner: yazilan yol. "
    "Yalniz knowledge/ altina yazar; baska yol reddedilir.",
    {"path": {"type": "string",
              "description": "knowledge/ altinda dosya yolu"},
     "content": {"type": "string", "description": "Dosya icerigi"}},
    ["path", "content"],
)

HATIRLATMA_OZET = _arac(
    "get_reminders",
    "Bugunku hatirlatmalari ve gorev ozetini doner: tarihli notlar, "
    "bekleyen gorevler, karsilama metni.",
    {},
    [],
)

GOREV_EKLE = _arac(
    "add_task",
    "Gorev listesine yeni gorev ekler. Doner: eklenen gorev (no + metin).",
    {"text": {"type": "string", "description": "Gorev aciklamasi"}},
    ["text"],
)

GOREV_LISTELE = _arac(
    "list_tasks",
    "Gorev listesini doner: no, metin, durum, tarih.",
    {},
    [],
)

GOREV_BITIR = _arac(
    "complete_task",
    "Verilen nodaki gorevi tamamlandi isaretler. Doner: sonuc.",
    {"task_id": {"type": "integer", "description": "Gorev no"}},
    ["task_id"],
)

UYGULAMA_AC = _arac(
    "ac_uygulama",
    "Beyaz listedeki bir uygulamayi acar (tarayici, notepad, "
    "calculator, file_manager, vscode). Doner: sonuc. "
    "Liste disi uygulama reddedilir.",
    {"uygulama": {"type": "string", "description": "Uygulama adi"},
     "parametre": {"type": "string",
                   "description": "Adres veya dosya yolu"}},
    ["uygulama"],
)

ICERIK_ARA = _arac(
    "icerik_ara",
    "Bir projenin tum klasorlerinde metin arar. Doner: "
    "dosya:satir: icerik satirlari (en fazla 8). "
    "Sifre dosyalari acilmaz, anahtar desenleri maskelenir.",
    {"proje": _PROJE,
     "sorgu": {"type": "string", "description": "Aranacak metin"},
     "uzanti": {"type": "string",
                "description": "Dosya uzantisi süzgeci (orn. .py)"}},
    ["proje", "sorgu"],
)

GITHUB_DURUM = _arac(
    "github_durum",
    "GitHub'da PR ve CI durumunu okur (salt-okunur). Doner: "
    "isleme gore PR listesi, PR detayi veya son 5 calisma. "
    "Yazan komut yok.",
    {"islem": {"type": "string",
               "description": "pr_liste | pr_goruntule | calisma_liste"},
     "proje": _PROJE,
     "no": {"type": "integer",
            "description": "PR numarasi (pr_goruntule icin)"},
     "durum": {"type": "string",
               "description": "PR durumu: open, closed, merged, all"}},
    ["islem", "proje"],
)

GIT_GECMIS = _arac(
    "git_gecmis",
    "Bir projenin son commitlerini listeler. Doner: oneline satirlari "
    "(en fazla 30).",
    {"proje": _PROJE,
     "dosya": {"type": "string",
               "description": "Tek dosya süzgeci (proje kokune gore)"},
     "adet": {"type": "integer", "description": "Kac commit (en fazla 30)"}},
    ["proje"],
)

GIT_DEGISENLER = _arac(
    "git_degisenler",
    "Taban dal ile HEAD arasi degisen dosya ozetini doner "
    "(diff --stat).",
    {"proje": _PROJE,
     "taban": {"type": "string",
               "description": "Taban referans (orn. origin/master)"}},
    ["proje"],
)

ADRES_KONTROL = _arac(
    "adres_kontrol",
    "Bir web adresinin canli durumunu olcer. Doner: HTTP durum kodu, "
    "yanit suresi, son adres. Sayfa govdesi indirilmez. "
    "Ic ag adresleri reddedilir.",
    {"url": {"type": "string", "description": "Kontrol edilecek adres"}},
    ["url"],
)

TOOLS = [WEB_ARAMA, SAYFA_OKU, DOSYA_OKU, KLASOR_LISTELE, GIT_DURUM,
         BELGE_ARA, DOSYA_BILGI, GORUNTU_OKU, DOSYA_YAZ,
         HATIRLATMA_OZET, GOREV_EKLE, GOREV_LISTELE, GOREV_BITIR,
         UYGULAMA_AC, ICERIK_ARA, GITHUB_DURUM,
         GIT_GECMIS, GIT_DEGISENLER, ADRES_KONTROL]

# Beyaz liste: model bu adlarin disinda bir arac uydurursa CALISMAZ.
# Yetkiyi kod verir, model kendine yetki yazamaz.
TANINMIS_TOOLLAR = frozenset(t["function"]["name"] for t in TOOLS)
