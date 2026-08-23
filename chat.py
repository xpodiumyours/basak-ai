"""chat.py — Sohbet ve tool calling akisi.

Faz 0 duzeltmeleri:
- Tool sadece gereken mesajlarda Groq'a gonderiliyor
- Yerel Ollama varsayilan olarak kullaniliyor
- Dil kontrolu: Karisik dil cevap gelirse fallback
"""

import json
import logging
import os
import re
import threading
import uuid

from olcu import (cikis_kapisi, PROMPT_BLOGU, YEDEK_CUMLE, HAM_BASLIK,
                  ham_olcum_satirlari)

logger = logging.getLogger(__name__)

# P3 Session Manager: uygulama acilista bir oturum kimligi uretir;
# her kayda islenir (coklu oturum/yarim gorev ayirt etmenin temeli)
OTURUM_ID = uuid.uuid4().hex[:8]

BASE = os.path.dirname(os.path.abspath(__file__))
HISTORY_FILE = os.path.join(BASE, "gecmis.json")
SETTINGS_FILE = os.path.join(BASE, "ayarlar.json")
KNOWLEDGE_DIR = os.path.join(BASE, "knowledge")
OBSIDIAN_DIR = os.path.join(BASE, "Basak")
DEFTER_DIR = os.path.join(BASE, "defter")
KNOWLEDGE_MAX_CHARS = 5000
GOREVLER_FILE = os.path.join(BASE, "gorevler.json")
MAX_HISTORY = 20

# P2 hafiza motoru — arka planda hazirlanir, hazir degilse sohbet etkilenmez
_hafiza = None
_hafiza_lock = threading.Lock()


def _hafiza_al():
    """Motoru tek seferlik olusturur; acilamazsa None doner (sohbet devam eder)."""
    global _hafiza
    with _hafiza_lock:
        if _hafiza is None:
            try:
                from memory import HafizaMotoru
                _hafiza = HafizaMotoru()
            except Exception as e:
                logger.warning("Hafiza motoru acilamadi: %s", e)
                _hafiza = False
    return _hafiza or None

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

# O-1: once olc, sonra konus (OLCU.md §3)
OLCU_YONLENDIRME = (
    "\nÖLÇÜM ÖNCE GELİR — ZORUNLU AKIŞ:\n"
    "1) Proje adı, durum, değişiklik, commit sorularında ÖNCE git_durum veya belge_ara veya dosya_bilgi araçlarını çalıştır.\n"
    "2) Cevabın DAYANAĞI yalnızca araç çıktısı olsun — kendi bilginden/önceki bilgiden olgu katma.\n"
    "   Ama çıktıyı olduğu gibi yapıştırma: kısa bir birebir alıntıyı kanıt olarak taşı, "
    "sonra sorunun cevabını KENDİ Türkçe cümlenle söyle. Kullanıcı makine çıktısı değil, cevap okur.\n"
    "3) Ölçülemeyen şeyde '[B] Bunun ölçümü yapılamıyor: ...' de.\n"
    "4) Araç kullanmadan cevap verme — measurement tools her zaman mevcut.\n"
    "KURAL: Proje durumu/değişiklik/commit/dosya sorularında measurement tool kullanmadan cevap vermek YASAKTIR.\n"
)

# Tool gerektiren anahtar kelimeler
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
    # O-1 olcum araclari: proje adi gecen her soru once olculur
    "git_durum": ["vixrex", "numeramatch", "xses",
                  "durumu ne", "durum ne", "son commit", "ne yapiyoruz"],
    "belge_ara": ["planda ne", "belgede ne", "listede ne yaziyor",
                  "dokumanda", "gorev listesinde"],
}


# Görev türüne göre beyin tercihi P3'te brain/secici.py'ye taşındı —
# seçim motoru şeffaf gerekçeyle çalışır, burada tekrar edilmez.


def _tool_gerekli_mi(text):
    """Mesajin tool cagrisi gerektirip gerektirmedigini kontrol eder."""
    text_lower = text.lower()
    bulunan = []

    for tool_name, kelimeler in _TOOL_KELIMELERI.items():
        for kelime in kelimeler:
            if kelime in text_lower:
                bulunan.append(tool_name)
                break

    return bool(bulunan), bulunan


