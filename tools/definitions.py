"""tools/definitions.py — Modele sunulan araç şemaları.

Şemalar yalnız aracın ne yaptığını ve hangi parametreleri aldığını açıklar.
Kullanıcı cümlesi, sohbet türü veya niyet için kullanım kuralı içermez.
"""

WEB_ARAMA = {
    "type": "function",
    "function": {
        "name": "web_search",
        "description": "İnternette web araması yap.",
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
        "description": "Bir web sayfasının metin içeriğini oku.",
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
        "description": "Web adresinin HTTP durumunu, yanıt süresini ve son adresini ölç.",
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
        "description": "Yerel bir dosyanın içeriğini oku; hassas ve sistem dosyaları kapalıdır.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Dosya yolu veya adı"}
            },
            "required": ["path"],
        },
    },
}

KLASOR_LISTELE = {
    "type": "function",
    "function": {
        "name": "list_files",
        "description": "Yerel bir klasördeki dosya ve klasörleri listele.",
        "parameters": {
            "type": "object",
            "properties": {
                "folder": {"type": "string", "description": "Klasör yolu"}
            },
            "required": ["folder"],
        },
    },
}

DOSYA_YAZ = {
    "type": "function",
    "function": {
        "name": "write_file_tool",
        "description": "knowledge/ altına dosya kaydet.",
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
        "description": "Bugünkü ve yaklaşan hatırlatmaları getir.",
        "parameters": {"type": "object", "properties": {}},
    },
}

GOREV_EKLE = {
    "type": "function",
    "function": {
        "name": "add_task",
        "description": "Yeni görev ekle.",
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
        "description": "Bekleyen görevleri listele.",
        "parameters": {"type": "object", "properties": {}},
    },
}

GOREV_TAMAMLA = {
    "type": "function",
    "function": {
        "name": "complete_task",
        "description": "Görevi tamamlandı işaretle.",
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
        "description": "Tanımlı uygulamalardan birini aç.",
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
        "description": "Bir projenin dal, son commit ve commit edilmemiş dosyalarını ölç.",
        "parameters": {
            "type": "object",
            "properties": {
                "proje": {"type": "string", "description": "basak | vixrex | numeramatch | xses"}
            },
            "required": ["proje"],
        },
    },
}

GIT_GECMIS = {
    "type": "function",
    "function": {
        "name": "git_gecmis",
        "description": "Projenin son commitlerini veya bir dosyanın git geçmişini oku.",
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
        "description": "Taban ref ile HEAD arasındaki değişen dosya istatistiğini oku.",
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
        "description": "Bir projenin kökündeki Markdown belgelerinde satır ara.",
        "parameters": {
            "type": "object",
            "properties": {
                "proje": {"type": "string", "description": "basak | vixrex | numeramatch | xses"},
                "sorgu": {"type": "string", "description": "Belgelerde aranacak metin"},
            },
            "required": ["proje", "sorgu"],
        },
    },
}

ICERIK_ARA = {
    "type": "function",
    "function": {
        "name": "icerik_ara",
        "description": "Proje genelindeki metin dosyalarında kod veya ifade ara.",
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
        "description": "Bir proje içindeki dosya veya klasörün varlık, boyut ve son değişim bilgisini ölç.",
        "parameters": {
            "type": "object",
            "properties": {
                "proje": {"type": "string", "description": "basak | vixrex | numeramatch | xses"},
                "yol": {"type": "string", "description": "Proje köküne göre dosya veya klasör yolu"},
            },
            "required": ["proje", "yol"],
        },
    },
}

GITHUB_DURUM = {
    "type": "function",
    "function": {
        "name": "github_durum",
        "description": "GitHub PR listesi, PR detayı veya son CI koşumlarını oku.",
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
        "description": "Tanımlı projenin kodda sabit test komutunu çalıştır.",
        "parameters": {
            "type": "object",
            "properties": {
                "proje": {"type": "string", "description": "basak | vixrex | numeramatch | xses"}
            },
            "required": ["proje"],
        },
    },
}

GORUNTU_OKU = {
    "type": "function",
    "function": {
        "name": "image_analyze",
        "description": "Bir görüntü veya ekran görüntüsü dosyasını incele.",
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string", "description": "Görüntü dosyasının yolu"},
                "soru": {"type": "string", "description": "Görüntü hakkında sorulacak şey"},
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

TANINMIS_TOOLLAR = frozenset(t["function"]["name"] for t in TOOLS)
