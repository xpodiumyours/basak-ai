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
]
