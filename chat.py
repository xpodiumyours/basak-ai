"""chat.py — Sohbet ve tool calling akisi.

Varsayilan model: Groq (ucretsiz, hizli).
Yerel Ollama sadece Groq calismazsa fallback olarak kullanilir.
"""

import json
import os
import re
import threading
import time

BASE = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE, "gecmis.json")
SETTINGS_FILE = os.path.join(BASE, "ayarlar.json")
KNOWLEDGE_DIR = os.path.join(BASE, "knowledge")
KNOWLEDGE_MAX_CHARS = 4000
GOREVLER_FILE = os.path.join(BASE, "gorevler.json")
MAX_HISTORY = 20

TOOL_LABELS = {
    "web_search": "Aranıyor...",
    "add_task": "Görev ekleniyor...",
    "list_tasks": "Görevler listeleniyor...",
    "complete_task": "Tamamlanıyor...",
    "save_note": "Kaydediliyor...",
    "read_file": "Dosya okunuyor...",
    "write_file_tool": "Dosya yazılıyor...",
    "list_files": "Dosyalar listeleniyor...",
    "ac_uygulama": "Uygulama açılıyor...",
}

TOOL_YONLENDIRME = (
    "\nARAÇLARI NASIL KULLANIRSIN:\n"
    "- Kullanıcı bir şey yapacağını söylediğinde (yap, et, al, git, hazırla) → add_task\n"
    "- Kullanıcı görevlerini sorduğunda → list_tasks\n"
    "- Kullanıcı bir işi bitirdiğini söylediğinde → complete_task\n"
    "- Kullanıcı bir şeyi hatırlamanı istediğinde → save_note\n"
    "- Güncel bilgi gerektiğinde (hava, fiyat, haber) → web_search\n"
    "- Kullanıcı bir dosyanın içeriğini okumak istediğinde → read_file\n"
    "- Kullanıcı bir dosyaya yazmak/güncellemek istediğinde → write_file_tool\n"
    "- Kullanıcı klasördeki dosyaları görmek istediğinde → list_files\n"
    "- Kullanıcı bir uygulama açmak istediğinde (tarayıcı, not defteri) → ac_uygulama\n"
    "- Selamlaşma, veda, basit sohbet → tool KULLANMA, doğrudan cevap ver\n\n"
    "ÖNEMLİ: Tool çağrısından sonra tool sonucunu kullanıcıya sun."
)

_TOOL_KELIMELERI = {
    "add_task": ["yap", "et", "al", "git", "hazırla", "başla", "bitir", "ekle",
                  "kaydet", "not al", "satın al", "alışveriş", "görev"],
    "list_tasks": ["görev", "yapacak", "listele", "ne yapacağım", "yapacaklarım",
                   "hatırlatma", "plan"],
    "complete_task": ["bitirdim", "tamamladım", "yaptım", "hallettim",
                      "görevi bitir", "işlem tamam"],
    "save_note": ["hatırla", "not al", "kaydet", "bunu hatırla", "not et",
                  "aklında tut"],
    "web_search": ["hava", "sıcaklık", "fiyat", "haber", "güncel",
                   "para", "dolar", "euro", "kur", "borsa", "döviz"],
    "read_file": ["dosyayı oku", "içeriğe bak", "dosya oku", "okumak istiyorum",
                  "göster", "oku"],
    "write_file_tool": ["dosyaya yaz", "dosyayı güncelle", "yeni dosya oluştur",
                        "dosya oluştur", "güncelle"],
    "list_files": ["dosyaları göster", "klasörde ne var", "dosyaları listele",
                   "klasör içeriği", "listele"],
    "ac_uygulama": ["tarayıcıyı aç", "not defterini aç", "uygulama aç",
                    "hesap makinesini aç", "dosya yöneticisini aç", "vscode'u aç"],
}


def _tool_gerekli_mi(text):
    text_lower = text.lower()
    bulunan = []
    for tool_name, kelimeler in _TOOL_KELIMELERI.items():
        for kelime in kelimeler:
            if kelime in text_lower:
                bulunan.append(tool_name)
                break
    return bool(bulunan), bulunan


