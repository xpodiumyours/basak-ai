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
    "add_task": ["yazma"],
    "list_tasks": ["salt-okunur"],
    "complete_task": ["yazma"],
    "save_note": ["yazma"],
    "read_file": ["salt-okunur"],
    "write_file_tool": ["yazma"],
    "list_files": ["salt-okunur"],
    "ac_uygulama": ["sistem"],
    "get_reminders": ["salt-okunur"],
    "video_analyze": ["salt-okunur"],  # video okur, yazmaz
    "image_analyze": ["salt-okunur"],  # goruntu okur, yazmaz
    "model_stats": ["salt-okunur"],   # istatistik okur
}


def etiketler(tool_name):
    """Aracin etiketlerini dondurur; tanimsizsa None (calistirilamaz)."""
    return ETIKETLER.get(tool_name)


def izinli_mi(tool_name):
    """Etiketi tanimli arac True; tanimsiz arac ASLA calismaz."""
    return tool_name in ETIKETLER
