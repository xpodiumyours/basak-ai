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
    """'calisma_modu' ayarini dondurur: 'normal' | 'canary'.

    CANARY (2026-08-24, canli test hatti): gercek modellerle yapilan
    guvenlik denemelerinde yazma ve sistem araclarinin TAMAMI kapalidir
    — onay kuyusu olmadan 'yazma onayi' talebi yerine daha SIKI olan
    tam engel secildi (denetim raporu karari).
    """
    mod = str(_ayar_deger("calisma_modu", "normal") or "normal").lower()
    return mod if mod in ("normal", "canary") else "normal"


def _canary_yasakli_mi(etiketlerim):
    """Canary modunda bu etiket seti engellenir mi?"""
    if calisma_modu() != "canary":
        return False
    return bool({"yazma", "sistem"} & set(etiketlerim))


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
    hayir der (onay kuyusu fazi kurulmadi). CANARY modunda yazma ve
    sistem etiketli araclar kosulsuz kapalidir.
    """
    etiketlerim = ETIKETLER.get(tool_name)
    if not etiketlerim:
        return False
    p = politika(tool_name)
    if p == "otomatik":
        return not _canary_yasakli_mi(etiketlerim)
    if p == "opt-in":
        if _canary_yasakli_mi(etiketlerim):
            return False
        anahtar = _OPTIN_ANAHTARI.get(
            next(e for e in etiketlerim
                 if ETIKET_POLITIKASI.get(e) == "opt-in"), "")
        return bool(anahtar) and _ayar_oku(anahtar)
    return False


def engel_sebebi(tool_name):
    """Engellendigi takdirde KULLANICIYA gosterilecek nedeni dondurur;
    engel yoksa None. Mesajlar executor'in eskisiyle birebir aynidir."""
    etiketlerim = ETIKETLER.get(tool_name)
    if not etiketlerim:
        return "'%s' aracının izin etiketi yok." % tool_name
    if _canary_yasakli_mi(etiketlerim):
        tur = "yazma" if "yazma" in etiketlerim else "sistem"
        return ("'%s' aracı CANARY modunda kapalı — %s işlemleri canlı "
                "denemede devre dışı." % (tool_name, tur))
    p = politika(tool_name)
    if p == "yasak":
        return ("'%s' aracının izin etiketi yok." % tool_name)
    if p == "opt-in":
        return ("'%s' sistem aracı varsayılan kapalı. Casper "
                "ayarlar.json'da 'sistem_araclari_acik': true "
                "dediğinde açılır." % tool_name)
    if p == "onay":
        return ("'%s' aracı kullanıcı onayı bekliyor (onay kuyusu "
                "henüz kurulmadı)." % tool_name)
    return None
