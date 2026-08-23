"""tools/definitions.py — Tool JSON schema tanımları."""

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "sayfa_oku",
            "description": (
                "E-2: Bir web sayfasinin icerigini oku (yalnizca GET). "
                "HTML etiketleri soyulur, duz metin olarak doner. "
                "Arastrirma icin bir sayfanin tam icerigini gormek istediginde kullan. "
                "Max 5000 karakter."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "url": {
                        "type": "string",
                        "description": "Okunacak URL (http:// veya https://)"
                    }
                },
                "required": ["url"],
            },
        },
    },
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
            "name": "deftere_kaydet",
            "description": (
                "OD-1: Ortak deftere kayit ekle (ORTAK-DEFTER.md biciimi). "
                "Kayit bicimi: kim/tarih/tip/omur/kaynak on bilgisi + icerik. "
                "Basak'a bir sey soylendiginde veya onemli bir bilgi dogrulandiginda "
                "deftere yaz. 'Bunu deftere yaz', 'not al' dediginde kullan. "
                "Parametreler: kim (basak|claude|casper), tip (olcum|alinti|cikarim|karar|soru), "
                "omur (1s|6s|1g|30g|sonsuz), kaynak (kaynak aciklamasi)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "title": {"type": "string", "description": "Kayit konusu (dosya adina donusturulur)"},
                    "content": {"type": "string", "description": "Kayit icerigi (tek paragraf)"},
                    "kim": {"type": "string", "description": "Yazan taraf: basak|claude|casper|kilo|opencode|freebuff", "enum": ["basak", "claude", "casper", "kilo", "opencode", "freebuff"]},
                    "tip": {"type": "string", "description": "Kayit tipi", "enum": ["olcum", "alinti", "cikarim", "karar", "soru"]},
                    "omur": {"type": "string", "description": "Bilgi omru", "enum": ["1s", "6s", "1g", "30g", "sonsuz"]},
                    "kaynak": {"type": "string", "description": "Bilgi kaynagi (olcum komutu, dosya adi, sohbet vb.)"},
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
    {
        "type": "function",
        "function": {
            "name": "git_durum",
            "description": (
                "Bir projenin GUNCEL durumunu olc: dal, son commit, "
                "commit edilmemis dosyalar. 'VixRex'te durum ne', "
                "'ne yapiyoruz', 'son is ne zaman' sorularinda CEVAPTAN "
                "ONCE kullan. Beyaz listeli projeler: basak, vixrex, "
                "numeramatch, xses. Salt-okunur olcumdur, bir sey degistirmez."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "proje": {"type": "string", "description": "Proje adi: basak | vixrex | numeramatch | xses"}
                },
                "required": ["proje"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "belge_ara",
            "description": (
                "Bir projenin kok klasorundeki .md belgelerde kelime arar; "
                "eslesen satirlari dosya:satir ile dondurur. 'Planda ne "
                "yaziyor', 'belgede X geciyor mu' sorularinda kullan. "
                "Buldugun satiri cevabinda [O] alintisi olarak AYNEN tasi."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "proje": {"type": "string", "description": "Proje adi: basak | vixrex | numeramatch | xses"},
                    "sorgu": {"type": "string", "description": "Aranacak kelime/cümle"},
                },
                "required": ["proje", "sorgu"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "dosya_bilgi",
            "description": (
                "Projedeki tek dosyanin var mi / boyut / son degisim zamani "
                "bilgisini olcer. 'X dosyası değişti mi', 'şu dosya duruyor mu' "
                "sorularinda kullan."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "proje": {"type": "string", "description": "Proje adi: basak | vixrex | numeramatch | xses"},
                    "yol": {"type": "string", "description": "Proje icinde dosya yolu"},
                },
                "required": ["proje", "yol"],
            },
        },
    },
]