def _dil_kontrol(text):
    if not text or not isinstance(text, str):
        return True
    alfa_sayisi = sum(1 for ch in text if ch.isalpha())
    if alfa_sayisi < 5:
        return True
    ingilizce = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    oransal_ingilizce = ingilizce / alfa_sayisi
    if oransal_ingilizce > 0.6:
        return False
    return True


_knowledge_cache = None
_knowledge_lock = threading.Lock()
_knowledge_last_load = 0


def _load_knowledge(force=False):
    global _knowledge_cache, _knowledge_last_load
    now = time.time()
    if not force and _knowledge_cache is not None and (now - _knowledge_last_load) < 60:
        return
    _knowledge_last_load = now
    try:
        dosyalar = sorted(
            ad for ad in os.listdir(KNOWLEDGE_DIR)
            if ad.lower().endswith((".md", ".txt")) and ad != "README.md"
        )
    except OSError:
        _knowledge_cache = ""
        return

    parcalar = []
    kalan = KNOWLEDGE_MAX_CHARS

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


def reload_knowledge():
    _load_knowledge(force=True)


def yukle(path, varsayilan):
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return varsayilan


def kaydet(path, veri):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)


def _hangi_toollari_gonder(bulunan_toollar, tum_toollar):
    if not bulunan_toollar:
        return None
    filtreli = [
        t for t in tum_toollar
        if t["function"]["name"] in bulunan_toollar
    ]
    return filtreli if filtreli else None


def mesaj_isle(text, brain, system_prompt, js_callback, tools):
    from tools import calistir

    text = (text or "").strip()
    js_callback("BasakUI.thinking()")
    if not text:
        js_callback("BasakUI.error(" + _j("Bos mesaj") + ")")
        return

    # Groq musait mi? Musaitse her seyde Groq kullan
    groq_musait = brain.bulut_musait()

    if not groq_musait:
        modeller = brain.yerel_modeller()
        if not modeller:
            js_callback("BasakUI.error(" + _j("Ollama calismiyor — lutfen Ollama'yı baslat") + ")")
            return
        model = yukle(SETTINGS_FILE, {}).get("model")
        if model not in modeller:
            model = modeller[0]
    else:
        model = yukle(SETTINGS_FILE, {}).get("model", "groq")

    raw_gecmis = [m for m in yukle(HISTORY_FILE, []) if m.get("role") != "system"]
    gecmis = _temizle_history(raw_gecmis)

    tam_prompt = system_prompt + TOOL_YONLENDIRME
    mesajlar = [{"role": "system", "content": tam_prompt}]

    with _knowledge_lock:
        _load_knowledge(force=False)
        bilgi = _knowledge_cache
    if bilgi:
        mesajlar.append({
            "role": "system",
            "content": "Casper'in notlari:\n\n" + bilgi,
        })

    mesajlar += gecmis[-MAX_HISTORY:] + [{"role": "user", "content": text}]

    # Tool gerekli mi?
    tools_gerekli, hangi_toollar = _tool_gerekli_mi(text)
    filtreli_tools = _hangi_toollari_gonder(hangi_toollar, tools) if tools_gerekli else None

    # Her durumda once Groq dene (musaitse)
    if groq_musait:
        try:
            yanit, kaynak = brain.cevapla(mesajlar, model, tools=filtreli_tools)
        except Exception as e:
            hata_str = str(e)
            if "429" in hata_str or "rate" in hata_str.lower():
                # Rate limit → yerel modele dus
                try:
                    yanit, kaynak = brain.yerel_cevap(mesajlar, model), "yerel"
                    yanit = {"content": yanit} if isinstance(yanit, str) else yanit
                except Exception:
                    js_callback("BasakUI.error(" + _j("Cok fazla istek, biraz bekle") + ")")
                    return
            else:
                # Diger hatalar → yerel modele dus
                try:
                    yanit, kaynak = brain.yerel_cevap(mesajlar, model), "yerel"
                    yanit = {"content": yanit} if isinstance(yanit, str) else yanit
                except Exception:
                    js_callback("BasakUI.error(" + _j("Beyin hatasi: " + hata_str[:100]) + ")")
                    retu
