"""tools/permissions.py — Tool Permission Layer (P3).

Her aracin izin etiketi. Model KENDI yetkisini veremez/artiramaz:
buradaki tablo kod olarak sabit, executor calistirmeden once bakar.

Etiket sozlugu:
- salt-okunur : hicbir seyi degistirmez
- yazma       : dosya/gorev/not olusturur veya degistirir
- internet    : disari istek gonderir
- sistem      : bilgisayarda uygulama/pencere acar
- hassas      : ayrica Casper onayi gerektiren isler (simdilik bos)
"""

ETIKETLER = {
    "web_search": ["internet"],
    "sayfa_oku": ["internet"],
    "add_task": ["yazma"],
    "list_tasks": ["salt-okunur"],
    "complete_task": ["yazma"],
    "save_note": ["yazma"],
    "deftere_kaydet": ["yazma"],
    "read_file": ["salt-okunur"],
    "write_file_tool": ["yazma"],
    "list_files": ["salt-okunur"],
    "ac_uygulama": ["sistem"],
    "get_reminders": ["salt-okunur"],
    "video_analyze": ["salt-okunur"],  # video okur, yazmaz
    "image_analyze": ["salt-okunur"],  # goruntu okur, yazmaz
    "model_stats": ["salt-okunur"],   # istatistik okur
    "git_durum": ["salt-okunur"],     # OLCU: sabit okuma komutlari, shell yok
    "belge_ara": ["salt-okunur"],     # OLCU: kok .md belgelerde arama
    "dosya_bilgi": ["salt-okunur"],   # OLCU: var/mtime/boyut olcumu
}

# Etiket -> calisma politikasi (2026-08-23: etiket artik BELGE degil,
# executor bunu ZORUNLU KILAR):
# - otomatik : gunluk kullanim, sorunsuz calisir
# - opt-in   : VARSAYILAN KAPALI — ayarlar.json'da ilgili anahtar aciksa calisir
# - onay     : her cagrıda kullanıcı onayı ister (simdilik hicbir aracta yok;
#              P4/P6 onay kuyusu fazi icin ayrilmis)
ETIKET_POLITIKASI = {
    "salt-okunur": "otomatik",
    "internet": "otomatik",
    "yazma": "otomatik",
    "sistem": "opt-in",
    "hassas": "onay",
}

# opt-in etiketleri hangi ayar anahtari acar?
_OPTIN_ANAHTARI = {"sistem": "sistem_araclari_acik"}

SETTINGS_YOLU = None  # testler monkeypatch eder; None ise kok dizinden okunur


def _ayar_oku(anahtar, varsayilan=False):
    """ayarlar.json'dan tek anahtar okur (BOM guvenli, D-2 kurali)."""
    import json
    import os
    yol = SETTINGS_YOLU or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "ayarlar.json")
    try:
        with open(yol, "r", encoding="utf-8-sig") as f:
            return bool(json.load(f).get(anahtar, varsayilan))
    except (OSError, ValueError):
        return varsayilan


def politika(tool_name):
    """Aracin en kisitlayici politikasini dondurur.

    Etiketsiz araç "yasak"tir; birden fazla etiketi olan aracin en sikisi
    kazanir (otomatik < opt-in < onay < yasak).
    """
    etiketlerim = ETIKETLER.get(tool_name)
    if not etiketlerim:
        return "yasak"
    sira = {"otomatik": 0, "opt-in": 1, "onay": 2, "yasak": 3}
    return max((ETIKET_POLITIKASI.get(e, "yasak") for e in etiketlerim),
               key=lambda p: sira.get(p, 3))


def izinli_mi(tool_name):
    """Etiketi tanimli arac True; tanimsiz arac ASLA calismaz."""
    return tool_name in ETIKETLER


def calistirilabilir_mi(tool_name):
    """Aracin BU AN gercekten kosup kosmayacagini soyler.

    Tabloda olmayan -> hayir. Politikasi opt-in olan (orn. sistem) ->
    yalnizca ayarlar.json'daki anahtari aciksa. Onay politikasi simdilik
    hayir der (onay kuyusu fazi kurulmadi).
    """
    p = politika(tool_name)
    if p == "otomatik":
        return True
    if p == "opt-in":
        anahtar = _OPTIN_ANAHTARI.get(
            next(e for e in ETIKETLER[tool_name]
                 if ETIKET_POLITIKASI.get(e) == "opt-in"), "")
        return bool(anahtar) and _ayar_oku(anahtar)
    return False
