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
    """Ekranda 'neye bakıyorum' diye gostermek icin kisa detay.

    2026-09-09: kullanici 'okuduklari belli degil' dedi. Artik
    durum satirinda hangi klasor/dosya/sorgu okundugu yazar.
    Hassas icerik ASLA yazilmaz — yalniz isim/yol/sorgu.
    """
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
    """'Aranıyor... + sorgu' gibi ekrana giden durum metni."""
    etiket = TOOL_LABELS.get(tool_name, "İşleniyor...")
    detay = _arac_detay(tool_name, args)
    if detay:
        detay = str(detay)
        if len(detay) > 80:
            detay = detay[:80].rstrip() + "..."
        return "%s %s" % (etiket, detay)
    return etiket


def _yazma_koku():
    """Yazma karari icin kok dizin (executor ile ayni mantik)."""
    try:
        from tools.executor import ToolContext
        return ToolContext("", "").base_dir
    except Exception:
        return os.getcwd()


def _otomatik_yazma(args):
    """Hedef knowledge/research-engine ise True (onaysiz)."""
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
    """Guvenli alan disina yazma onayi. Donus: True/False.

    UI yoksa onay GELMEZ ve yazma yapilmaz — guvenli varsayilan REDDIR.
    """
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

TUR_SINIRI = 12  # 2026-08-25: 3'ten yukseltildi — cok adimli isler erken kesilmesin

