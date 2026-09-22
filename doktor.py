"""doktor.py - Basak ortam saglik kontrolu (tek komut, kod degistirmez).

    python doktor.py            # cevrimdisi kontrol; kota harcamaz
    python doktor.py --canli    # + 1 gercek beyin cagrisi (KOTA HARCAR)

Amac: yeni bir makinede "Basak neden konusmuyor?" sorusunu README okumadan
cevaplamak. Cikti ASCII'dir (Windows konsolu Turkce karakterlerde
patlamasin) ve SIR YAZDIRMAZ - yalnizca anahtarin var/yok durumu gorunur.

Cikis kodu: 0 = hata yok, 1 = en az bir HATA var.
"""

import importlib.util
import json
import os
import sys

BASE = os.path.dirname(os.path.abspath(__file__))
if BASE not in sys.path:
    sys.path.insert(0, BASE)

OK, UYARI, HATA = "OK", "UYARI", "HATA"
_ETIKET = {OK: "[OK]", UYARI: "[!!]", HATA: "[XX]"}

# ── paketler ──────────────────────────────────────────────────────────
# Zorunlu: metin sohbeti bunlar olmadan ACILMAZ.
ZORUNLU_PAKETLER = (
    ("openai", "openai"),
    ("requests", "requests"),
    ("webview", "pywebview"),
    ("numpy", "numpy"),
    ("ddgs", "ddgs"),
)
# Opsiyonel: ilgili ozellik sessizce kapanir, sohbet yasar.
OPSIYONEL_PAKETLER = (
    ("cohere", "cohere"),
    ("sqlite_vec", "sqlite-vec"),
    ("PIL", "Pillow"),
    ("pystray", "pystray"),
    ("piper", "piper-tts"),
    ("sounddevice", "sounddevice"),
    ("soundfile", "soundfile"),
    ("faster_whisper", "faster-whisper"),
    ("telegram", "python-telegram-bot"),
    ("pyannote.audio", "pyannote.audio"),
)

# ── ayar alanlari ─────────────────────────────────────────────────────
# DIKKAT: adaptorlar ve uygulama bu alanlari UST SEVIYEDEN okur
# (ayar.get("mistral_key") gibi). Ic ice bir '_' grubuna yazilan ayni ad
# kodu HIC gormez - ayarlar.ornek.json 2026-09-22'ye kadar tam bu hatayi
# yapiyordu. Sozluk anahtar listesi oldugu icin test de bunu bekcisi yapar.
ANAHTAR_ALANLARI = (
    "groq_key", "gemini_key", "openrouter_key", "zai_key", "nvidia_key",
    "kilo_key", "cloudflare_account_id", "cloudflare_api_token",
    "cohere_key", "mistral_key", "hf_token", "chutes_key",
)
AYAR_ALANLARI = ANAHTAR_ALANLARI + (
    "glm_model", "groq_model", "tts_on", "yerel_goru_kapali",
)

SES_MODELI_ADI = "tr_TR-dfki-medium.onnx"


def _dolu(deger):
    """Alan gercekten doldurulmus mu? Bayrak (bool) anahtar sayilmaz."""
    if isinstance(deger, bool) or deger is None:
        return False
    if isinstance(deger, str):
        return bool(deger.strip())
    return bool(deger)


def _var_mi(modul):
    """Paket kurulu mu? Import ETMEZ (find_spec hizli ve yan etkisiz)."""
    try:
        return importlib.util.find_spec(modul) is not None
    except (ImportError, ValueError, ModuleNotFoundError):
        return False


def ayar_yukle(yol):
    """ayarlar.json'u BOM'a dayanikli okur; yok/bozuksa {} doner."""
    try:
        with open(yol, "r", encoding="utf-8-sig") as f:
            veri = json.load(f)
        return veri if isinstance(veri, dict) else {}
    except (OSError, json.JSONDecodeError):
        return {}


def ic_ice_alanlar(veri):
    """Ic ice sozluklerde duran ayar alanlarini bulur.

    Donus: [(grup_adi, alan_adi), ...] - kod bu alanlari OKUMAZ.
    """
    bulunan = []
    if not isinstance(veri, dict):
        return bulunan
    for anahtar, deger in veri.items():
        if not isinstance(deger, dict):
            continue
        for ad in AYAR_ALANLARI:
            if ad in deger:
                bulunan.append((anahtar, ad))
        bulunan.extend(ic_ice_alanlar(deger))
    return bulunan