def _dil_kontrol(text):
    """Cevabin cogunlukla Turkce olup olmadigini kontrol eder."""
    if not text or not isinstance(text, str):
        return True

    alfa_sayisi = sum(1 for ch in text if ch.isalpha())
    if alfa_sayisi < 5:
        return True

    ingilizce = sum(1 for ch in text if ch.isascii() and ch.isalpha())
    oransal_ingilizce = ingilizce / alfa_sayisi

    # Eger alfabe karakterlerinin %60'tan fazlasi Ingilizce ise
    if oransal_ingilizce > 0.6:
        return False

    return True


# Saglayicilarin sizdirdigi dusunme metni tipik olarak Ingilizce ve
# "we need to / the user asks" kalibinda olur. _dil_kontrol bu is icin
# YETMIYOR: Turkce harflerin cogu ASCII oldugu icin duzgun Turkce cevabi
# da Ingilizce sayiyor (2026-08-23'te test yakaladi).
_ING_KELIMELER = frozenset("""the we need user should must answer because
let okay first then assistant tool call question response they there
what which about would could their this that with from have""".split())
_TR_KELIMELER = frozenset("""bir ve için bu şu var yok ile daha göre olarak
değil şimdi son ama veya gibi kadar sonra önce hangi nedir dalında""".split())


def _ingilizce_sizinti_mi(text):
    """Cevap, Turkce yanit degil de Ingilizce dusunme metni mi?"""
    if not text or not isinstance(text, str):
        return False
    kelimeler = re.findall(r"[a-zçğıöşü]+", text.lower())
    if len(kelimeler) < 8:
        return False
    ing = sum(1 for k in kelimeler if k in _ING_KELIMELER)
    tr = sum(1 for k in kelimeler if k in _TR_KELIMELER)
    return ing >= 3 and ing > tr


_knowledge_cache = None
_knowledge_lock = threading.Lock()

KNOWLEDGE_EMBED_CHARS = 2000  # Sadece bu kadar direkt embed edilir, geri kalan BM25


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

    parcalar = []
    kalan = KNOWLEDGE_EMBED_CHARS  # 2000 char embed için sınır

    if "INDEX.md" in dosyalar:
        dosyalar.remove("INDEX.md")
        dosyalar.insert(0, "INDEX.md")

    # Proje dokümanları da hafızaya karışsın (plan + kurallar)
    # Ortak defter: yalnız INDEX her mesaja girer; tek tek kayıtlar
    # hafıza motorunun aramasıyla, ilgiliyse çekilir (ORTAK-DEFTER.md §4)
    for ad_ek in ("defter/INDEX.md", "GOREV_LISTESI.md", "AGENTS.md"):
        if os.path.exists(os.path.join(BASE, ad_ek)) and ad_ek not in dosyalar:
            dosyalar.append(ad_ek)

    for ad in dosyalar:
        if kalan <= 0:
            break
        try:
            dosya_yolu = os.path.join(KNOWLEDGE_DIR, ad)
            if not os.path.exists(dosya_yolu):
                dosya_yolu = os.path.join(BASE, ad)
            with open(dosya_yolu, "r",
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

    # TÜM BILGI TABANININ %20'İNYI KORU, GERİ KALAN BM25'E BıLDİRIR
    if KNOWLEDGE_EMBED_CHARS < 12000:
        try:
            with open(os.path.join(KNOWLEDGE_DIR, "README.md"), "r",
                       encoding="utf-8", errors="replace") as f:
                readme = f.read().strip()
            # Toplam bilgi miktarını hesapla
            toplam_bilgi = KNOWLEDGE_EMBED_CHARS
            for ad in dosyalar:
                try:
                    yol = os.path.join(KNOWLEDGE_DIR, ad)
                    if not os.path.exists(yol):
                        yol = os.path.join(BASE, ad)
                    with open(yol, "r", encoding="utf-8", errors="replace") as f:
                        toplam_bilgi += len(f.read())
                except OSError:
                    pass
            kartik = f"\n\n--- BILGI EKSİĞİ: {toplam_bilgi - KNOWLEDGE_EMBED_CHARS} karakter BM25 hafızasına bırakıldı ---"
            _knowledge_cache = "\n\n".join(parcalar) + kartik
        except OSError:
            _knowledge_cache = "\n\n".join(parcalar)
    else:
        _knowledge_cache = "\n\n".join(parcalar)


def yukle(path, varsayilan):
    try:
        with open(path, "r", encoding="utf-8-sig") as f:
            return json.load(f)
    except (OSError, json.JSONDecodeError):
        return varsayilan


def kaydet(path, veri):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)


