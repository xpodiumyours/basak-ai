"""chat — Sohbet ve tool calling paketi.

Strangler Fig gecis asamasinda: bu __init__.py eski _chat_legacy.py'deki
tum public sembolleri yeniden export eder. Mevcut `import chat` /
`from chat import mesaj_isle` gibi tum import'lar aynen calismaya devam eder.

Yeni moduller kademeli olarak buradan export edilecek:
  - chat.approval  → onay sistemi
  - chat.gate      → cikis kapilari + dil kontrolu
  - chat.context   → knowledge + hafiza + gecmis
  - chat.tools     → tool calling dongusu
  - chat.flow      → ana akis orkestrasyonu
"""

# ── Backward compatibility: eski chat.py'deki her seyi export et ──────

# mesaj_isle: chat.flow'dan al; her kullanıcı turu TaskProfile scope'una
# girer. Belirsiz görevler LEGACY kalır, yani mevcut davranış korunur.
from chat.flow import mesaj_isle_yeni as _mesaj_isle_yeni  # noqa: F401
from brain.harness import harness_scope


def mesaj_isle(text, *args, **kwargs):
    with harness_scope(text):
        return _mesaj_isle_yeni(text, *args, **kwargs)


# Prompt blokları: circular import önlemi için ayrı modülde
from chat.prompts import TOOL_YONLENDIRME, OLCU_YONLENDIRME  # noqa: F401

from _chat_legacy import (  # noqa: F401, F403
    # Onay sistemi
    onay_bekle,
    onay_ver,
    _onay_kuyrugu,
    _onay_kararlari,
    _onay_lock,
    # Gecmis
    _gecmis_pencere,
    # Hafiza
    _hafiza,
    _hafiza_lock,
    _hafiza_al,
    # Tool etiketleri
    TOOL_LABELS,
    _TOOL_KELIMELERI,
    _TOOL_KELIMELERI,
    # Dinamik araclar
    _dinamik_araclar,
    _dosya_islemi_sinyali,
    _tool_gerekli_mi,
    _OLCUM_TOOLLARI,
    _ARAC_AILESI,
    _EK_TETIKLER,
    _DOSYA_OKUMA,
    _YOL_DESENI,
    _DIS_PROJE_ADLARI,
    # Dil kontrolu
    _dil_kontrol,
    _ingilizce_sizinti_mi,
    _ING_KELIMELER,
    _TR_KELIMELER,
    # Knowledge
    _load_knowledge,
    _knowledge_cache,
    _knowledge_lock,
    KNOWLEDGE_EMBED_CHARS,
    # Sozlesme
    _SOZLESME_MODU,
    _yapi_kwargi,
    _kapidan_gecir,
    # Onem
    _onem_puanla,
    _ONEM_KELIMELERI,
    _ONEM_YAZMA_ARACLARI,
    # Ana akis (mesaj_isle artik chat.flow'dan gelir)
    mesaj_isle_orkestra,
    _tool_calling_multi,
    _tool_argumani_duzelt,
    _temizle,
    _temizle_history,
    _sonucu_donustur,
    _parse_args,
    _save_and_reply,
    # Raw tool call parser
    _ham_tool_call_ayir,
    # Legacy tools
    _ham_tool_call_ayir,
    _raw_tool_call_var_mi,
    _TANINMIS_TOOLLAR,
    _RAW_TOOL_CALL_RE,
    _RAW_ARG_RE,
    # Dosya yollari ve sabitler
    BASE,
    HISTORY_FILE,
    SETTINGS_FILE,
    KNOWLEDGE_DIR,
    OBSIDIAN_DIR,
    KNOWLEDGE_MAX_CHARS,
    GOREVLER_FILE,
    MAX_HISTORY,
    GECMIS_KILO_LIMITI,
    TUR_SINIRI,
    OTURUM_ID,
    # Yukle/kaydet
    yukle,
    kaydet,
    # J
    _j,
    # Init
    init_cache,
    # Golge mod
    golge_mod_aktif_mi,
    golge_kos,
    _benzerlik,
    # Orkestra
    orkestra_aktif_mi,
    juri_acik_mi,
    orkestra_bilesenleri,
    _JURI_MAX,
    # Hafiza
    _hafiza_hazirla,
    _gecmisi_aktar,
    _ilgili_anilar,
)