# ── kontroller ────────────────────────────────────────────────────────

def kontrol_python():
    surum = "%d.%d.%d" % sys.version_info[:3]
    if sys.version_info[:2] == (3, 12):
        return [(OK, "Python", surum)]
    if (3, 10) <= sys.version_info[:2] < (3, 14):
        return [(UYARI, "Python", "%s - onerilen 3.12" % surum)]
    return [(HATA, "Python", "%s - 3.10-3.13 gerekli" % surum)]


def kontrol_paketler():
    sonuc = []
    eksik_z = [ad for m, ad in ZORUNLU_PAKETLER if not _var_mi(m)]
    if eksik_z:
        sonuc.append((HATA, "Paketler (zorunlu)",
                      "eksik: %s - kur: pip install -r requirements.txt"
                      % ", ".join(eksik_z)))
    else:
        sonuc.append((OK, "Paketler (zorunlu)",
                      "%d/%d yerinde" % (len(ZORUNLU_PAKETLER),
                                         len(ZORUNLU_PAKETLER))))
    eksik_o = [ad for m, ad in OPSIYONEL_PAKETLER if not _var_mi(m)]
    if eksik_o:
        sonuc.append((UYARI, "Paketler (opsiyonel)",
                      "eksik: %s - ilgili ozellik sessiz kalir"
                      % ", ".join(eksik_o)))
    return sonuc


def kontrol_ayarlar(ayar_yolu):
    """Dosya var mi + dolu anahtarlar + ic ice gruba sikismis alanlar."""
    if not os.path.exists(ayar_yolu):
        return [(HATA, "ayarlar.json",
                 "yok - duzelt: ayarlar.ornek.json'i kopyala")]
    ayar = ayar_yukle(ayar_yolu)
    if not ayar:
        return [(HATA, "ayarlar.json", "okunamadi veya bozuk JSON")]

    sonuc = []
    gomulu = ic_ice_alanlar(ayar)
    if gomulu:
        adlar = sorted({ad for _, ad in gomulu})
        gruplar = sorted({g for g, _ in gomulu})
        sonuc.append((HATA, "ayarlar.json (ic ice)",
                      "su alanlar '%s' grubunda duruyor; kod UST SEVIYEDEN "
                      "okur, yani YOK SAYILIR: %s"
                      % (", ".join(gruplar), ", ".join(adlar))))

    dolu_anahtar = [ad for ad in ANAHTAR_ALANLARI if _dolu(ayar.get(ad))]
    if dolu_anahtar:
        sonuc.append((OK, "Anahtarlar",
                      "%d dolu: %s" % (len(dolu_anahtar),
                                       ", ".join(dolu_anahtar))))
    else:
        sonuc.append((UYARI, "Anahtarlar",
                      "hicbir saglayici anahtari yok - yalniz anahtarsiz "
                      "yollarla (kilo) denenir"))
    return sonuc


def kontrol_ses_modeli(kok):
    onnx = os.path.join(kok, SES_MODELI_ADI)
    sozluk = onnx + ".json"
    eksik = [os.path.basename(y) for y in (onnx, sozluk)
             if not os.path.exists(y)]
    if eksik:
        return [(UYARI, "Ses modeli",
                 "eksik: %s - Basak KONUSMAZ (README 3.4)"
                 % ", ".join(eksik))]
    mb = os.path.getsize(onnx) / (1024 * 1024)
    return [(OK, "Ses modeli", "%s (%.0f MB)" % (SES_MODELI_ADI, mb))]


def kontrol_veri_klasoru(kok):
    # 2026-09-23: kisi koku chat.kimlik ile (tasima sonrasi
    # state_kok/kisi/memory): BASAK_STATE_DIR yoksa <kok>/data.
    try:
        from chat.kimlik import aktif_kullanici
        kisi = aktif_kullanici()
    except Exception:
        kisi = "casper"  # kimlik bozuksa doktor yine de kendi isini yapsin
    temel = os.environ.get("BASAK_STATE_DIR") or os.path.join(kok, "data")
    hedef = os.path.join(temel, kisi, "memory")
    try:
        os.makedirs(hedef, exist_ok=True)
        deneme = os.path.join(hedef, ".doktor-yazma-testi")
        with open(deneme, "w", encoding="utf-8") as f:
            f.write("ok")
        os.remove(deneme)
    except OSError as e:
        return [(HATA, "Veri klasoru", "%s - %s" % (hedef, e))]
    return [(OK, "Veri klasoru", hedef)]


