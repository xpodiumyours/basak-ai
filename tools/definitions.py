"""tools/definitions.py — Modele sunulan araç şemaları.

2026-09-13: 21 araçlık yığın söküldü, Casper'in seçtikleri geri geldi.
Araçlar dar işlere ayrılır; yazma aracı yalnız knowledge/ altında çalışır.

Dokuz araç, beş iş:
  internet  → web_search, sayfa_oku
  bilgisayar→ read_file, list_files, git_durum
  belge     → belge_ara, dosya_bilgi
  yazma     → write_file_tool (yalnız knowledge/)
  görme     → image_analyze
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

DOSYA_YAZ = {
    "type": "function",
    "function": {
        "name": "write_file_tool",
        "description": ("Bir dosyayi yaz veya olustur. Yalnizca Basak "
                        "projesindeki knowledge/ klasoru altina yazabilir."),
        "parameters": {
            "type": "object",
            "properties": {
                "path": {"type": "string",
                         "description": "knowledge/ ile baslayan hedef dosya yolu"},
                "content": {"type": "string",
                            "description": "Dosyaya yazilacak icerik"},
            },
            "required": ["path", "content"],
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

TOOLS = [WEB_ARAMA, SAYFA_OKU, DOSYA_OKU, KLASOR_LISTELE, GIT_DURUM,
         BELGE_ARA, DOSYA_BILGI, DOSYA_YAZ, GORUNTU_OKU]

# Beyaz liste: model bu adlarin disinda bir arac uydurursa CALISMAZ.
# Yetkiyi kod verir, model kendine yetki yazamaz.
TANINMIS_TOOLLAR = frozenset(t["function"]["name"] for t in TOOLS)