# Bağlam diyeti ADIM 1 (2026-08-23): kategori -> o tetikleyicide hangi
# araçların KILAVUZU gider. Eskiden tek anahtar kelime 18 aracın tamamını
# açıyordu (~3.000 token); artık yalnız ilgili aile gider.
_OLCUM_TOOLLARI = frozenset(("git_durum", "belge_ara", "dosya_bilgi"))
_ARAC_AILESI = {
    "add_task": frozenset(("add_task",)),
    "list_tasks": frozenset(("list_tasks", "get_reminders")),
    "complete_task": frozenset(("complete_task",)),
    "save_note": frozenset(("save_note", "deftere_kaydet")),
    "web_search": frozenset(("web_search", "sayfa_oku")),
    "git_durum": _OLCUM_TOOLLARI,
    "belge_ara": _OLCUM_TOOLLARI,
    "video_analyze": frozenset(("video_analyze",)),
    "image_analyze": frozenset(("image_analyze",)),
    "model_stats": frozenset(("model_stats",)),
    "dosya_islemi": frozenset(("read_file", "write_file_tool", "list_files")),
    "ac_uygulama": frozenset(("ac_uygulama",)),
}
# Bugune dek tam setle dolayli ulasilan araçlara minik tetikleyiciler
# (dinamik sunumda erisilebilir kalmanin sarti):
_EK_TETIKLER = {
    "dosya_islemi": ("dosya", "klasor", "klasör"),
    "ac_uygulama": ("uygulama", "çalıştır", "calistir"),
    "video_analyze": ("video",),
    "image_analyze": ("görüntü", "goruntu", "fotoğraf", "fotograf"),
    "model_stats": ("model istatistik", "hangi model", "performans"),
}


def _dinamik_araclar(text_lower, tools):
    """Soruya gore yalnız ilgili araç kılavuzlarını dondurur.

    Olçüm üçlüsü HER ZAMAN dahil (O-1 kurali — ÖLÇÜ.md §3). Verilen
    listede olmayan aile üyeleri sessizce elenir; yetki tavanı bozulmaz.
    """
    istenen = set(_OLCUM_TOOLLARI)
    for ad, kelimeler in _TOOL_KELIMELERI.items():
        if any(k in text_lower for k in kelimeler):
            istenen |= _ARAC_AILESI.get(ad, frozenset())
    for ad, kelimeler in _EK_TETIKLER.items():
        if any(k in text_lower for k in kelimeler):
            istenen |= _ARAC_AILESI.get(ad, frozenset())
    return [t for t in tools if t["function"]["name"] in istenen]