def kontrol_hafiza(kok):
    try:
        from memory.engine import HafizaMotoru
        # 2026-09-23: tek kisilik tasima sonrasi yol data/casper/ altinda.
        motor = HafizaMotoru(db_yolu=os.path.join(kok, "data", "casper",
                                                  "memory", "basak.db"))
        try:
            sayi = motor.say()
            vektor = "acik" if getattr(motor, "vektor_var", False) else "kapali"
        finally:
            motor.kapat()
    except Exception as e:
        return [(UYARI, "Hafiza DB", "acilamadi: %s" % str(e)[:60])]
    return [(OK, "Hafiza DB",
             "%d kayit | anlam aramasi %s (kapaliysa BM25)" % (sayi, vektor))]


def kontrol_beyin(brain=None):
    """Gercek zinciri kurar - hangi saglayicilar HAZIR, tahmin etmeden."""
    try:
        if brain is None:
            from brain.brain import Brain
            brain = Brain()
        adlar = [ad for ad, _ in brain._bulut_zinciri()]
    except Exception as e:
        return [(HATA, "Beyin zinciri", "kurulamadi: %s" % str(e)[:60])]
    if not adlar:
        return [(HATA, "Beyin zinciri",
                 "hicbir saglayici yok - ayarlar.json'a bir anahtar yaz")]
    return [(OK, "Beyin zinciri",
             "%d saglayici: %s" % (len(adlar), ", ".join(adlar)))]


def kontrol_canli(brain=None):
    """Tek gercek cagri: anahtarlar gercekten calisiyor mu? KOTA HARCAR."""
    try:
        if brain is None:
            from brain.brain import Brain
            brain = Brain()
        yanit, kaynak = brain.cevapla(
            [{"role": "user", "content": "Tek kelimeyle cevap ver: merhaba"}])
        metin = yanit.get("content") if isinstance(yanit, dict) else yanit
        metin = (metin or "").strip()
        if metin:
            return [(OK, "Canli cagri",
                     "kaynak=%s | %s" % (kaynak, metin[:40]))]
        return [(UYARI, "Canli cagri", "bos cevap (kaynak=%s)" % kaynak)]
    except Exception as e:
        return [(HATA, "Canli cagri", str(e)[:80])]


def calistir(kok=None, canli=False, brain=None):
    """Tum kontrolleri kosar; [(durum, ad, detay), ...] doner."""
    kok = kok or BASE
    satirlar = []
    satirlar += kontrol_python()
    satirlar += kontrol_paketler()
    satirlar += kontrol_ayarlar(os.path.join(kok, "ayarlar.json"))
    satirlar += kontrol_ses_modeli(kok)
    satirlar += kontrol_veri_klasoru(kok)
    satirlar += kontrol_hafiza(kok)
    satirlar += kontrol_beyin(brain)
    if canli:
        satirlar += kontrol_canli(brain)
    return satirlar


def _yaz(metin):
    """Windows konsolu Turkce karakterde patlamasin."""
    try:
        print(metin, flush=True)
    except UnicodeEncodeError:
        print(metin.encode("ascii", "replace").decode("ascii"), flush=True)


def main(argv=None):
    argv = list(sys.argv[1:] if argv is None else argv)
    canli = "--canli" in argv
    _yaz("Basak ortam kontrolu")
    _yaz("")
    satirlar = calistir(canli=canli)
    for durum, ad, detay in satirlar:
        _yaz("%-4s %-20s %s" % (_ETIKET[durum], ad, detay))
    hata = sum(1 for d, _, _ in satirlar if d == HATA)
    uyari = sum(1 for d, _, _ in satirlar if d == UYARI)
    _yaz("")
    _yaz("OZET: %d kontrol · %d hata · %d uyari" % (len(satirlar), hata,
                                                    uyari))
    if not canli:
        _yaz("(Kota harcayan anahtar testi icin: python doktor.py --canli)")
    return 1 if hata else 0


if __name__ == "__main__":
    sys.exit(main())
