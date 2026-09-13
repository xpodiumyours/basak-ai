"""chat/tools.py — doğal tool-calling döngüsü.

Modelin istediği araçlar çalıştırılır, sonuçlar standart tool mesajları olarak
modele geri verilir ve model isterse yeni araç çağırarak devam eder. Başak
ara sonuçlardan sonra modele nasıl cevap vereceğini dayatmaz. Güvenlik ve
yazma onayı uygulama katmanında kalır.
"""

import json
import logging
import os
import re

logger = logging.getLogger(__name__)

TANINMIS_TOOLLAR = frozenset((
    "list_files", "read_file", "write_file_tool", "web_search",
    "sayfa_oku", "add_task", "list_tasks", "complete_task",
    "save_note", "deftere_kaydet", "ac_uygulama", "get_reminders",
    "video_analyze", "image_analyze", "model_stats",
    "git_durum", "belge_ara", "dosya_bilgi",
    "is_ac", "is_liste", "is_onayla",
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
    "list_files": "Klasör okunuyor...",
    "read_file": "Dosya okunuyor...",
    "sayfa_oku": "Sayfa okunuyor...",
    "is_ac": "İş açılıyor...",
    "is_liste": "İşler okunuyor...",
    "is_onayla": "İş onaylanıyor...",
}


def _arac_detay(tool_name, args):
    try:
        args = args or {}
        if tool_name == "list_files":
            return args.get("folder", "")
        if tool_name == "read_file":
            return args.get("path", "")
        if tool_name == "web_search":
            return args.get("query", "")
        if tool_name == "sayfa_oku":
            return args.get("url", "")
        if tool_name in ("git_durum", "belge_ara", "dosya_bilgi"):
            return args.get("proje", "")
        if tool_name in ("save_note", "deftere_kaydet"):
            return args.get("title", "")
        if tool_name == "add_task":
            return args.get("text", args.get("title", ""))
    except Exception:
        pass
    return ""


def _durum_metni(tool_name, args):
    etiket = TOOL_LABELS.get(tool_name, "İşleniyor...")
    detay = _arac_detay(tool_name, args)
    if detay:
        detay = str(detay)
        if len(detay) > 80:
            detay = detay[:80].rstrip() + "..."
        return "%s %s" % (etiket, detay)
    return etiket


def _yazma_koku():
    try:
        from tools.executor import ToolContext
        return ToolContext("", "").base_dir
    except Exception:
        return os.getcwd()


def _otomatik_yazma(args):
    try:
        from tools import file_ops as _fops
        hedef = str((args or {}).get("path", "") or "")
        if not hedef:
            return True
        base = _yazma_koku()
        mutlak = (os.path.realpath(hedef) if os.path.isabs(hedef)
                  else os.path.realpath(os.path.join(base, hedef)))
        return bool(_fops._otomatik_yazma_mi(mutlak, base))
    except Exception:
        return False


def _yazma_onayi(call, args, js_callback):
    """Güvenli alan dışına yazmayı kullanıcı onaylamadan yapma."""
    try:
        from chat.approval import _system as _onay
        icerik = str((args or {}).get("content", "") or "")
        if len(icerik) > 300:
            icerik = icerik[:300].rstrip() + "..."
        return bool(_onay.bekle(
            str((call or {}).get("id", "call_sorumsuz")),
            "write_file_tool",
            {"path": str((args or {}).get("path", "")),
             "icerik_ozet": icerik},
            timeout=90, js_callback=js_callback))
    except Exception as e:
        logger.warning("Onay sorulamadi, yazma iptal: %s", e)
        return False


_RAW_TOOL_CALL_RE = re.compile(r'\[?(\w+)\]?\s*\(\s*([^)]*)\s*\)')
_RAW_ARG_RE = re.compile(
    r'''(\w+)\s*=\s*(?:"([^"]*)"|'([^']*)'|([^,)]+))''')


def ham_tool_call_ayir(metin):
    if not metin or not isinstance(metin, str):
        return []
    sonuclar = []
    for eslesme in _RAW_TOOL_CALL_RE.finditer(metin):
        ad = eslesme.group(1)
        if ad not in TANINMIS_TOOLLAR:
            continue
        args = {}
        ham_args = eslesme.group(2).strip()
        if ham_args:
            for ae in _RAW_ARG_RE.finditer(ham_args):
                deger = ae.group(2) or ae.group(3) or ae.group(4) or ""
                args[ae.group(1)] = deger.strip()
        sonuclar.append((ad, args))
    return sonuclar


def raw_tool_call_var_mi(metin):
    return bool(ham_tool_call_ayir(metin))


def tool_argumani_duzelt(tool_name, args):
    """Bariz bozuk dosya argümanlarını güvenli biçimde düzelt."""
    if not isinstance(args, dict):
        return args
    if tool_name == "list_files":
        folder = args.get("folder", "")
        if folder:
            yanlis = (
                "klasoru", "klasor", "klasör", "klasörü", "klasorde",
                "klasörde", "dosyalari", "dosyaları", "dosyalar",
                "listesi", "listele", "dosya",
            )
            if folder.strip().lower() in yanlis or len(folder.strip()) < 2:
                args["folder"] = os.path.expanduser("~")
    if tool_name == "read_file":
        path = args.get("path", "")
        if path and path.strip().lower() in (
                "dosya", "dosyasi", "dosyası", "dosyayi", "dosyayı",
                "oku", "icerik", "içerik", "metin", "text"):
            args["path"] = ""
    return args


def parse_args(args):
    if isinstance(args, str):
        try:
            return json.loads(args)
        except (json.JSONDecodeError, TypeError):
            return {}
    return args if isinstance(args, dict) else {}


# Sonsuz döngüye karşı yalnız teknik güvenlik tavanı. Eski küçük-model 3 tur
# kısıtı kaldırıldı; tüm modeller aynı çok-adımlı çalışma alanına sahip.
TUR_SINIRI = 24

# Araç sonuçlarının tek bir aşırı büyük dosyayla tüm bağlamı tüketmesini önleyen
# teknik güvenlik sınırı. Eski 1500 karakter sınırı uzun görevleri kesiyordu.
ARAC_SONUC_TAVAN = 12000


def tool_calling_multi(tool_calls, mesajlar, brain, model, js_callback,
                        calistir, tools=None, tur_siniri=TUR_SINIRI,
                        knowledge_dir="", gorevler_file=""):
    """Modelin doğal çok-adımlı araç döngüsünü çalıştır."""
    tum_sonuclar = []
    tum_kaynaklar = []
    expanded = list(mesajlar)

    for _tur in range(max(1, int(tur_siniri))):
        if not tool_calls:
            break

        expanded.append({
            "role": "assistant",
            "content": "",
            "tool_calls": tool_calls,
        })

        for idx, call in enumerate(tool_calls):
            func = call.get("function", {})
            tool_name = func.get("name", "")
            args = tool_argumani_duzelt(
                tool_name, parse_args(func.get("arguments", "{}")))
            call_id = call.get("id", "call_%d" % idx)

            if tool_name not in TANINMIS_TOOLLAR:
                net = "Hata: bilinmeyen araç: %s" % tool_name
            elif (tool_name == "write_file_tool"
                  and not _otomatik_yazma(args)
                  and not _yazma_onayi(call, args, js_callback)):
                net = "Kullanıcı onaylamadı — yazılmadı."
            else:
                js_callback("BasakUI.toolStatus(" + json.dumps(
                    _durum_metni(tool_name, args), ensure_ascii=False) + ")")
                try:
                    sonuc = calistir(tool_name, args,
                                     knowledge_dir, gorevler_file)
                    net = sonucu_donustur(tool_name, sonuc)
                except Exception as e:
                    net = "Hata: %s" % str(e)

            tum_sonuclar.append((tool_name, net))
            if isinstance(net, str) and not net.startswith("Hata:"):
                detay = _arac_detay(tool_name, args)
                etiket = ("%s %s" % (tool_name, detay)).strip()
                if etiket and etiket not in tum_kaynaklar:
                    tum_kaynaklar.append(etiket)

            modele = str(net)
            if len(modele) > ARAC_SONUC_TAVAN:
                modele = (modele[:ARAC_SONUC_TAVAN].rstrip()
                          + "... [sonuç teknik sınırda kısaltıldı]")
            expanded.append({
                "role": "tool",
                "tool_call_id": call_id,
                "content": modele,
            })

        try:
            from _chat_legacy import _yapi_kwargi
            son_yanit, _ = brain.cevapla(
                expanded, model, tools=tools, **_yapi_kwargi(brain))
        except Exception as e:
            logger.warning("Tool sonrasi model cagrisi kesildi: %s", e)
            break

        yeni_cagrilar = son_yanit.get("tool_calls") or []
        if yeni_cagrilar:
            tool_calls = yeni_cagrilar
            continue

        from chat.gate import temizle as _temizle_fn
        son_cevap = _temizle_fn(son_yanit.get("content", ""))
        if son_cevap:
            return (_kaynak_satiri_ekle(son_cevap, tum_kaynaklar),
                    tum_sonuclar)
        break

    # Model final metin üretmediyse kullanıcının gerçek araç sonuçlarını kaybetme.
    return ("\n".join(str(net) for _ad, net in tum_sonuclar if net),
            tum_sonuclar)


def _kaynak_satiri_ekle(cevap, kaynaklar):
    if not kaynaklar:
        return cevap
    satir = "\n\nKaynaklar: " + "; ".join(kaynaklar[:5])
    if len(kaynaklar) > 5:
        satir += " (+%d kaynak daha)" % (len(kaynaklar) - 5)
    return (cevap or "").rstrip() + satir


def sonucu_donustur(tool_name, sonuc):
    if not isinstance(sonuc, dict):
        return str(sonuc)
    if "error" in sonuc:
        return "Hata: " + str(sonuc["error"])
    return str(sonuc.get("result", "İşlem tamamlandı."))


def temizle_cevap(text):
    if not text:
        return ""
    if not isinstance(text, str):
        text = text.get("content", str(text)) if isinstance(text, dict) else str(text)
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r'badge::[OÖ]::', '', text)
    text = re.sub(r'badge::[^\n]*', '', text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()