def mesaj_isle(text, brain, system_prompt, js_callback, tools):
    from tools import calistir

    text = (text or "").strip()

    # Konuşmacı bilgisini çıkar: "Merhaba [Casper]" → "Merhaba", aktif_konusmaci="Casper"
    aktif_konusmaci = None
    konusmaci_eslesme = re.search(r"\[([^\]]+)\]\s*$", text)
    if konusmaci_eslesme:
        aktif_konusmaci = konusmaci_eslesme.group(1)
        text = text[:konusmaci_eslesme.start()].strip()

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

    tam_prompt = system_prompt + TOOL_YONLENDIRME + OLCU_YONLENDIRME + PROMPT_BLOGU
    if aktif_konusmaci:
        tam_prompt += "\n\n[ANLIK DURUM] An itibarıyla konuşan kişi: %s. Ona göre hitap et." % aktif_konusmaci
    mesajlar = [{"role": "system", "content": tam_prompt}]

    with _knowledge_lock:
        bilgi = _knowledge_cache
    if bilgi:
        mesajlar.append({
            "role": "system",
            "content": "Casper'in notlari:\n\n" + bilgi,
        })

    anilar = _ilgili_anilar(text)
    if anilar:
        blok = "\n\n".join(
            "- %s (kaynak: %s)" % (a["text"][:500], a["source"] or a["kind"])
            for a in anilar
        )
        mesajlar.append({
            "role": "system",
            "content": (
                "Hafizandaki ilgili anilar ve notlar (eski sohbetlerden ve "
                "not defterinden geliyor; soruyla iliskiliyse kullan):\n\n" + blok
            ),
        })

    mesajlar += gecmis[-MAX_HISTORY:] + [{"role": "user", "content": text}]

    # Baglam diyeti ADIM 1: anahtar kelime artik TAM SETI acmaz — yalniz
    # ilgili arac ailesinin kilavuzu gider. Olcum uclusu her zaman acik
    # (O-1 kurali). Yetki tavani aynen gecer: dongu bu seti asamaz.
    if tools:
        aktif_toollar = _dinamik_araclar(text.lower(), tools)
    else:
        aktif_toollar = None

    # Tum mesajlar brain.cevapla uzerinden gider:
    # Router v2: secici.sec() gorev turune gore saglayici sirasini belirler.
    # Olcum Retry: measurement tool gerekliyse ve model tool_call dondurmediyse,
    # guclu Groq modeliyle (openai/gpt-oss-120b) 1 kez tekrar dene.
    _OLCUM_SET = {"git_durum", "belge_ara", "dosya_bilgi"}
    olcum_aktif = bool(aktif_toollar and any(
        t["function"]["name"] in _OLCUM_SET for t in aktif_toollar))
    _GUCLU_MODEL = "openai/gpt-oss-120b"
    _retry = 0
    MAX_RETRY = 1

    while _retry <= MAX_RETRY:
        try:
            override = _GUCLU_MODEL if _retry > 0 and olcum_aktif else None
            yanit, kaynak = brain.cevapla(
                mesajlar, model,
                tools=aktif_toollar if aktif_toollar else None,
                override_model=override)
        except Exception as e:
            hata_str = str(e)
            if "429" in hata_str or "rate" in hata_str.lower():
                js_callback("BasakUI.error(" + _j("Cok fazla istek, biraz bekle") + ")")
            else:
                js_callback("BasakUI.error(" + _j("Beyin hatasi: " + hata_str[:100]) + ")")
            return

        tool_calls = yanit.get("tool_calls")
        # Olcum Retry: tool_call donmediyse ve olcum sorusuysa, 1 kez tekrar dene
        if not tool_calls and olcum_aktif and _retry < MAX_RETRY:
            _retry += 1
            logger.info("Olcum retry #%d: tool_call alinamadi, guclu model deneniyor", _retry)
            continue
        break

    # tool_calls burada zaten yukarida atandi
    if not tool_calls:
        cevap = _temizle(yanit.get("content", ""))

        # Dil kontrolu: Karisik/Ingilizce cevap gelirse Turkce telkinle tekrar dene
        if cevap and _ingilizce_sizinti_mi(cevap):
            try:
                telkin = mesajlar + [{
                    "role": "system",
                    "content": "SADECE TURKCE yaz. Ingilizce kelime ve cumle kullanma.",
                }]
                yanit2, kaynak2 = brain.cevapla(telkin, model)
                icerik2 = yanit2.get("content", "") if isinstance(yanit2, dict) else yanit2
                cevap2 = _temizle(icerik2)
                if cevap2 and not _ingilizce_sizinti_mi(cevap2):
                    cevap = cevap2
                    kaynak = kaynak2 + " (dil duzeltme)"
            except Exception:
                pass
            # Telkin de tutmadiysa sizinti metnini KULLANICIYA VERME.
            if _ingilizce_sizinti_mi(cevap):
                logger.info("Ingilizce sizinti telkinden sonra da surdu")
                cevap = YEDEK_CUMLE

        # Çıkış kapısı (Ö-0): işaretsiz/uydurma cümle kullanıcıya gitmez
        cevap, _kapi = cikis_kapisi(cevap, olcumler=[])
        _save_and_reply(text, cevap, kaynak, gecmis, js_callback, speaker=aktif_konusmaci)
        return

    # YETKİ TAVANI: donguye SUZULMUŞ set girer — ham `tools` degil.
    # Ilk turda ne sunulduysa sonraki turlarda da o gorunur; model kendi
    # yetkisini genisletemez (2026-08-23'te Casper'in buldugu acik:
    # olcum-suzuguyle baslayan bir is ikinci turda write_file_tool,
    # deftere_kaydet, ac_uygulama gibi aracları gorebiliyordu).
    cevap, arac_ciktilari = _tool_calling_multi(
        tool_calls, mesajlar, brain, model, js_callback, calistir,
        aktif_toollar)
    cevap = _temizle(cevap)
    # Saglayici bazen kendi dusunme metnini cevap sanip gonderiyor
    # ("We need to answer..."). Dil kontrolu araciz yolda vardi, araclli
    # yolda YOKTU — sizinti buradan geciyordu (2026-08-23 olcumu).
    if cevap and _ingilizce_sizinti_mi(cevap):
        logger.info("Ingilizce sizinti: model cevabi atildi, ham olcum verildi")
        ham = ham_olcum_satirlari(arac_ciktilari)
        cevap = (HAM_BASLIK + "\n" + "\n".join(ham)) if ham else YEDEK_CUMLE
        _save_and_reply(text, cevap, kaynak, gecmis, js_callback,
                        speaker=aktif_konusmaci)
        return
    # Kapı araç çıktılarına karşı da denetler ([Ö] alıntısı birebir olmalı)
    cevap, _kapi = cikis_kapisi(cevap, olcumler=arac_ciktilari)
    # Kapi modelin butun cumlelerini elediyse kullaniciyi bos birakma:
    # olcum gercekten alindiysa ham halini KOD uretir (birebirligi kesin).
    if cevap.strip() == YEDEK_CUMLE:
        ham = ham_olcum_satirlari(arac_ciktilari)
        if ham:
            cevap = HAM_BASLIK + "\n" + "\n".join(ham)
    _save_and_reply(text, cevap, kaynak, gecmis, js_callback, speaker=aktif_konusmaci)


