"""chat/tools.py — Tool calling döngüsü modülü.

Modelin tool_calls yanıtlarını işler, araçları çalıştırır ve sonuçları
 modele geri göndererek doğal dil özeti üretir.

Bağımlılıklar: json, re, os (standart), tools.executor (proje içi)
DI Container: ToolConfig (tool_labels, taninmis_toollar)
"""

import json
import logging
import os
import re

logger = logging.getLogger(__name__)


# ── Tanınmış tool isimleri ──────────────────────────────────────────

TANINMIS_TOOLLAR = frozenset((
    "list_files", "read_file", "write_file_tool", "web_search",
    "sayfa_oku", "add_task", "list_tasks", "complete_task",
    "save_note", "deftere_kaydet", "ac_uygulama", "get_reminders",
    "video_analyze", "image_analyze", "model_stats",
    "git_durum", "belge_ara", "dosya_bilgi",
))

TOOL_LABELS = {
    "web_search": "Aranıyor...",
    "add_task": "Görev ekleniyor...",
    "list_tasks": "Görevler listeleniyor...",
    "complete_task": "Tamamlanıyor...",
    "save_note": "Kaydediliyor...",
    "git_durum": "Ölçülüyor (git)...",
    "belge_ara": "Belgeler taranıyor...",
    "dosya_bilgi": "Dosya ölçülüyor...",
}


# ── Raw tool call parser ────────────────────────────────────────────

_RAW_TOOL_CALL_RE = re.compile(
    r'\[?(\w+)\]?\s*\(\s*([^)]*)\s*\)',
)
_RAW_ARG_RE = re.compile(
    r'''(\w+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^,)]+))''',
)


def ham_tool_call_ayir(metin):
    """Ham metindeki raw tool call desenlerini yakalar.

    Dönüş: [(tool_name, {args}), ...]  — yakalama yoksa boş liste.
    """
    if not metin or not isinstance(metin, str):
        return []
    sonuclar = []
    for eslesme in _RAW_TOOL_CALL_RE.finditer(metin):
        ad = eslesme.group(1)
        if ad not in TANINMIS_TOOLLAR:
            continue
        ham_args = eslesme.group(2).strip()
        args = {}
        if ham_args:
            for ae in _RAW_ARG_RE.finditer(ham_args):
                deger = ae.group(2) or ae.group(3) or ae.group(4) or ""
                args[ae.group(1)] = deger.strip()
        sonuclar.append((ad, args))
    return sonuclar


def raw_tool_call_var_mi(metin):
    """Metinde raw tool call deseni var mı? (hızlı bakış)"""
    return bool(ham_tool_call_ayir(metin))


# ── Argüman düzeltme ────────────────────────────────────────────────

def tool_argumani_duzelt(tool_name, args):
    """Küçük modelin ürettiği hatalı tool argümanlarını düzelt."""
    if not isinstance(args, dict):
        return args

    # --- list_files düzeltmeleri ---
    if tool_name == "list_files":
        folder = args.get("folder", "")
        if folder:
            folder_lower = folder.strip().lower()
            yanlis_degerler = (
                "klasoru", "klasor", "klasör", "klasörü", "klasorde",
                "klasörde", "dosyalari", "dosyaları", "dosyalar",
                "listesi", "listele", "dosya",
            )
            if folder_lower in yanlis_degerler:
                args["folder"] = os.path.expanduser("~")
            elif len(folder.strip()) < 2:
                args["folder"] = os.path.expanduser("~")

    # --- read_file düzeltmeleri ---
    if tool_name == "read_file":
        path = args.get("path", "")
        if path:
            path_lower = path.strip().lower()
            yanlis_degerler = (
                "dosya", "dosyasi", "dosyası", "dosyayi", "dosyayı",
                "oku", "icerik", "içerik", "metin", "text",
            )
            if path_lower in yanlis_degerler:
                args["path"] = ""

    return args


# ── Argüman parsing ─────────────────────────────────────────────────

def parse_args(args):
    """Tool argümanlarını parse eder."""
    if isinstance(args, str):
        try:
            return json.loads(args)
        except (json.JSONDecodeError, TypeError):
            return {}
    return args


# ── Tool calling döngüsü ────────────────────────────────────────────

TUR_SINIRI = 3


