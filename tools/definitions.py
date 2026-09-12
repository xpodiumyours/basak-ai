"""tools/definitions.py — Modele sunulan araç şemaları.

2026-09-13: araç katmanı söküldükten sonra Casper'in istegiyle YALNIZ
internet araclari geri getirildi. Eski 21 araclik yigin geri gelmedi;
burada iki arac var ve ikisi de salt-okunur.

Neden bu ikisi: model interneti kendi goremez. "Guncel fiyat nedir",
"rakipler kim" gibi sorularda arac olmadan ya uydurur ya "yapamam" der.
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

TOOLS = [WEB_ARAMA, SAYFA_OKU]

# Beyaz liste: model bu ikisi disinda bir arac adi uydurursa CALISMAZ.
# Yetkiyi kod verir, model kendine yetki yazamaz.
TANINMIS_TOOLLAR = frozenset(t["function"]["name"] for t in TOOLS)
