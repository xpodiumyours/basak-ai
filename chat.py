"""chat.py — Sohbet ve tool calling akisi.

Tur 6: Kalite iyilestirmeleri:
- Knowledge cache 4000 karaktere cikarildi
- History 5'e cikarildi
- Multi-turn tool calling: tool sonucu modele geri gonderilir
- Daha iyi hata yonetimi
"""

import json
import os
import re
import threading

BASE = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE, "gecmis.json")
SETTINGS_FILE = os.path.join(BASE, "ayarlar.json")
KNOWLEDGE_DIR = os.path.join(BASE, "knowledge")
KNOWLEDGE_MAX_CHARS = 4000
GOREVLER_FILE = os.path.join(BASE, "gorevler.json")
MAX_HISTORY = 5

TOOL_LABELS = {
    "web_search": "Aranıyor...",
    "add_task": "Görev ekleniyor...",
    "list_tasks": "Görevler listeleniyor...",
    "complete_task": "Tamamlanıyor...",
    "save_note": "Kaydediliyor...",
}

TOOL_YONLENDIRME = (
    "\nARAÇLARI NASIL KULLANIRSIN:\n"
    "- Kullanıcı bir şey yapacağını söylediğinde (yap, et, al, git, hazırla) → add_task\n"
    "- Kullanıcı görevlerini sorduğunda → list_tasks\n"
    "- Kullanıcı bir işi bitirdiğini söylediğinde → complete_task\n"
    "- Kullanıcı bir şeyi hatırlamanı istediğinde → save_note\n"
    "- Güncel bilgi gerektiğinde (hava, fiyat, haber) → web_search\n"
    "- Selamlaşma, veda, basit sohbet → tool KULLANMA, doğrudan cevap ver\n\n"
    "ÖNEMLİ: Tool çağrısından sonra tool sonucunu kullanıcıya sun."
)

_knowledge_cache = None
_knowledge_lock = threading.Lock()


def _load_knowledge():
    global _knowledge_cache
    try:
        dosyalar = sorted(
            ad for ad in os.listdir(KNOWLEDGE_DIR)
            if ad.lower().endswith((".md", ".txt")) and ad != "README.md"
        )
    except OSError:
        _knowledge_cache = ""
        return

    # INDEX.md varsa onu once yukle (oncelikli bilgi)
    parcalar = []
    kalan = KNOWLEDGE_MAX_CHARS

    # INDEX.md oncelikli
    if "INDEX.md" in dosyalar:
        dosyalar.remove("INDEX.md")
        dosyalar.insert(0, "INDEX.md")

    for ad in dosyalar:
        if kalan <= 0:
            break
        try:
            with open(os.path.join(KNOWLEDGE_DIR, ad), "r",
                       encoding="utf-8", errors="replace") as f:
                icerik = f.read().strip()
        except OSError:
            continue
        if not icerik:
            continue
        if len(icerik) > kalan:
            icerik = icerik[:kalan].rstrip() + "..."
        parcalar.append("### " + ad + "\n" + icerik)
        kalan -= len(icerik)

    _knowledge_cache = "\n\n".join(parcalar)


def yukle(path, varsayilan):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return varsayilan


def kaydet(path, veri):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)


def mesaj_isle(text, brain, system_prompt, js_callback, tools):
    from tools import calistir

    text = (text or "").strip()
    js_callback("BasakUI.thinking()")
    if not text:
        js_callback("BasakUI.error(" + _j("Bos mesaj") + ")")
        return

    modeller = brain.yerel_modeller()
    if not modeller:
        js_callback("BasakUI.error(" + _j("Ollama calismiyor — lutfen Ollama'yı baslat") + ")")
        return

    model = yukle(SETTINGS_FILE, {}).get("model")
    if model not in modeller:
        model = modeller[0]

    raw_gecmis = [m for m in yukle(HISTORY_FILE, []) if m.get("role") != "system"]
    gecmis = _temizle_history(raw_gecmis)

    tam_prompt = system_prompt + TOOL_YONLENDIRME
    mesajlar = [{"role": "system", "content": tam_prompt}]

    # Knowledge bilgisini ekle
    with _knowledge_lock:
        bilgi = _knowledge_cache
    if bilgi:
        mesajlar.append({
            "role": "system",
            "content": "Casper'in notlari:\n\n" + bilgi,
        })

    mesajlar += gecmis[-MAX_HISTORY:] + [{"role": "user", "content": text}]

    # Model cevabi al — tool calling ile birlikte
    try:
        yanit, kaynak = brain.cevapla(mesajlar, model, tools=tools)
    except Exception as e:
        hata_str = str(e)
        # Rate limit hatasi → Ollama'ya dus
        if "429" in hata_str or "rate" in hata_str.lower():
            try:
                yanit, kaynak = brain.yerel_cevap(mesajlar, model)
                yanit = {"content": yanit}
            except Exception:
                js_callback("BasakUI.error(" + _j("Cok fazla istek gonderildi, biraz bekle") + ")")
                return
        else:
            js_callback("BasakUI.error(" + _j("Beyin hatasi: " + hata_str[:100]) + ")")
            return

    tool_calls = yanit.get("tool_calls")
    if not tool_calls:
        cevap = _temizle(yanit.get("content", ""))
        _save_and_reply(text, cevap, kaynak, gecmis, js_callback)
        return

    # Multi-turn tool calling: tool sonucunu modele geri gonder
    cevap = _tool_calling_multi(tool_calls, mesajlar, brain, model, js_callback, calistir)
    _save_and_reply(text, cevap, kaynak, gecmis, js_callback)