def tool_calling_multi(tool_calls, mesajlar, brain, model, js_callback,
                        calistir, tools=None, tur_siniri=TUR_SINIRI,
                        knowledge_dir="", gorevler_file=""):
    """Tool sonuçlarını modele geri göndererek anlamlı cevap üretir.

    Cok adimli isler icin DONGU: model sonucu gordukten sonra yeni bir arac
    isteyebilir. Son turda arac verilmez ki dongu kapansin.

    YETKİ TAVANI: `tools` parametresi tavan setidir.

    Dönüş: (cevap_metni, arac_ciktilari)
    """
    tum_sonuclar = []
    expanded = list(mesajlar)

    for tur in range(tur_siniri):
        tur_sonuclari = []
        for call in tool_calls:
            func = call.get("function", {})
            tool_name = func.get("name", "")
            args = parse_args(func.get("arguments", "{}"))
            args = tool_argumani_duzelt(tool_name, args)
            js_callback("BasakUI.toolStatus(" + json.dumps(
                TOOL_LABELS.get(tool_name, "İşleniyor..."),
                ensure_ascii=False) + ")")

            # Onay sistemi
            from chat.approval import onay_bekle
            from tools.permissions import onay_gerekli_mi
            if onay_gerekli_mi(tool_name):
                # BUG #2 FIX: tanimsiz i degiskeni yerine call.get('id') kullan
                call_id = call.get("id") or ("call_%d" % len(tur_sonuclari))
                onaylandi = onay_bekle(call_id, tool_name, args)
                if not onaylandi:
                    net = "Onay verilmediği için işlem iptal edildi."
                    tur_sonuclari.append((tool_name, net))
                    continue

            sonuc = calistir(tool_name, args, knowledge_dir, gorevler_file)
            net = sonucu_donustur(tool_name, sonuc)
            tur_sonuclari.append((tool_name, net))

        expanded = expanded + [
            {"role": "assistant", "content": "", "tool_calls": tool_calls}]
        for i, (_isim, sonuc) in enumerate(tur_sonuclari):
            expanded.append({
                "role": "tool",
                "tool_call_id": tool_calls[i].get("id", "call_%d" % i),
                "content": sonuc,
            })
        tum_sonuclar.extend(tur_sonuclari)

        # Son turda arac verilmez
        sonraki_araclar = tools if tur < tur_siniri - 1 else None
        tool_sonuclari_text = "\n".join(
            "%s: %s" % (ad, net[:300]) for ad, net in tur_sonuclari)
        expanded = expanded + [{
            "role": "user",
            "content": (
                "Araç sonuçları:\n" + tool_sonuclari_text +
                "\n\nŞimdi bu sonuçları KISA ve DOĞAL TÜRKÇE ile özetle. "
                "[Ö], badge::, kod, bash kullanma. "
                "Kullanıcıya doğal dil ile anlat."
            ),
        }]
        try:
            # _yapi_kwargi geri yuklenir (circular import onlemi: lazy import)
            from _chat_legacy import _yapi_kwargi
            son_yanit, _ = brain.cevapla(expanded, model,
                                         tools=sonraki_araclar,
                                         **_yapi_kwargi(brain))
        except Exception:
            break

        yeni_cagrilar = son_yanit.get("tool_calls")
        if yeni_cagrilar:
            tool_calls = yeni_cagrilar
            continue

        # temizle cevap: gate modulundeki temizle'yi kullan
        from chat.gate import temizle as _temizle_fn
        son_cevap = _temizle_fn(son_yanit.get("content", ""))
        if son_cevap:
            return (son_cevap, tum_sonuclar)
        break

    # FALLBACK: Model contract takip etmediyse ham tool ciktisi kaliyor.
    from olcu import arac_cikti_kur
    temiz_sonuclar = []
    for ad, net in tum_sonuclar:
        if net and 'badge::' in str(net):
            temiz_sonuclar.append(arac_cikti_kur(ad, net))
        else:
            temiz_sonuclar.append(net)
    return ("\n".join(s for s in temiz_sonuclar if s), tum_sonuclar)


# ── Yardımcılar ─────────────────────────────────────────────────────

def sonucu_donustur(tool_name, sonuc):
    """Tool sonucunu metin formatına çevirir."""
    if "error" in sonuc:
        return "Hata: " + sonuc["error"]
    return sonuc.get("result", "İşlem tamamlandı.")


def temizle_cevap(text):
    """Model cevabını temizler (gate temizliğinden önce basit temizlik)."""
    if not text:
        return ""
    if not isinstance(text, str):
        if isinstance(text, dict):
            text = text.get("content", str(text))
        else:
            text = str(text)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r'badge::[OÖ]::', '', text)
    text = re.sub(r'badge::[^\n]*', '', text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
