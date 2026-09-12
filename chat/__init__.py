"""chat — sohbet ve tool-calling paketi.

Yeni akış chat.flow üzerinden çalışır; legacy semboller geriye uyumluluk için
korunur. Tam kapasite modunda eski orkestra/jüri/gölge katmanı ana yola
giremez, konuşma geçmişi 4000 karaktere kesilmez ve eski çelişkili kişilik
metni modele taşınmaz.
"""

import chat.flow as _flow_mod
from chat.flow import mesaj_isle_yeni as _orijinal_mesaj_isle
from chat.prompts import TOOL_YONLENDIRME, OLCU_YONLENDIRME  # noqa: F401

from _chat_legacy import (  # noqa: F401, F403
    onay_bekle, onay_ver, _onay_kuyrugu, _onay_kararlari, _onay_lock,
    _gecmis_pencere,
    _hafiza, _hafiza_lock, _hafiza_al,
    TOOL_LABELS, _TOOL_KELIMELERI,
    _dinamik_araclar, _dosya_islemi_sinyali, _tool_gerekli_mi,
    _OLCUM_TOOLLARI, _ARAC_AILESI, _EK_TETIKLER, _DOSYA_OKUMA,
    _YOL_DESENI, _DIS_PROJE_ADLARI,
    _dil_kontrol, _ingilizce_sizinti_mi, _ING_KELIMELER, _TR_KELIMELER,
    _load_knowledge, _knowledge_cache, _knowledge_lock,
    KNOWLEDGE_EMBED_CHARS,
    _SOZLESME_MODU, _yapi_kwargi, _kapidan_gecir,
    _onem_puanla, _ONEM_KELIMELERI, _ONEM_YAZMA_ARACLARI,
    mesaj_isle_orkestra,
    _tool_calling_multi, _tool_argumani_duzelt, _temizle,
    _temizle_history, _sonucu_donustur, _parse_args, _save_and_reply,
    _ham_tool_call_ayir, _raw_tool_call_var_mi, _TANINMIS_TOOLLAR,
    _RAW_TOOL_CALL_RE, _RAW_ARG_RE,
    BASE, HISTORY_FILE, SETTINGS_FILE, KNOWLEDGE_DIR, OBSIDIAN_DIR,
    DEFTER_DIR, KNOWLEDGE_MAX_CHARS, GOREVLER_FILE,
    MAX_HISTORY, GECMIS_KILO_LIMITI, TUR_SINIRI, OTURUM_ID,
    yukle, kaydet, _j, init_cache,
    golge_mod_aktif_mi, golge_kos, _benzerlik,
    orkestra_aktif_mi, juri_acik_mi, orkestra_bilesenleri, _JURI_MAX,
    _hafiza_hazirla, _gecmisi_aktar, _ilgili_anilar,
)

import _chat_legacy as _legacy

GECMIS_KILO_LIMITI = 60000
MAX_HISTORY = 40


def _tam_gecmis_pencere(gecmis, limit=GECMIS_KILO_LIMITI,
                        adet_siniri=MAX_HISTORY):
    """Son konuşmayı geniş pencereyle, mesajları bölmeden modele taşı."""
    secilen = []
    toplam = 0
    for m in reversed(gecmis or []):
        uzunluk = len(m.get("content") or "")
        if secilen and toplam + uzunluk > limit:
            break
        secilen.append(m)
        toplam += uzunluk
        if len(secilen) >= adet_siniri:
            break
    secilen.reverse()
    return secilen


_gecmis_pencere = _tam_gecmis_pencere
_legacy._gecmis_pencere = _tam_gecmis_pencere
_legacy.GECMIS_KILO_LIMITI = GECMIS_KILO_LIMITI
_legacy.MAX_HISTORY = MAX_HISTORY


def _kapali():
    return False


orkestra_aktif_mi = _kapali
golge_mod_aktif_mi = _kapali
juri_acik_mi = _kapali
_legacy.orkestra_aktif_mi = _kapali
_legacy.golge_mod_aktif_mi = _kapali
_legacy.juri_acik_mi = _kapali


# basak_app.py'deki eski KISILIK metni birbiriyle çelişen isim ve cevap
# kuralları içeriyor. Kimlik artık chat.prompts.KIMLIK_BLOGU'nda tek kaynak.
# Flow'un tüm çağrılarında eski metni yok say; dürüstlük ve kişisel hafıza
# flow içinde ayrı katmanlardan zaten ekleniyor.
def mesaj_isle(text, brain, system_prompt, js_callback, tools):
    return _orijinal_mesaj_isle(text, brain, "", js_callback, tools)


def _dogal_mesaj_isle_yeni(text, brain, system_prompt, js_callback, tools):
    return _orijinal_mesaj_isle(text, brain, "", js_callback, tools)


_flow_mod.mesaj_isle_yeni = _dogal_mesaj_isle_yeni