def _tool_calling_multi(tool_calls, mesajlar, brain, model, js_callback, calistir):
    """Tool sonuclarini modele geri gondererek anlamlil cevap uretir."""
    # Ilk tool sonuclarini al
    tool_sonuclari = []
    for call in tool_calls:
        func = call.get("function", {})
        tool_name = func.get("name", "")
        args = _parse_args(func.get("arguments", "{}"))
        js_callback("BasakUI.toolStatus(" + _j(
            TOOL_LABELS.get(tool_name, "Isleniyor...")) + ")")
        sonuc = calistir(tool_name, args, KNOWLEDGE_DIR, GOREVLER_FILE)
        net = _sonucu_donustur(tool_name, sonuc)
        tool_sonuclari.append((tool_name, net))

    # Tool sonuclarini modele geri gonder (multi-turn)
    tool_sonuc_metni = "\n".join(
        f"[{isim} sonucu]: {sonuc}" for isim, sonuc in tool_sonuclari
    )

    # Tool mesajlarini ekle ve modelden son cevabi al
    tool_msg = [{"role": "assistant", "content": None, "tool_calls": tool_calls}]
    tool_result_msgs = []
    for i, (isim, sonuc) in enumerate(tool_sonuclari):
        tool_result_msgs.append({
            "role": "tool",
            "content": sonuc,
        })

    # Modelin son cevabini al
    expanded = mesajlar + tool_msg + tool_result_msgs
    try:
        son_yanit, _ = brain.cevapla(expanded, model, tools=None)
        son_cevap = _temizle(son_yanit.get("content", ""))
        if son_cevap:
            return son_cevap
    except Exception:
        pass

    # Fallback: tool sonuclarini dogrudan don
    return "\n".join(sonuc for _, sonuc in tool_sonuclari)


def _save_and_reply(text, cevap, kaynak, gecmis, js_callback):
    gecmis += [{"role": "user", "content": text},
               {"role": "assistant", "content": cevap}]
    kaydet(HISTORY_FILE, gecmis[-40:])
    js_callback("BasakUI.reply(" + _j(cevap) + ", " + _j(kaynak) + ")")


def _temizle_history(gecmis):
    temiz = []
    for m in gecmis:
        if m.get("role") == "assistant" and m.get("tool_calls"):
            temiz.append({"role": "assistant", "content": m.get("content", "")})
        else:
            temiz.append(m)
    return temiz


def _sonucu_donustur(tool_name, sonuc):
    if "error" in sonuc:
        return "Hata: " + sonuc["error"]
    return sonuc.get("result", "Islem tamamlandi.")


def _temizle(text):
    if not text:
        return ""
    text = re.sub(r"<think>.*?</think>", "", text, flags=re.DOTALL)
    text = re.sub(r"```.*?```", "", text, flags=re.DOTALL)
    text = re.sub(r"`([^`]+)`", r"\1", text)
    text = re.sub(r'\*\*([^*]+)\*\*', r'\1', text)
    text = re.sub(r'\*([^*]+)\*', r'\1', text)
    text = re.sub(r'^#{1,6}\s+', '', text, flags=re.MULTILINE)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _parse_args(args):
    if isinstance(args, str):
        try:
            return json.loads(args)
        except (json.JSONDecodeError, TypeError):
            return {}
    return args


def init_cache():
    _load_knowledge()


def _j(obj):
    return json.dumps(obj, ensure_ascii=False)
