"""Basak gercek capability registry metadata'si.

53 gercek arac icin tek runtime kaynak tools.definitions.TOOLS'tur.
Bu namespace'ler arac SECMEZ; kullanici metnini SINIFLANDIRMAZ ve runtime
capability yuzeyini DARALTAMAZ. Yalniz test/kabul/dokumantasyon ve gelecekte
provider-native deferred/tool-search metadata'si icindir.
"""

from tools.definitions import TOOLS

CAPABILITY_NAMESPACES = {
    "internet": (
        "web_search", "haber_ara", "zamanli_ara", "site_ara",
        "gorsel_ara", "kitap_ara", "derin_oku", "sayfa_oku",
        "adres_kontrol", "sirket_ara", "hava_durumu",
    ),
    "dosyalar": (
        "read_file", "list_files", "belge_ara", "dosya_bilgi",
        "icerik_ara", "write_file_tool",
    ),
    "projeler": (
        "git_durum", "github_durum", "git_gecmis", "git_degisenler",
        "testleri_kos", "saglik_raporu",
    ),
    "gorevler": (
        "get_reminders", "add_task", "list_tasks", "complete_task", "simdi",
    ),
    "hafiza": ("hafiza_ara",),
    "gorsel": ("image_analyze", "gorsel_uret"),
    "katalog": (
        "fatura_oku", "katalog_kur", "katalog_getir", "katalog_liste",
        "katalog_fiyat_guncelle", "katalog_onayla", "yetki_belgesi_ekle",
        "urun_eslestir", "yayin_paketi", "cikti_oku",
    ),
    "matris": (
        "matris_ac", "matris_liste", "satir_ekle", "kanit_ekle",
        "satir_kapat", "satir_ac", "satir_sil", "satir_tasi",
        "matris_durum", "satir_duzenle",
    ),
    "masaustu": ("ac_uygulama",),
    "hesap": ("hesapla",),
}


def tool_names(tools=None):
    return tuple(
        (t.get("function") or {}).get("name")
        for t in (TOOLS if tools is None else tools)
        if isinstance(t, dict) and (t.get("function") or {}).get("name")
    )


def validate_registry(tools=None):
    names = tool_names(tools)
    flat = [name for group in CAPABILITY_NAMESPACES.values() for name in group]
    missing = sorted(set(names) - set(flat))
    unknown = sorted(set(flat) - set(names))
    duplicates = sorted({x for x in flat if flat.count(x) > 1})
    return {
        "ok": not missing and not unknown and not duplicates
              and len(flat) == len(names),
        "tool_count": len(names),
        "namespace_count": len(CAPABILITY_NAMESPACES),
        "missing": missing,
        "unknown": unknown,
        "duplicates": duplicates,
    }


def namespace_schemas(namespace, tools=None):
    """Kabul/native discovery gorunumu; runtime gating DEGIL."""
    allowed = set(CAPABILITY_NAMESPACES.get(str(namespace or ""), ()))
    katalog = TOOLS if tools is None else tools
    return [
        t for t in katalog
        if (t.get("function") or {}).get("name") in allowed
    ]