TUR_SINIRI = 3   # "sunu bul, sonra kaydet" gibi isler icin arac turu sayisi


def _tool_calling_multi(tool_calls, mesajlar, brain, model, js_callback,
                        calistir, tools=None, tur_siniri=TUR_SINIRI):
    """Tool sonuclarini modele geri gondererek anlamlil cevap uretir.

    Cok adimli isler icin DONGU: model sonucu gorduk ten sonra yeni bir arac
    isteyebilir ("araclari say" -> "deftere kaydet"). Eskiden tek tur vardi,
    bu yuzden ikinci adim hicbir zaman calismiyordu (2026-08-23 olcumu).
    Son turda arac verilmez ki dongu kapansin.

    YETKİ TAVANI: `tools` parametresi tavan setidir — tum turlarda YALNIZ
    bu set sunulur. Çağıran taraf (mesaj_isle) süzülmüş aktif_toollar
    verir; döngü seti asla büyütmez.

    Donus: (cevap_metni, arac_ciktilari) — ciktilar (arac_adi, metin)
    ciftleri olarak doner; cikis kapisi hem birebirligi hem ATFI denetler
    (cumle hangi araca dayandigini soyluyorsa alinti o aracin ciktisinda
    gecmeli).
    """
    tum_sonuclar = []
    expanded = list(mesajlar)

    for tur in range(tur_siniri):
        tur_sonuclari = []
        for call in tool_calls:
            func = call.get("function", {})
            tool_name = func.get("name", "")
            args = _parse_args(func.get("arguments", "{}"))
            js_callback("BasakUI.toolStatus(" + _j(
                TOOL_LABELS.get(tool_name, "Isleniyor...")) + ")")
            sonuc = calistir(tool_name, args, KNOWLEDGE_DIR, GOREVLER_FILE)
            net = _sonucu_donustur(tool_name, sonuc)
            tur_sonuclari.append((tool_name, net))

        expanded = expanded + [
            {"role": "assistant", "content": None, "tool_calls": tool_calls}]
        for i, (_isim, sonuc) in enumerate(tur_sonuclari):
            expanded.append({
                "role": "tool",
                "tool_call_id": tool_calls[i].get("id", "call_%d" % i),
                "content": sonuc,
            })
        tum_sonuclar.extend(tur_sonuclari)

        # Son turda arac verilmez: model artik cevabi yazmak zorunda.
        sonraki_araclar = tools if tur < tur_siniri - 1 else None
        try:
            son_yanit, _ = brain.cevapla(expanded, model,
                                         tools=sonraki_araclar)
        except Exception:
            break

        yeni_cagrilar = son_yanit.get("tool_calls")
        if yeni_cagrilar:
            tool_calls = yeni_cagrilar
            continue

        son_cevap = _temizle(son_yanit.get("content", ""))
        if son_cevap:
            return (son_cevap, tum_sonuclar)
        break

    return ("\n".join(sonuc for _, sonuc in tum_sonuclar), tum_sonuclar)


