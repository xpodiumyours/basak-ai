"""tools/definitions.py — Tool JSON schema tanımları.

Bağlam diyeti ADIM 2 (2026-08-23): açıklamalar sıkılaştırıldı — isim ve
parametre yapısı AYNEN korundu, yalnız açıklama metinleri kısaltıldı
(8.384 → ~2.900 karakter). Tetikleyici ipuçları korundu.
"""

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
            "description": ("Dosya icerigini oku (knowledge/ ve beyaz "
                            "listeli projeler)."),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Dosya yolu"}
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
            "description": "Klasordeki dosyalari listele (varsayilan knowledge/).",
            "parameters": {
                "type": "object",
                "properties": {
                    "folder": {"type": "string", "description": "Klasor yolu"}
                },
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
            "name": "terminal_exec",
            "description": ("Workspace içinde terminal komutu çalıştır (read/write/git/python). "
                            "cwd workspace'e göre göreli; timeout 30s varsayılan."),
            "parameters": {
                "type": "object",
                "properties": {
                    "command": {"type": "string", "description": "Çalıştırılacak shell komutu"},
                    "cwd": {"type": "string", "description": "Çalışma dizini (göreli, varsayılan kök)"},
                    "timeout": {"type": "integer", "description": "Zaman aşımı saniye (max 120)"},
                },
                "required": ["command"],
            },
        },
    },
]
