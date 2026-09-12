"""tools/definitions.py — Tool JSON schema tanımları.

Bağlam diyeti ADIM 2 (2026-08-23): açıklamalar sıkılaştırıldı — isim ve
parametre yapısı AYNEN korundu, yalnız açıklama metinleri kısaltıldı
(8.384 → ~2.900 karakter). Tetikleyici ipuçları korundu.
"""

# CORE TOOLS: modelin her zaman gorebildigi temel araclar
# 2026-08-26 v2: 8'den 5'e dusuruldu — log'da calistigi kanitlanmis
CORE_TOOL_NAMES = {
    "web_search",       # internette arama — KANITLANMIS
    "add_task",         # gorev ekle — basit (sadece text)
    "list_tasks",       # gorevleri listele — KANITLANMIS
    "list_files",       # klasor listele — KANITLANMIS
    "save_note",        # not kaydet — basit (title+content)
}

# KUCUK/UCRETSIZ MODELLER ICIN DAHA DAR CORE: yalniz en kanitlanmis,
# en basit 4 arac. 3b sinifi icin sema yukunu dusurur (B-EYLEM/BAĞLAM
# DIYETI). gate_modu=otomatik ve guclu saglayici yoksa kullanilir.
SMALL_CORE_TOOL_NAMES = {
    "web_search",       # internette arama
    "add_task",         # gorev ekle — basit (sadece text)
    "list_files",       # klasor listele — KANITLANMIS
    "read_file",        # dosya oku — KANITLANMIS
}

# EXTENDED TOOL TETIKLEYICILERI
# Anahtar kelime gecerse ilgili arac da sete eklenir.
EXTENDED_TETIKLERI = {
    "complete_task": [
        "bitirdim", "tamamladim", "bitti", "yaptim",
        "gorevi tamamla", "gorevi bitir",
    ],
    "read_file": [
        "dosyayi oku", "dosya icerigi", "dosyanin icinde ne var",
        "bu dosyayi ac", "oku", "icini ac", "icinde ne yaziyor",
        "bana oku", "goster su dosyayi",
    ],
    "get_reminders": [
        "hatirlatma", "hatirlat", "bugun ne yapacagim",
        "ajandam", "programim", "planim", "yarin ne var",
        "bugun neler var", "gunum nasil",
    ],
    "git_durum": [
        "vixrex", "numeramatch", "xses",
        "durumu ne", "durum ne", "son commit",
        "branch", "dal", "commit", "diff",
        "kod durumu", "guncel mi",
    ],
    "belge_ara": [
        "planda ne", "belgede ne", "listede ne yaziyor",
        "dokumanda", "gorev listesinde", "notlarda",
        "defterde ne", "bilgi notu", "rehberde",
    ],
    "dosya_bilgi": [
        "dosya boyutu", "dosya tarihi", "dosya bilgisi",
        "kac kb", "kac mb", "ne zaman degisti",
    ],
    "sayfa_oku": [
        "sayfayi oku", "url oku", "sayfa icerigi",
        "siteyi oku", "linkte ne yaziyor", "bu sayfada ne var",
    ],
    "write_file_tool": [
        "dosyaya yaz", "dosya olustur", "yeni dosya",
        "kaydet dosyaya", "dosyayi guncelle",
    ],
    "ac_uygulama": [
        "ac", "baslat", "calistir",
        "tarayici ac", "vscode ac", "notepad ac",
    ],
    "image_analyze": [
        "goruntu", "resim", "foto", "png", "jpg",
        "ekran goruntusu", "screenshot", "gorsel",
    ],
    "video_analyze": [
        "video", "ses dosyasi", "transkript",
        "ses kaydi", "konusma", "podcast",
    ],
    "model_stats": [
        "model istatistik", "performans", "kullanim",
        "token", "hiz testi",
    ],
    "deftere_kaydet": [
        "deftere yaz", "ortak deftere", "kayit ekle",
        "deftere kaydet", "bunu bir kenara yaz", "unutma diye yaz",
    ],
    "is_ac": [
        "is ac", "plan yap", "adim adim", "zamana yay",
        "periyodik is", "duzenli bakim",
    ],
    "is_liste": [
        "islerim", "is durumu", "is kuyrugu", "acan isler",
        "bekleyen isler",
    ],
    "is_onayla": [
        "isi onayla", "onu onayla", "devam et",
    ],
    "is_notu": [
        "plana yaz", "işe yaz", "ise yaz", "iş dosyasına",
        "bulguyu kaydet", "sonraki adım",
    ],
}



TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "sayfa_oku",
            "description": ("Bir web sayfasinin icerigini oku "
                            "(GET, HTML temizlenir, max 5000 karakter)."),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {"type": "string", "description": "Okunacak URL"}
                },
                "required": ["url"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": ("Internette guncel bilgi ara (hava, fiyat, "
                            "haber). Sohbet/gorev icin kullanma."),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "Arama sorgusu"}
                },
                "required": ["query"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "add_task",
            "description": ("Yeni gorev ekle ('yarin odevimi bitir', "
                            "'sut al' gibi yapilacak isler)."),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Gorev aciklamasi"}
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": "Mevcut gorevleri listele ('gorevlerim ne').",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_task",
            "description": ("Gorevi tamamlandi isaretle ('bitirdim/"
                            "tamamladim' denince)."),
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Gorev no"}
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_note",
            "description": ("Onemli bilgiyi not kaydet ('hatirla' denince). "
                            "Kisisel tanitim kaydetme."),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Baslik"},
                    "content": {"type": "string", "description": "Icerik"},
                },
                "required": ["title", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "deftere_kaydet",
            "description": ("Ortak deftere kayit yaz (ORTAK-DEFTER bicimi: "
                            "kim/tip/omur/kaynak). 'deftere yaz' denince."),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Konu"},
                    "content": {"type": "string", "description": "Icerik"},
                    "kim": {"type": "string", "description": "Yazan", "enum": ["basak", "claude", "casper", "kilo", "opencode", "freebuff"]},
                    "tip": {"type": "string", "description": "Tip", "enum": ["olcum", "alinti", "cikarim", "karar", "soru"]},
                    "omur": {"type": "string", "description": "Omur", "enum": ["1s", "6s", "1g", "30g", "sonsuz"]},
                    "kaynak": {"type": "string", "description": "Kaynak"},
                },
                "required": ["title", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": ("Dosya icerigini oku. Kullanici dosya yolu verdiyse "
                            "onu KULLAN — 'knowledge/' yazma. Mutlak yol "
                            "(C:\\Users\\... veya /home/...) dogrudan gider. "
                            "Kullanici yol belirtmezse knowledge/ kullan."),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Dosya yolu (kullanici verdiyse mutlak yol)"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file_tool",
            "description": "Dosyaya yaz/olustur (yalniz knowledge/ alti).",
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Dosya yolu"},
                    "content": {"type": "string", "description": "Icerik"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": ("Klasordeki dosyalari listele. Kullanici klasor "
                            "yolu verdiyse onu KULLAN — 'knowledge/' yazma. "
                            "Mutlak yol dogrudan gider. Kullanici klasor "
                            "belirtmezse knowledge/ kullan."),
            "parameters": {
                "type": "object",
                "properties": {
                    "folder": {"type": "string", "description": "Klasor yolu (kullanici verdiyse mutlak yol)"}
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ac_uygulama",
            "description": ("Beyaz listedeki uygulamayi ac (tarayici, "
                            "notepad, calculator, vscode...)."),
            "parameters": {
                "type": "object",
                "properties": {
                    "uygulama": {"type": "string", "description": "Uygulama adi"},
                    "parametre": {"type": "string", "description": "Parametre"},
                },
                "required": ["uygulama"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_reminders",
            "description": "Bugunku hatirlatmalar ve gorevleri ozetle.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "video_analyze",
            "description": ("Video/ses dosyasini analiz et: transkript, "
                            "konusmaci, zaman damgasi."),
            "parameters": {
                "type": "object",
                "properties": {
                    "video_yolu": {"type": "string",
                                   "description": "Dosyanin mutlak yolu"}
                },
                "required": ["video_yolu"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "image_analyze",
            "description": ("Goruntuyu analiz et (icerik, metin, nesne). "
                            "jpg/png/webp/gif."),
            "parameters": {
                "type": "object",
                "properties": {
                    "goruntu_yolu": {"type": "string",
                                     "description": "Goruntunun mutlak yolu"},
                    "soru": {"type": "string",
                             "description": "Ozel soru (opsiyonel)"},
                },
                "required": ["goruntu_yolu"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "model_stats",
            "description": ("Model performans istatistikleri (hiz, basari, "
                            "hatalar)."),
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {"type": "string", "description": "Model adi"},
                    "son_saat": {"type": "integer",
                                 "description": "Son kac saat (varsayilan 24)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "git_durum",
            "description": ("Projenin guncel durumunu olc: dal, son commit, "
                            "degisiklikler. Cevaptan ONCE kullan."),
            "parameters": {
                "type": "object",
                "properties": {
                    "proje": {"type": "string",
                              "description": "basak | vixrex | numeramatch | xses"}
                },
                "required": ["proje"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "belge_ara",
            "description": ("Proje .md belgelerinde kelime arar; buldugunu "
                            "[O] alintisi olarak aynen tasi."),
            "parameters": {
                "type": "object",
                "properties": {
                    "proje": {"type": "string",
                              "description": "basak | vixrex | numeramatch | xses"},
                    "sorgu": {"type": "string", "description": "Aranacak kelime"},
                },
                "required": ["proje", "sorgu"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dosya_bilgi",
            "description": ("Tek dosyanin varlik/boyut/son degisim zamanini "
                            "olcer."),
            "parameters": {
                "type": "object",
                "properties": {
                    "proje": {"type": "string",
                              "description": "basak | vixrex | numeramatch | xses"},
                    "yol": {"type": "string", "description": "Proje ici yol"},
                },
                "required": ["proje", "yol"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "is_ac",
            "description": ("Kalıcı iş aç (kapanınca kaybolmaz). Adımlar: "
                            "gorev_hatirlat, proje_yokla, gunluk_ozet."),
            "parameters": {
                "type": "object",
                "properties": {
                    "baslik": {"type": "string", "description": "İş başlığı"},
                    "adimlar": {"type": "string",
                                "description": "Virgüllü adım adları"},
                },
                "required": ["baslik", "adimlar"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "is_liste",
            "description": "Kuyruktaki işlerin kısa özeti.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "is_onayla",
            "description": "Onay bekleyen işi onaylar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "is_id": {"type": "string", "description": "İş no (is-000001)"}
                },
                "required": ["is_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "is_notu",
            "description": ("Aktif iş dosyasına not düşer (plan/bulgu/sonraki/"
                            "karar). HEDEF yazılamaz."),
            "parameters": {
                "type": "object",
                "properties": {
                    "is_id": {"type": "string", "description": "İş no (8 harf)"},
                    "bolum": {"type": "string", "description": "plan, bulgu, sonraki ya da karar"},
                    "metin": {"type": "string", "description": "Not metni"},
                },
                "required": ["is_id", "bolum", "metin"],
            },
        },
    },
]