# 2026-09-09 (tam tespit — Groq kelime duvari): arac sonuclari modele
# TAM boy gidiyordu (sayfa_oku 5000 harf, read_file sinirsiz). 12 tur
# birikince tek istek 9000+ kelime olup Groq'un dakikada 8000 duvarina
# carpiyordu (413 hatasi). Modele giden kopya kirpilir; tam sonuc
# tum_sonuclar'da saklanir, ekrana/ozete tam gider.
ARAC_SONUC_TAVAN = 1500


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
    tum_kaynaklar = []  # 2026-09-10: "nereden buldun" satiri icin adlar
    expanded = list(mesajlar)

    # Kapasiteye gore taban: kucuk modelde tavan dusuk, guclu modelde TUR_SINIRI
    from brain.kapasite import mod_kapasite
    mevcut_kaynaklar = [ad for ad, _ in brain._bulut_zinciri()] if hasattr(brain, "_bulut_zinciri") else []
    kap = mod_kapasite(kaynaklar=mevcut_kaynaklar)
    tavan = 3 if kap.kucuk else tur_siniri

    for tur in range(tavan):
        tur_sonuclari = []
        for call in tool_calls:
            func = call.get("function", {})
            tool_name = func.get("name", "")
            args = parse_args(func.get("arguments", "{}"))
            args = tool_argumani_duzelt(tool_name, args)
            # Bilinmeyen toollari sessizce atla (orn: terminal_calistir)
            if tool_name not in TANINMIS_TOOLLAR:
                logger.info("Bilinmeyen tool atlandi: %s", tool_name)
                continue
            # ONAY (2026-09-09, Casper karari): knowledge/ ve
            # research-engine/ disina yazmadan once Casper'a sorulur.
            # Ben de sormadan dokunmam — o da oyle yapar.
            if tool_name == "write_file_tool" and not _otomatik_yazma(args):
                if not _yazma_onayi(call, args, js_callback):
                    tur_sonuclari.append(
                        (tool_name, "Casper onaylamadı — yazılmadı."))
                    continue
            js_callback("BasakUI.toolStatus(" + json.dumps(
                _durum_metni(tool_name, args),
                ensure_ascii=False) + ")")

            sonuc = calistir(tool_name, args, knowledge_dir, gorevler_file)
            net = sonucu_donustur(tool_name, sonuc)
            tur_sonuclari.append((tool_name, net))
            if not net.startswith("Hata:"):
                detay = _arac_detay(tool_name, args)
                etiket = ("%s %s" % (tool_name, detay)).strip()
                if etiket and etiket not in tum_kaynaklar:
                    tum_kaynaklar.append(etiket)

        expanded = expanded + [
            {"role": "assistant", "content": "", "tool_calls": tool_calls}]
        for i, (_isim, sonuc) in enumerate(tur_sonuclari):
            # Modele kirpilmis kopya gider (kelime duvari); tam sonuc
            # tum_sonuclar'da durur.
            kirpilmis = sonuc
            if isinstance(sonuc, str) and len(sonuc) > ARAC_SONUC_TAVAN:
                kirpilmis = (sonuc[:ARAC_SONUC_TAVAN].rstrip()
                             + "... [devami kirpildi]")
            expanded.append({
                "role": "tool",
                "tool_call_id": tool_calls[i].get("id", "call_%d" % i),
                "content": kirpilmis,
            })
        tum_sonuclar.extend(tur_sonuclari)

        # Son turda arac verilmez; kucuk modelde yalniz ilk turda arac verilir
        sonraki_araclar = tools if (tur < tavan - 1 and kap.guclu) else None
        tool_sonuclari_text = "\n".join(
            "%s: %s" % (ad, net[:800]) for ad, net in tur_sonuclari)
        expanded = expanded + [{
            "role": "user",
            "content": (
                "Araç sonuçları:\n" + tool_sonuclari_text +
                "\n\nŞimdi bu sonuçları DOĞAL TÜRKÇE ile özetle. "
                "Kurallar:\n"
                "- Kullanıcı kısa ve okunaklı ister: 104 satırlık ham liste "
                "AYNEN YAZILMAZ. Önemli 5-10 madde seç, gerisini say "
                "('... ve 94 oge daha').\n"
                "- Sistem dosyaları (NTUSER, .cache, .config gibi nokta "
                "klasörler, AppData) liste AYNEN yazılmaz; bir cümleyle "
                "geç.\n"
                "- Kullanıcıya yararlı olanları öne al: belgeler, masaüstü, "
                "projeler, notlar.\n"
                "- Bicim: ayri konulari ## baslikla ayir, listeleri - ile "
                "madde yap, onemli adlari **kalin** yaz. Emoji/simge yok.\n"
                "- Sonunda bir sonraki adimi teklif et ('Hangisine "
                "bakayim?').\n"
                "- Gördüğün şeyi UYDURMA; sadece elindeki sonuçta yazan var."
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
            return (_kaynak_satiri_ekle(son_cevap, tum_kaynaklar),
                    tum_sonuclar)
        break

    # FALLBACK (2026-09-10, birinci ders): model ozet uretmediyse ham
    # cikti aynen basilmaz — 104 ogelik liste okunamaz. Ozetleyici devreye
    # girer: sistem curufunu eler, 10 oge gosterir, devamini teklif eder.
    ham_metin = "\n".join(
        str(net) for _ad, net in tum_sonuclar if net)
    return (_ham_listeyi_ozetle(ham_metin), tum_sonuclar)

def _ham_listeyi_ozetle(ham_metin):
    """Model ozet uretmediginde ham arac ciktisini insan diline cevirir.

    Ozellikle klasor listesi icin: sistem dosyalarini eler, en onemli
    10 ogeyi baslik+madde olarak gosterir, gerisini sayar, devam teklif eder.
    Liste degilse kisa kesip aynen doner.
    """
    metin = (ham_metin or "").strip()
    if not metin:
        return "Suctan bir sey cikmadi. Baska dener misin?"
    satirlar = [s.strip() for s in metin.split("\n") if s.strip()]
    liste_mi = any(("(klas" in s.lower()) or ("bayt" in s.lower())
                   for s in satirlar)
    if not liste_mi:
        kisa = metin[:600].rstrip()
        return kisa + ("..." if len(metin) > 600 else "")

    # Baslik: "C:\Users\Casper/ (104 ogе):" seklinde gelir
    baslik = satirlar[0] if satirlar else ""
    ogeler = satirlar[1:]
    m = re.search(r"\((\d+)\s*oge", baslik, re.IGNORECASE)
    toplam = int(m.group(1)) if m else len(ogeler)

    GIZLI = (
        "ntuser", ".tm.", ".regtrans", "application data", "cookies",
        "local settings", "nethood", "printhood", "recent", "sendto",
        "start menu", "searches", "saved games", "favorites", "links",
        "contacts", "templates", "printhood",
    )
    NOKTA = (".agents", ".aider", ".android", ".antigravity", ".bun",
             ".cache", ".claude", ".cline", ".codeium", ".codex",
             ".config", ".copilot", ".cursor", ".devin", ".docker",
             ".dsh", ".expo", ".gemini", ".gradle", ".kimi", ".kiro",
             ".local", ".ollama", ".omniroute", ".paddlex",
             ".pytest_cache", ".sbx", ".semantic", ".supabase",
             ".vscode", ".webui")
    ONEMLI = ("vixrex", "source", "src", "obsidian", "onedrive",
              "documents", "downloads", "desktop", "pictures",
              "supabase", "tool", "goose", "jarvis", "studio")

    def _ad(o):
        return o.split(" (")[0].strip().lstrip("-• ").strip()

    temiz = []
    for o in ogeler:
        a = _ad(o).lower()
        if not a or a.startswith("ntuser") or a.endswith(".blf"):
            continue
        if any(k in a for k in GIZLI):
            continue
        if a.startswith(".") and any(a.startswith(k) for k in NOKTA):
            continue
        temiz.append(o)
    temiz.sort(key=lambda s: (0 if any(k in _ad(s).lower()
                                       for k in ONEMLI) else 1,
                              _ad(s).lower()))

    goster = temiz[:10]
    kalan = max(0, len(temiz) - len(goster))
    klasor = baslik.split("/")[0].split("(")[0].strip().rstrip("\\/") or "klasor"
    satir = ["## " + klasor + " — one cikanlar"]
    for g in goster:
        kls = " (klasor)" if "(klas" in g.lower() else ""
        satir.append("- **" + _ad(g) + "**" + kls)
    if kalan > 0:
        satir.append("- ... ve **" + str(kalan) + " oge** daha")
    satir.append("")
    satir.append("Hangisine bakayim?")
    return "\n".join(satir)





def _kaynak_satiri_ekle(cevap, kaynaklar):
    """Arac kullanildiysa sonuna 'Kaynaklar: ...' satiri ekler.

    2026-09-10 (Casper): 'sunu nereden buldun' belli olsun. Yalniz
    isim/yol yazilir, icerik tekrarlanmaz. Arac yoksa metin aynen doner.
    """
    if not kaynaklar:
        return cevap
    satir = "\n\nKaynaklar: " + "; ".join(kaynaklar[:5])
    if len(kaynaklar) > 5:
        satir += " (+%d kaynak daha)" % (len(kaynaklar) - 5)
    return (cevap or "").rstrip() + satir


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
