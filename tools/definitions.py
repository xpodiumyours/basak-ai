"""tools/definitions.py — Tool JSON schema tanımları."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "web_search",
            "description": (
                "İnternette bilgi ara. SADECE güncel bilgi gerektiğinde: "
                "hava durumu, fiyat, haber. Selamlaşma, görev, not için KULLANMA."
            ),
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
            "description": (
                "YENİ GÖREV EKLE. Kullanıcı bir şey YAPMASI gerektiğini söylediğinde "
                "kullan. 'Yarın odevimi bitir', 'Süt al', 'Alışverişe git' gibi. "
                "'Bitir' kelimesi görev TAMAMLAMAK için değil, YENİ GÖREV eklemek için. "
                "Örnek: 'Yarın odevimi bitir' = bu bir görev, yapacak bir şey."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "Görev açıklaması"}
                },
                "required": ["text"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_tasks",
            "description": (
                "Mevcut görevleri listele. 'Görevlerim', 'Ne yapacağım', "
                "'Yapacaklarım', 'Şimdi ne yapmam lazım' dediğinde kullan."
            ),
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "complete_task",
            "description": (
                "Bir GÖREVİ tamamlandı işaretle. Kullanıcı bir işi YAPTIĞINI "
                "söyleyince kullan: 'Bitirdim', 'Tamamladım', 'Yaptım'. "
                "Sadece mevcut görevlerden birini tamamlar."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "task_id": {"type": "integer", "description": "Tamamlanacak görev no"}
                },
                "required": ["task_id"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "save_note",
            "description": (
                "Önemli bilgiyi kaydet. 'Bunu hatırla', 'Not al' dediğinde kullan. "
                "Kişisel tanıtım (yaş, meslek) KAYDETME."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Not başlığı"},
                    "content": {"type": "string", "description": "Not içeriği"},
                },
                "required": ["title", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "read_file",
            "description": (
                "Bir dosyanın içeriğini oku. Sadece knowledge/ klasöründeki "
                "dosyaları okuyabilirsin. 'Dosyayı oku', 'İçeriğe bak' dediğinde kullan."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Dosya yolu (knowledge/ altı)"}
                },
                "required": ["path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "write_file_tool",
            "description": (
                "Bir dosyaya yaz. Sadece knowledge/ klasörüne yazabilirsin. "
                "Dosya yoksa oluşturur. 'Dosyayı güncelle', 'Yeni dosya oluştur' dediğinde kullan."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Dosya yolu (knowledge/ altı)"},
                    "content": {"type": "string", "description": "Yazılacak içerik"},
                },
                "required": ["path", "content"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "list_files",
            "description": (
                "Bir klasördeki dosyaları listele. Varsayılan olarak knowledge/ "
                "klasörünü listeler. 'Dosyaları göster', 'Klasörde ne var' dediğinde kullan."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "folder": {"type": "string", "description": "Klasör yolu (varsayılan: knowledge)"}
                },
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ac_uygulama",
            "description": (
                "Bilgisayarda bir uygulama aç. Sadece beyaz listedeki "
                "uygulamaları açabilirsin: tarayici, notepad, calculator, "
                "file_manager, vscode. 'Tarayıcıyı aç', 'Not defterini aç' dediğinde kullan."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "uygulama": {"type": "string", "description": "Uygulama adı"},
                    "parametre": {"type": "string", "description": "Parametre (örn: URL, dosya yolu)"},
                },
                "required": ["uygulama"],
            },
        },
    },

    {
        "type": "function",
        "function": {
            "name": "get_reminders",
            "description": "Bugunku hatirlatmalari goster. Tarih bazli onemli gunler, bugunku gorevler ve yaklasan gorevler hakkinda bilgi ver. Uygulama basladiginda veya kullanici hatirlatmalarim ne dediginde kullan.",
            "parameters": {"type": "object", "properties": {}},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "video_analyze",
            "description": (
                "Video dosyasini analiz et: konusmacilari tespit et, "
                "transkript uret, zaman damgalari goster. "
                "'Bu videoyu analiz et', 'Videodaki konusmacilari bul' "
                "dediginde kullan. "
                "Desteklenen formatlar: mp4, mkv, avi, mov, webm, wav, mp3."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "video_yolu": {
                        "type": "string",
                        "description": "Video dosyasinin mutlak yolu",
                    }
                },
                "required": ["video_yolu"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "image_analyze",
            "description": (
                "Bir goruntuyu analiz et: icerigi, metni, nesneleri, renkleri acikla. "
                "'Bu goruntuyu acikla', 'Fotoğrafta ne var', 'Ekran goruntusunu oku' "
                "dediginde kullan. jpg/png/webp/gif destekler."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "goruntu_yolu": {
                        "type": "string",
                        "description": "Goruntu dosyasinin mutlak yolu",
                    },
                    "soru": {
                        "type": "string",
                        "description": "Goruntu hakkinda ozel soru (opsiyonel)",
                    },
                },
                "required": ["goruntu_yolu"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "model_stats",
            "description": (
                "Model performans istatistiklerini goster. "
                "Hangi model daha hizli, hangisi daha basarili, "
                "son hatalar neler — ogren. "
                "'Model performansları nasıl', 'Hangi model daha hızlı' "
                "dediginde kullan."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "model": {
                        "type": "string",
                        "description": "Belirli bir modelin istatistigi (opsiyonel)",
                    },
                    "son_saat": {
                        "type": "integer",
                        "description": 'Son kac saat (varsayilan 24)',
                    },
                },
                "required": [],
            },
        },
    },
]