def _save_and_reply(text, cevap, kaynak, gecmis, js_callback, speaker=""):
    gecmis += [{"role": "user", "content": text, "oturum": OTURUM_ID},
               {"role": "assistant", "content": cevap, "oturum": OTURUM_ID}]
    kaydet(HISTORY_FILE, gecmis[-40:])
    js_callback("BasakUI.reply(" + _j(cevap) + ", " + _j(kaynak) + ")")
    # UI guncellendikten sonra ani kaydet — cevabi bekletmesin
    motor = _hafiza_al()
    if motor and cevap:
        try:
            motor.episodik_kaydet(text, cevap, speaker=speaker)
        except Exception as e:
            logger.warning("Ani kaydedilemedi: %s", e)


def _temizle_history(gecmis):
    temiz = []
    for m in gecmis:
        if m.get("role") == "assistant" and m.get("tool_calls"):
            temiz.append({"role": "assistant", "content": m.get("content", "")})
        else:
            # API'ye yalnızca role+content gider; oturum gibi yerel alanlar silinir
            temiz.append({"role": m.get("role"), "content": m.get("content", "")})
    return temiz


def _sonucu_donustur(tool_name, sonuc):
    if "error" in sonuc:
        return "Hata: " + sonuc["error"]
    return sonuc.get("result", "Islem tamamlandi.")


def _temizle(text):
    # Gelen content her türden olabilir (str, dict, None)
    if not text:
        return ""
    if not isinstance(text, str):
        # Dict ise content anahtarini al
        if isinstance(text, dict):
            text = text.get("content", str(text))
        else:
            text = str(text)
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
    threading.Thread(target=_hafiza_hazirla, daemon=True).start()


def _hafiza_hazirla():
    """Arka planda: eski gecmisi aktar, knowledge/ + Obsidian'i indeksle."""
    motor = _hafiza_al()
    if not motor:
        return
    try:
        from memory.engine import indeksle_klasor

        if not motor.meta_al("gecmis_aktarildi", False):
            _gecmisi_aktar(motor)
            motor.meta_koy("gecmis_aktarildi", True)

        n1 = indeksle_klasor(motor, KNOWLEDGE_DIR, "knowledge")
        n2 = indeksle_klasor(motor, OBSIDIAN_DIR, "obsidian")
        n3 = indeksle_klasor(motor, DEFTER_DIR, "defter")
        logger.info("Hafiza hazir: %d ani, indekleme +%d", motor.say(), n1 + n2 + n3)
    except Exception as e:
        logger.warning("Hafiza hazirlanamadi (sohbet etkilenmez): %s", e)


def _gecmisi_aktar(motor):
    """gecmis.json'daki eski sohbeti bir kereye mahsus episodic hafizaya tasir."""
    kayitlar = yukle(HISTORY_FILE, [])
    soru = None
    sayac = 0
    for m in kayitlar:
        rol = m.get("role")
        icerik = (m.get("content") or "").strip()
        if not icerik:
            continue
        if rol == "user":
            soru = icerik
        elif rol == "assistant" and soru:
            if motor.episodik_kaydet(soru, icerik):
                sayac += 1
            soru = None
    logger.info("Eski gecmis hafizaya tasindi: %d cift", sayac)


def _ilgili_anilar(sorgu, limit=4):
    """Soruyla ilgili anilari dondurur; motor/hata durumunda bos liste."""
    motor = _hafiza_al()
    if not motor:
        return []
    try:
        return motor.ara(sorgu, limit=limit)
    except Exception as e:
        logger.warning("Ani arama hatasi: %s", e)
        return []


def _j(obj):
    return json.dumps(obj, ensure_ascii=False)
