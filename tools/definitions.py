"""tools/definitions.py — Modele sunulan araç şemaları.

2026-09-13: 21 araçlık yığın söküldü, Casper'in seçtikleri geri geldi.
Araç planındaki yeni yetenekler aynı sade şema listesine eklenir; gerçek
çalıştırma ve güvenlik sınırları tools/__init__.py ve ilgili modüllerdedir.
"""

WEB_ARAMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": ("Internette guncel bilgi ara: fiyat, haber, hava, "
                        "rakip, pazar. Sohbet icin kullanma."),
        "parameters": {
            "type": "object",
            "properties": {
                "query": {"type": "string", "description": "Arama sorgusu"}
            },
            "required": ["query"],
        },
    },
}

SAYFA_OKU = {
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
}

ADRES_KONTROL = {
    "type": "function",
    "function": {
        "name": "adres_kontrol",
        "description": "Canli web adresinin HTTP durumunu, yanit suresini ve son adresini olc.",
        "parameters": {
            "type": "object",
            "properties": {"url": {"type": "string"}},
            "required": ["url"],
        },
    },
}

DOSYA_OKU = {
    "type": "function",
    "function": {
        "name": "read_file",
        "description": ("Bir dosyanin icerigini oku. Casper'in ev klasoru "
                        "ve C:\\Projects okunabilir; sifre/sistem "
                        "dosyalari kapali."),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string",
                         "description": "Dosya yolu veya adi"}
            },
            "required": ["path"],
        },
    },
}

KLASOR_LISTELE = {
    "type": "function",
    "function": {
        "name": "list_files",
        "description": ("Bir klasordeki dosyalari listele (Belgeler, "
                        "Masaustu, Indirilenler, proje klasorleri)."),
        "parameters": {
            "type": "object",
            "properties": {
                "folder": {"type": "string",
                           "description": "Klasor adi veya yolu"}
            },
            "required": ["folder"],
        },
    },
}

DOSYA_YAZ = {
    "type": "function",
    "function": {
        "name": "write_file_tool",
        "description": "Yalniz knowledge/ altina dosya kaydet.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string"},
                "content": {"type": "string"},
            },
            "required": ["path", "content"],
        },
    },
}

HATIRLATMALAR = {
    "type": "function",
    "function": {
        "name": "get_reminders",
        "description": "Bugunku ve yaklasan hatirlatmalari getir.",
        "parameters": {"type": "object", "properties": {}},
    },
}

GOREV_EKLE = {
    "type": "function",
    "function": {
        "name": "add_task",
        "description": "Yeni gorev ekle.",
        "parameters": {
            "type": "object",
            "properties": {"text": {"type": "string"}},
            "required": ["text"],
        },
    },
}

GOREV_LISTELE = {
    "type": "function",
    "function": {
        "name": "list_tasks",
        "description": "Bekleyen gorevleri listele.",
        "parameters": {"type": "object", "properties": {}},
    },
}

GOREV_TAMAMLA = {
    "type": "function",
    "function": {
        "name": "complete_task",
        "description": "Gorevi tamamlandi isaretle.",
        "parameters": {
            "type": "object",
            "properties": {"task_id": {"type": "integer"}},
            "required": ["task_id"],
        },
    },
}

UYGULAMA_AC = {
    "type": "function",
    "function": {
        "name": "ac_uygulama",
        "description": "Beyaz listedeki uygulamayi ac.",
        "parameters": {
            "type": "object",
            "properties": {
                "uygulama": {"type": "string"},
                "parametre": {"type": "string"},
            },
            "required": ["uygulama"],
        },
    },
}

GIT_DURUM = {
    "type": "function",
    "function": {
        "name": "git_durum",
        "description": ("Bir projenin dal, son commit ve commit edilmemis "
                        "dosyalarini olcer. Projeler: basak, vixrex, "
                        "numeramatch, xses."),
        "parameters": {
            "type": "object",
            "properties": {
                "proje": {"type": "string",
                          "description": "basak | vixrex | numeramatch | xses"}
            },
            "required": ["proje"],
        },
    },
}

GIT_GECMIS = {
    "type": "function",
    "function": {
        "name": "git_gecmis",
        "description": "Projenin son commitlerini veya bir dosyanin git gecmisini oku.",
        "parameters": {
            "type": "object",
            "properties": {
                "proje": {"type": "string"},
                "dosya": {"type": "string"},
                "adet": {"type": "integer"},
            },
            "required": ["proje"],
        },
    },
}

