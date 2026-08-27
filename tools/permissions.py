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
    "ac_uygulama": ["yazma"],
    "get_reminders": ["salt-okunur"],
    "video_analyze": ["salt-okunur"],
    "image_analyze": ["salt-okunur"],
    "model_stats": ["salt-okunur"],
    "git_durum": ["salt-okunur"],
    "belge_ara": ["salt-okunur"],
    "dosya_bilgi": ["salt-okunur"],
    "terminal_exec": ["yazma"],
}

# Etiket -> calisma politikasi
# Fren sökümü (2026-08-27): sistem opt-in ve canary normal yoldan kaldırıldı.
# Kalan tek politika: otomatik (günlük ajan kullanımı) + onay (yıkıcı işlem).
# Yıkıcı terminal desenleri tools/terminal.py'de fail-closed engellenir.
ETIKET_POLITIKASI = {
    "salt-okunur": "otomatik",
    "internet": "otomatik",
    "yazma": "otomatik",
    "sistem": "otomatik",
    "hassas": "onay",
}

_OPTIN_ANAHTARI = {}

SETTINGS_YOLU = None  # testler monkeypatch eder; None ise kok dizinden okunur


def _ayar_deger(anahtar, varsayilan=None):
    """ayarlar.json'dan her tipte deger okur (BOM guvenli, D-2 kurali)."""
    import json
    import os
    yol = SETTINGS_YOLU or os.path.join(
        os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        "ayarlar.json")
    try:
        with open(yol, "r", encoding="utf-8-sig") as f:
            return json.load(f).get(anahtar, varsayilan)
    except (OSError, ValueError):
        return varsayilan


def _ayar_oku(anahtar, varsayilan=False):
    """ayarlar.json'dan tek anahtar okur (BOM guvenli, D-2 kurali)."""
    return bool(_ayar_deger(anahtar, varsayilan))


def calisma_modu():
    """Uyumluluk için korunuyor — canary normal yola müdahale etmez."""
    mod = str(_ayar_deger("calisma_modu", "normal") or "normal").lower()
    return mod if mod in ("normal", "canary") else "normal"


def _canary_yasakli_mi(etiketlerim):
    """Fren sökümü: canary normal ajan yolunu engellemez."""
    return False


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
    """Fren sökümü: tanımlı araç çalışır; yıkıcı terminal desenleri terminal.py'de engellenir."""
    etiketlerim = ETIKETLER.get(tool_name)
    if not etiketlerim:
        return False
    p = politika(tool_name)
    if p == "otomatik":
        return True
    if p == "opt-in":
        return True
    return False


def engel_sebebi(tool_name):
    etiketlerim = ETIKETLER.get(tool_name)
    if not etiketlerim:
        return "'%s' aracının izin etiketi yok." % tool_name
    p = politika(tool_name)
    if p == "yasak":
        return ("'%s' aracının izin etiketi yok." % tool_name)
    if p == "onay":
        return ("'%s' aracı kullanıcı onayı bekliyor." % tool_name)
    return None
