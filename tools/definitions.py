"""tools/definitions.py — Modele sunulan araç şemaları.

2026-09-13: 21 araçlık yığın söküldü, Casper'in seçtikleri geri geldi.
Buradaki araçların HEPSİ salt-okunur. Yazma, uygulama açma, görev/not
yönetimi yok — onlar araçtan çok bakım işi doğuruyordu ve etraflarına
onay katmanı gerektiriyordu.

Altı araç, üç iş:
  internet  → web_search, sayfa_oku
  bilgisayar→ read_file, list_files, git_durum
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
         GORUNTU_OKU]

# Beyaz liste: model bu adlarin disinda bir arac uydurursa CALISMAZ.
# Yetkiyi kod verir, model kendine yetki yazamaz.
TANINMIS_TOOLLAR = frozenset(t["function"]["name"] for t in TOOLS)