GIT_DEGISENLER = {
    "type": "function",
    "function": {
        "name": "git_degisenler",
        "description": "Taban ref ile HEAD arasindaki degisen dosya istatistigini oku.",
        "parameters": {
            "type": "object",
            "properties": {
                "proje": {"type": "string"},
                "taban": {"type": "string"},
            },
            "required": ["proje"],
        },
    },
}

BELGE_ARA = {
    "type": "function",
    "function": {
        "name": "belge_ara",
        "description": ("Bir projenin kokundeki Markdown belgelerinde "
                        "satir ara. Projeler: basak, vixrex, numeramatch, xses."),
        "parameters": {
            "type": "object",
            "properties": {
                "proje": {"type": "string",
                          "description": "basak | vixrex | numeramatch | xses"},
                "sorgu": {"type": "string",
                          "description": "Belgelerde aranacak metin"},
            },
            "required": ["proje", "sorgu"],
        },
    },
}

ICERIK_ARA = {
    "type": "function",
    "function": {
        "name": "icerik_ara",
        "description": "Proje genelindeki metin dosyalarinda kod veya ifade ara.",
        "parameters": {
            "type": "object",
            "properties": {
                "proje": {"type": "string"},
                "sorgu": {"type": "string"},
                "uzanti": {"type": "string"},
            },
            "required": ["proje", "sorgu"],
        },
    },
}

DOSYA_BILGI = {
    "type": "function",
    "function": {
        "name": "dosya_bilgi",
        "description": ("Bir proje icindeki dosya veya klasorun varlik, "
                        "boyut ve son degisim bilgisini olcer."),
        "parameters": {
            "type": "object",
            "properties": {
                "proje": {"type": "string",
                          "description": "basak | vixrex | numeramatch | xses"},
                "yol": {"type": "string",
                        "description": "Proje kokune gore dosya veya klasor yolu"},
            },
            "required": ["proje", "yol"],
        },
    },
}

GITHUB_DURUM = {
    "type": "function",
    "function": {
        "name": "github_durum",
        "description": "GitHub PR listesi, PR detayi veya son CI kosumlarini oku.",
        "parameters": {
            "type": "object",
            "properties": {
                "proje": {"type": "string"},
                "islem": {"type": "string", "enum": ["pr_list", "pr_view", "run_list"]},
                "pr_numarasi": {"type": "integer"},
                "durum": {"type": "string", "enum": ["open", "closed", "all"]},
            },
            "required": ["proje", "islem"],
        },
    },
}

TESTLERI_KOS = {
    "type": "function",
    "function": {
        "name": "testleri_kos",
        "description": "Beyaz listedeki projenin kodda sabit test komutunu calistir.",
        "parameters": {
            "type": "object",
            "properties": {
                "proje": {"type": "string",
                          "description": "basak | vixrex | numeramatch | xses"}
            },
            "required": ["proje"],
        },
    },
}

GORUNTU_OKU = {
    "type": "function",
    "function": {
        "name": "image_analyze",
        "description": ("Bir goruntu/ekran goruntusu dosyasini incele ve "
                        "icindekini anlat."),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string",
                         "description": "Goruntu dosyasinin yolu"},
                "soru": {"type": "string",
                         "description": "Goruntu hakkinda sorulacak sey"},
            },
            "required": ["path"],
        },
    },
}

TOOLS = [
    WEB_ARAMA, SAYFA_OKU, ADRES_KONTROL, DOSYA_OKU, KLASOR_LISTELE,
    DOSYA_YAZ, HATIRLATMALAR, GOREV_EKLE, GOREV_LISTELE, GOREV_TAMAMLA,
    UYGULAMA_AC, GIT_DURUM, GIT_GECMIS, GIT_DEGISENLER, BELGE_ARA,
    ICERIK_ARA, DOSYA_BILGI, GITHUB_DURUM, TESTLERI_KOS, GORUNTU_OKU,
]

# Beyaz liste: model bu adlarin disinda bir arac uydurursa CALISMAZ.
# Yetkiyi kod verir, model kendine yetki yazamaz.
TANINMIS_TOOLLAR = frozenset(t["function"]["name"] for t in TOOLS)
