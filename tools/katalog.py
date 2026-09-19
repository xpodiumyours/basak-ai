"""tools/katalog.py — Fatura fotoğrafından Vixrex'e hazır katalog.

Esnaf fatura / satış teklif formu fotoğrafı gönderir; bulut görü
(image_analyzer) yazıya döker; bu modül satırları doğrular, aynı
ürünün beden/renklerini tek kartta birleştirir ve Vixrex'in toplu
yükleme biçiminde dosya çıktısı üretir.

Vixrex'e YAZMA YOK — yalnız dosya çıktısı; aktarım ayrı aşamadır.
Resmi kaynak eşleştirmesi bu sürümde yok: image_urls boş çıkar,
alanı rezerve eder (eslesme_adayi F6 iskelesidir, ağa çıkmaz).

Klasörler (hepsi .gitignore'da, kişisel veri):
  data/gelen/    — yüklenen fatura fotoğrafları (staging)
  data/katalog/  — katalog işleri (<is_id>.json) + çıktılar (<is_id>/)
  data/yetki/    — üretici kullanım izni belgeleri

Eşzamanlılık: tools/tasks.py deseni — _KILIT + _atomik_yaz.
"""

import base64
import binascii
import csv
import io
import json
import logging
import os
import re
import threading
import time

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
GELEN_KOK = os.path.join(BASE, "data", "gelen")
KATALOG_KOK = os.path.join(BASE, "data", "katalog")
YETKI_KOK = os.path.join(BASE, "data", "yetki")

_KILIT = threading.Lock()

# Fatura fotoğrafı sınırları (image_analyzer ile aynı: 10MB).
# PDF staging'e KABUL EDILMEZ (fail-fast): fatura_oku PDF okuyamaz;
# dosya staging'de bekleyip hatta bir adim sonra patlamasin.
DESTEK_UZANTI = (".jpg", ".jpeg", ".png", ".webp", ".gif", ".bmp",
                 ".tiff")
MAX_BOYUT = 10 * 1024 * 1024

# Belge uzantıları
DESTEK_BELGE = (".jpg", ".jpeg", ".png", ".webp", ".pdf")

# Vixrex toplu yükleme CSV başlığı — birebir aynı olmalı
# (vixrex bulk_product_upload_service.dart generateTemplateCsv).
CSV_BASLIK = ["Ürün Adı", "Fiyat", "Açıklama", "Kategori",
              "Stok Durumu", "Görsel URL"]

# Stok etiketleri — Vixrex StockStatus label'ları ile birebir aynı.
STOK_VAR = "Mevcut"
STOK_BITTI = "Tükendi"
STOK_AZ = "Son birkaç adet"

# Çıktı dosya adları (sabit; cikti_oku beyaz listesiyle aynı)
DOSYA_CSV = "vixrex_urunler.csv"
DOSYA_BATCH = "vixrex_batch.json"
DOSYA_KATALOG = "basak_katalog.json"

# Görüntüye sorulacak soru (nötr; türü model belirler).
# Bu bir fatura/satış formu fotoğrafı olabilir, genel bir belge,
# ürün fotoğrafı veya başka bir görsel. Model içeriği okur,
# satırların üzerinde durur ve okuyamadığı yeri uydurma, boş bırakır.
# 2026-09-18 olcumu: omni-reasoning modeli aciklamaya dusunce
# metniyle basliyordu ("The user wants me..."); cikti bicimini
# tarif edince ("yalniz yazinin kendisi") tablo metni geldi.
# Bu, araca ne donecegini soyler (ne yapacagina karismaz).
GORUNTU_SORUSU = (
    "Bu fotoğraf/iş dosyasındaki TÜM yazıyı satır satır aynen yaz. "
    "Açıklama yapma, yorum ekleme, düşünceni yazma — yalnız "
    "fotoğraftaki yazının kendisi olsun. "
    "Tablo varsa her satırı ayrı satıra yaz; sayıları ve kodları "
    "olduğu gibi kopyala. "
    "Okuyamadığın yeri uydurma, boş bırak. "
    "Bir ürün/fatura/satış formu tablosu gibi görünüyorsa "
    "Model, Stok (ürün adı), Barkod, Varyant, Beden, Miktar (adet), "
    "Fiyat gibi sütunları da yazar."
)

_BARKOD_RE = re.compile(r"\d{8,14}")
_BEDEN_RE = re.compile(
    r"\b(XXXL|XXL|XXS|XS|S|M|L|XL|[34][0-9]|4[0-8])\b")
_FIYAT_RE = re.compile(
    r"(\d{1,3}(?:[.\s]\d{3})+,\d{2,4}|\d+,\d{2,4}|\d+\.\d{2}|\d+)"
    r"\s*(TL|₺|TRY)?", re.IGNORECASE)
_ID_RE = re.compile(r"[A-Za-z0-9_-]{1,64}\Z")


def _j(veri):
    return json.dumps(veri, ensure_ascii=False)


def _simdi():
    return time.strftime("%Y-%m-%d %H:%M:%S")


def _id(onek):
    return "%s_%s_%04d" % (onek, time.strftime("%Y%m%d%H%M%S"),
                           os.getpid() % 10000)


def _kok_hazirla(kok):
    try:
        os.makedirs(kok, exist_ok=True)
    except OSError as e:
        logger.warning("Klasor acilamadi (%s): %s", kok, e)


def _guvenli_id(deger):
    """Staging/katalog kimliği mi? Yol ayracı ve .. barındıramaz."""
    return bool(deger) and bool(_ID_RE.fullmatch(str(deger)))


def _atomik_yaz(yol, veri):
    gecici = yol + ".tmp"
    with open(gecici, "w", encoding="utf-8") as f:
        json.dump(veri, f, ensure_ascii=False, indent=2)
    os.replace(gecici, yol)


def _yukle_json(yol):
    with open(yol, "r", encoding="utf-8-sig") as f:
        return json.load(f)


# ── Fiyat ─────────────────────────────────────────────────────────

def fiyat_coz(ham):
    """Türkçe fiyat metnini sayıya çevirir.

    "1.250,50 TL" → 1250.5 ; "75,0000 TL" → 75.0 ; 125 → 125.0 ;
    "" → (None, None). Çözülemezse (None, uyari_metni) döner;
    istisna fırlatmaz. Rakam arası boşluk ("1 63,5000") düzine
    sütunu bulaşması olabilir — yanlış sayı yerine hata döner.
    """
    if ham is None or (isinstance(ham, str) and not ham.strip()):
        return None, None
    if isinstance(ham, bool):
        return None, "fiyat sayı olmalı: '%s'" % ham
    if isinstance(ham, (int, float)):
        deger = float(ham)
        if deger < 0:
            return None, "fiyat eksi olamaz: '%s'" % ham
        return deger, None
    metin = str(ham).strip()
    temiz = re.sub(r"(?i)\b(TL|TRY|₺)\b", "", metin).strip()
    if re.search(r"\d\s+\d", temiz):
        return None, "fiyat okunamadı (sütun bulaşması): '%s'" % metin[:40]
    temiz = re.sub(r"\s+", "", temiz)
    if not temiz:
        return None, None
    eslesme = re.fullmatch(r"(\d{1,3}(?:\.\d{3})*|\d+)(,\d{1,4})?",
                           temiz)
    noktali = re.fullmatch(r"(\d{1,3}(?:,\d{3})*|\d+)(\.\d{1,4})?",
                           temiz)
    try:
        if eslesme:
            tam, ondalik = eslesme.groups()
            tam = tam.replace(".", "")
            sayi = float(tam + (ondalik or "").replace(",", "."))
        elif noktali:
            tam, ondalik = noktali.groups()
            tam = tam.replace(",", "")
            sayi = float(tam + (ondalik or ""))
        else:
            return None, "fiyat okunamadı: '%s'" % metin[:40]
    except ValueError:
        return None, "fiyat okunamadı: '%s'" % metin[:40]
    if sayi < 0:
        return None, "fiyat eksi olamaz: '%s'" % metin[:40]
    return sayi, None


def fiyat_yaz(deger):
    """Vixrex CSV biçimi: tam sayıysa düz, değilse iki ondalık."""
    if deger is None:
        return ""
    if float(deger).is_integer():
        return str(int(deger))
    return "%.2f" % deger


# ── Normalleştirme ────────────────────────────────────────────────

def kodu_normla(kod):
    """Grup anahtarı: büyük harf, ayraçlar tek çizgiye iner."""
    norm = re.sub(r"[\s_./]+", "-", str(kod or "").strip().upper())
    return re.sub(r"-{2,}", "-", norm).strip("-")


def beden_normla(beden):
    return str(beden or "").strip().upper()


def _tr_duzelt(metin):
    """Noktalı İ'yi ASCII i'ye indirir (lower() bozmasın diye)."""
    return str(metin or "").replace("İ", "i")


def renk_normla(renk):
    return _tr_duzelt(renk).strip().lower()


def _ean_saglama(rakam):
    """GTIN sağlama hanesi tutuyor mu? (8/12/13/14 hane)"""
    agirlik = [3, 1] * 7 if len(rakam) % 2 == 0 else [1, 3] * 6 + [1]
    toplam = sum(int(c) * a for c, a in zip(rakam, agirlik))
    return toplam % 10 == 0


def barkod_dogrula(barkod):
    """EAN-8/12/13/14 biçimi mi? Sağlama hanesi tutmazsa uyarı verir."""
    if barkod is None or not str(barkod).strip():
        return None, None
    rakam = re.sub(r"\D", "", str(barkod))
    if len(rakam) in (8, 12, 13, 14):
        if not _ean_saglama(rakam):
            return rakam, ("barkod sağlaması tutmadı, rakamı fişten "
                           "kontrol et: '%s'" % rakam)
        return rakam, None
    return None, "barkod biçimi tanınmadı: '%s'" % str(barkod)[:20]


def varyant_renk(varyant):
    """Tutku Varyant sütunundan renk adı çıkarır.

    "100 BEYAZ" → "Beyaz" ; "750 SIYAH" → "Siyah" ;
    "975 KOMBİN" → "Kombin". Baştaki renk kodunu atar, kalanı
    baş harfi büyük yazıya çevirir. Renk yoksa "" döner.
    """
    parcalar = str(varyant or "").strip().split()
    adlar = [p for p in parcalar if not p.isdigit()]
    if not adlar:
        return ""
    renk = _tr_duzelt(" ".join(adlar))
    return renk[:1].upper() + renk[1:].lower() if renk else ""


# ── Toptancı jargonu sözlüğü ─────────────────────────────────────
# Fişteki kısaltmalar temiz Türkçe'ye çözülür. Yalnız BİLİNEN
# kısaltmalar değişir; bilinmeyen kelime fişteki haliyle kalır
# (veri uydurulmaz). Model kodları (ELT1301) dokunulmaz — sözlük
# yalnız bu anahtarlarla kelime kelime eşleşir.
JARGON_SOZLUGU = {
    "ERK": "Erkek",
    "ERKEK": "Erkek",
    "BYN": "Kadın",
    "BAYAN": "Kadın",
    "PEN": "Penye",
    "PENYE": "Penye",
    "SIFIRYAKA": "Sıfır Yaka",
    "UZUNKOL": "Uzun Kol",
    "KASKORSE": "Kaşkorse",
    "LICRALI": "Likralı",
    "DUZ": "Düz",
    "TUT": "Tut",
    "ATLET": "Atlet",
    "BOXER": "Boxer",
    "TISORT": "Tişört",
    # ── OCR yamulmaları (özellikle küçük vision modelleri) ──────
    # Canlı probda (2026-09-18, qwen2.5vl:3b) ölçülen gerçek hatalar:
    # LZUNKOL→UZUNKOL (U harfi L okundu), SINAR→SİYAH,
    # LORALI→LİCRALI, KALI→DÜZ, RANDORI→PANDORA,
    # ENSEMILI→DESENLİ.
    "LZUNKOL": "Uzun Kol",
    "LORALI": "Likralı",
    "SINAR": "SİYAH",
    "KALI": "Düz",
    "RANDORI": "Pandora",
    "ENSEMILI": "Desenli",
}

_JARGON_RE = re.compile(
    r"\b(%s)\b" % "|".join(
        re.escape(k) for k in sorted(JARGON_SOZLUGU, key=len,
                                     reverse=True)),
    re.IGNORECASE)


def jargon_coz(metin):
    """Fiş jargonunu sözlükten temiz Türkçe'ye çözer.

    "ELIT ERK PENYE ATLET" → "ELIT Erkek Penye Atlet".
    Kelime sınırıyla eşleşir; ELT1301 gibi kodlar zarar görmez.
    """
    s = str(metin or "")
    if not s:
        return s

    def _cevir(m):
        anahtar = _tr_duzelt(m.group(0)).upper()
        return JARGON_SOZLUGU.get(anahtar, m.group(0))

    return _JARGON_RE.sub(_cevir, s)


# ── Staging: fatura fotoğrafı kaydı ───────────────────────────────

def _staging_kaydet(ham, ad):
    """Ham baytı data/gelen/ altına yazar. Dönüş: dict (result/error)."""
    if not ham:
        return {"error": "Dosya boş."}
    if len(ham) > MAX_BOYUT:
        return {"error": "Dosya çok büyük (en fazla 10MB)."}
    uzanti = os.path.splitext(str(ad or ""))[1].lower()
    if uzanti not in DESTEK_UZANTI:
        if uzanti == ".pdf":
            return {"error": ("PDF okuma bu sürümde yok; "
                              "faturanın fotoğrafını gönder.")}
        return {"error": ("Desteklenmeyen dosya: '%s'. " % uzanti
                          + "Fotoğraf (jpg/png/webp) gönder.")}
    _kok_hazirla(GELEN_KOK)
    fatura_id = _id("gln")
    dosya = fatura_id + uzanti
    try:
        with _KILIT:
            with open(os.path.join(GELEN_KOK, dosya), "wb") as f:
                f.write(ham)
    except OSError as e:
        logger.warning("Fatura yazilamadi: %s", e)
        return {"error": "Dosya saklanamadı."}
    return {"result": _j({"fatura_id": fatura_id, "dosya": dosya,
                          "boyut": len(ham)})}


def fatura_kaydet_b64(b64_veri, ad):
    """Base64 fatura fotoğrafı/belgesi kaydeder (UI ve Telegram girişi)."""
    if not b64_veri or not str(b64_veri).strip():
        return {"error": "Dosya verisi boş."}
    govde = str(b64_veri)
    if "," in govde and govde.startswith("data:"):
        govde = govde.split(",", 1)[1]
    try:
        ham = base64.b64decode(govde, validate=True)
    except (binascii.Error, ValueError):
        return {"error": "Dosya verisi bozuk (base64 çözülmedi)."}
    return _staging_kaydet(ham, ad)


def _fatura_yolu(fatura_id):
    if not _guvenli_id(fatura_id):
        return None
    try:
        adaylar = [d for d in os.listdir(GELEN_KOK)
                   if d.startswith(str(fatura_id) + ".")]
    except OSError:
        return None
    if len(adaylar) != 1:
        return None
    yol = os.path.realpath(os.path.join(GELEN_KOK, adaylar[0]))
    kok = os.path.realpath(GELEN_KOK)
    if os.path.commonpath([yol, kok]) != kok:
        return None
    return yol


# ── F2: fatura okuma (bulut görü + aday çıkarım) ──────────────────

def _aday_satirlar(yazi):
    """OCR metninden kaba adaylar: barkod/fiyat/beden geçen satırlar.

    Satir TAM verilir (kesme yok); 200 karakteri asan modelin
    göreceği `kesildi` bayrağı taşınır.
    """
    adaylar = []
    for satir in (yazi or "").splitlines():
        s = satir.strip()
        if len(s) < 3:
            continue
        barkodlar = _BARKOD_RE.findall(s)
        fiyatlar = [m.group(0).strip()
                    for m in _FIYAT_RE.finditer(s)]
        bedenler = _BEDEN_RE.findall(s.upper())
        if barkodlar or fiyatlar or bedenler:
            adaylar.append({"satir": s, "kesildi": len(s) > 200,
                            "barkodlar": barkodlar,
                            "fiyatlar": fiyatlar, "bedenler": bedenler})
    return adaylar


_GECICI_HATA = ("503", "429", "timed out", "timeout", "connection",
                "overloaded", "try again", "rate")


def _gecici_mi(hata):
    h = str(hata or "").lower()
    return any(k in h for k in _GECICI_HATA)


def _ustbilgi_cikar(yazi):
    """OCR metninden fiş üst bilgilerini kurallarla çıkarır.

    Fiş no, tarih, satıcı firma, KDV, toplam. Bulunamayan alan
    hiç yazılmaz (uydurma yok); model bunları esnafa sorar.
    Desenler Tutku tipi Satış Teklif Form dökümlerine göredir;
    uymayan fişte alanlar boş kalır, satır verisi etkilenmez.
    """
    ust = {}
    if not yazi:
        return ust
    m = re.search(r"Fi[şs]\s*No\s*[:.]?\s*([0-9][0-9.]{6,24})", yazi)
    if m:
        ust["fis_no"] = m.group(1).strip()
    m = re.search(r"(?:Fi[şs]\s*|Fatura\s*)Tarihi\s*[:.]?\s*"
                  r"(\d{1,2}[.\/]\d{1,2}[.\/]\d{2,4})", yazi)
    if m:
        ust["tarih"] = m.group(1)
    if not ust.get("tarih"):
        m = re.search(r"(\d{1,2}[.\/]\d{1,2}[.\/]\d{2,4})\s+\d{1,2}:\d{2}",
                      yazi)
        if m:
            ust["tarih"] = m.group(1)
    m = re.search(r"(?:İrsaliye\s*Firma|Firma)\s*[:.]?\s*"
                  r"([^\r\n]{3,80})", yazi)
    if m:
        aday = m.group(1).strip().rstrip(".")
        if len(aday) >= 3:
            ust["firma"] = aday
    m = re.search(r"KDV\s*[(%]?\s*(\d{1,2})\s*[%)]?", yazi, re.IGNORECASE)
    if m:
        ust["kdv_oran"] = int(m.group(1))
    m = re.search(
        r"Toplam\s*[:.]?\s*(?:\d+\s*ad\s*\d+\s*dz)?\s*"
        r"(\d{1,3}(?:[.,]\d{3})*[.,]\d{2})\s*(?:TL|₺|TRY)?", yazi)
    if m:
        tutar, _uy = fiyat_coz(m.group(1))
        if tutar is not None:
            ust["toplam"] = tutar
    m = re.search(r"(\d+)\s*ad\s+(\d+)\s*dz", yazi)
    if m:
        ust["adet"] = int(m.group(1))
        ust["dusin"] = int(m.group(2))
    return ust


def fatura_oku(fatura_id):
    """Kayıtlı fatura fotoğrafını okur; yazı + aday satırları JSON döner.

    Önce Başak'ın kendi gözü (yerel VLM) denenir; yoksa/kapalıysa ya
    da boş dönerse mevcut bulut zinciri (image_analyzer) devralır.
    Geçici bulut hatalarında 3 kez denenir. Aday çıkarımı kuraldır
    (barkod/fiyat/beden deseni); nihai satırları model
    katalog_kur'a verir.
    """
    yol = _fatura_yolu(fatura_id)
    if yol is None or not os.path.isfile(yol):
        return {"error": "Fatura bulunamadı: '%s'." % (fatura_id or "")}
    if os.path.splitext(yol)[1].lower() == ".pdf":
        return {"error": ("PDF okuma bu sürümde yok; "
                          "faturanın fotoğrafını gönder.")}
    from tools import yerel_goru
    kaynak = ""
    if yerel_goru.musait():
        sonuc = yerel_goru.oku(yol, GORUNTU_SORUSU)
        if not sonuc.get("error"):
            kaynak = "yerel"
        else:
            logger.info("Yerel goz devretti: %s", sonuc["error"])
            sonuc = None
    else:
        sonuc = None
    if sonuc is None:
        from tools import image_analyzer
        import time as _zaman
        for deneme in range(3):
            sonuc = image_analyzer.image_analyze(yol, GORUNTU_SORUSU)
            if not sonuc.get("error") or not _gecici_mi(sonuc["error"]):
                break
            # 2026-09-18: 10 sn bekleme hatta 60 sn API timeout ile
            # birlesince tek fatura 200 sn'yi buluyor, sohbet
            # kilitlenmis gorunuyordu. 2 sn yeterli; kalici
            # hatada zaten donguden cikiliyor.
            if deneme < 2:
                _zaman.sleep(2)
        if not kaynak:
            kaynak = "bulut"
    if sonuc.get("error"):
        return {"error": "Görüntü okunamadı: %s" % sonuc["error"]}
    yazi = sonuc.get("result", "")
    if not yazi.strip():
        return {"error": "Fotoğrafta yazı bulunamadı."}
    ust = _ustbilgi_cikar(yazi)
    return {"result": _j({"fatura_id": fatura_id, "yazi": yazi,
                          "aday_satirlar": _aday_satirlar(yazi),
                          "ustbilgi": ust,
                          "kaynak": kaynak,
                          "model": sonuc.get("model", "")})}


# ── F3: doğrulama + aile birleştirme ──────────────────────────────

def _satir_dogrula(ham, sira):
    """Tek fatura satırını doğrular; (temiz, uyarilar) döner.

    2026-09-18 (Faz A): marka/kategori jargon sözlüğüyle çözülür;
    eksik-belirsiz alanlar uyarıya SORU olarak yazılır — model
    bunları esnafa sohbetten iletir (sessiz varsayım kalmaz).
    """
    uyarilar = []
    if not isinstance(ham, dict):
        return None, ["%d. satır atlandı (biçim bozuk)." % sira]
    marka = str(ham.get("marka", "") or "").strip()
    kod = str(ham.get("kod", "") or "").strip()
    if not kod:
        return None, ["%d. satır atlandı (ürün kodu yok)." % sira]
    if not marka:
        uyarilar.append("%d. satır: marka boş — SOR: '%s' kodlu ürünün "
                        "markası nedir?" % (sira, kod))
    else:
        cozulmus = jargon_coz(marka)
        if cozulmus != marka:
            uyarilar.append("%d. satır: marka '%s' → '%s' (fiş kısaltması "
                            "çözüldü)." % (sira, marka, cozulmus))
        marka = cozulmus
    renk = renk_normla(jargon_coz(ham.get("renk")))
    varyant = str(ham.get("varyant", "") or "").strip()
    if not renk and varyant:
        renk = renk_normla(jargon_coz(varyant_renk(varyant)))
    if not renk:
        uyarilar.append("%d. satır: renk belirsiz — SOR: '%s' ürününün "
                        "rengi nedir?" % (sira, kod))
    barkod, uyari = barkod_dogrula(ham.get("barkod"))
    if uyari:
        uyarilar.append("%d. satır: %s" % (sira, uyari))
    try:
        adet = int(str(ham.get("adet", 1) or 1).strip() or 1)
    except (ValueError, TypeError, AttributeError):
        adet = 1
        uyarilar.append("%d. satır: adet okunamadı, 1 sayıldı — SOR: "
                        "'%s' gerçekten 1 adet mi?" % (sira, kod))
    if adet < 0:
        adet = 0
        uyarilar.append("%d. satır: eksi adet 0 sayıldı." % sira)
    alis, uyari = fiyat_coz(ham.get("alis_fiyat"))
    if uyari:
        uyarilar.append("%d. satır: %s" % (sira, uyari))
    kategori_ham = str(ham.get("kategori", "") or "").strip()
    kategori = jargon_coz(kategori_ham) if kategori_ham else ""
    if not kategori:
        uyarilar.append("%d. satır: kategori belirsiz — SOR: '%s' ürünü "
                        "hangi kategoride satılacak (örn. Erkek Tişört, "
                        "Kadın Atlet)?" % (sira, kod))
        kategori = "Genel"
    return {"marka": marka, "kod": kod,
            "kod_norm": kodu_normla(kod),
            "marka_norm": kodu_normla(marka),
            "barkod": barkod, "beden": beden_normla(ham.get("beden")),
            "renk": renk, "varyant": varyant,
            "adet": adet, "alis_fiyat": alis,
            "kategori": kategori,
            "urun_adi": str(ham.get("urun_adi", "") or "").strip()}, \
        uyarilar


def _kart_ad(marka, kod, renkler):
    ad = ("%s %s" % (marka, kod)).strip() or kod
    if len(renkler) == 1 and next(iter(renkler)):
        ad += " (%s)" % next(iter(renkler)).capitalize()
    return ad


def _kart_aciklama(kod, renkler, bedenler, adet, barkodlar):
    parcalar = ["Ürün Kodu: %s" % kod]
    if renkler - {""}:
        parcalar.append("Renkler: %s" % ", ".join(
            sorted(r.capitalize() for r in renkler if r)))
    if bedenler - {""}:
        parcalar.append("Bedenler: %s" % ", ".join(sorted(bedenler - {""})))
    parcalar.append("Toplam Adet: %d" % adet)
    if barkodlar:
        parcalar.append("Barkod: %s" % ", ".join(sorted(barkodlar)))
    return " | ".join(parcalar)


def _stok_durumu(toplam):
    if toplam <= 0:
        return STOK_BITTI
    if toplam <= 3:
        return STOK_AZ
    return STOK_VAR


def katalog_kur(fatura_id, satirlar, ustbilgi=None):
    """Doğrulanmış satırlardan ürün kartları kurar, işi saklar.

    Aynı (marka, kod) tek kart olur; beden/renk varyant dizilir.
    2026-09-18 (Faz A): sonuç 'sorulacaklar' listesi taşır —
    marka/kategori/renk/adet eksik ya da belirsizse buradan esnafa
    sorulur; cevaplarla satırlar düzeltildikten sonra katalog_kur
    yeniden çağrılır. ustbilgi (fatura_oku'dan) iş verisine yazılır.
    Dönüş: iş özeti JSON (is_id, kartlar, uyarilar, sorulacaklar).
    """
    if not _fatura_yolu(fatura_id):
        return {"error": "Fatura bulunamadı: '%s'." % (fatura_id or "")}
    if not isinstance(satirlar, list) or not satirlar:
        return {"error": "Satır listesi boş olamaz."}
    if len(satirlar) > 500:
        return {"error": "Satır çok fazla (en fazla 500)."}
    temizler, uyarilar = [], []
    for i, ham in enumerate(satirlar, 1):
        temiz, uy = _satir_dogrula(ham, i)
        uyarilar.extend(uy)
        if temiz:
            temizler.append(temiz)
    if not temizler:
        return {"error": ("Hiç geçerli satır yok (%d uyarı). " % len(uyarilar) +
                          " ".join(uyarilar[:3]))}
    gruplar = {}
    for satir in temizler:
        anahtar = (satir["marka_norm"], satir["kod_norm"])
        gruplar.setdefault(anahtar, []).append(satir)
    kartlar = []
    for sira, ((marka_norm, kod_norm), uyeler) in enumerate(
            sorted(gruplar.items()), 1):
        ilk = uyeler[0]
        renkler = {u["renk"] for u in uyeler}
        bedenler = {u["beden"] for u in uyeler}
        barkodlar = {u["barkod"] for u in uyeler if u["barkod"]}
        kategoriler = {}
        for u in uyeler:
            kategoriler[u["kategori"]] = kategoriler.get(
                u["kategori"], 0) + 1
        kategori = max(kategoriler, key=kategoriler.get)
        ad = next((u["urun_adi"] for u in uyeler if u["urun_adi"]),
                  _kart_ad(ilk["marka"], ilk["kod"], renkler))
        toplam = sum(u["adet"] for u in uyeler)
        kartlar.append({
            "kart_id": "krt_%02d" % sira,
            "ad": ad, "marka": ilk["marka"], "kod": ilk["kod"],
            "kategori": kategori,
            "aciklama": _kart_aciklama(ilk["kod"], renkler, bedenler,
                                       toplam, barkodlar),
            "varyantlar": [{"beden": u["beden"], "renk": u["renk"],
                             "barkod": u["barkod"], "adet": u["adet"],
                             "alis_fiyat": u["alis_fiyat"]}
                            for u in uyeler],
            "toplam_adet": toplam,
            "stok_durumu": _stok_durumu(toplam),
            "satis_fiyat": None,
            "eslesme": None,
        })
    is_id = _id("ktg")
    sorulacaklar = [u for u in uyarilar if "SOR:" in u]
    is_verisi = {"is_id": is_id, "fatura_id": fatura_id,
                 "durum": "taslak", "olusturma": _simdi(),
                 "ustbilgi": ustbilgi if isinstance(ustbilgi, dict) else {},
                 "satirlar": temizler, "kartlar": kartlar,
                 "uyarilar": uyarilar, "yetki_id": None}
    _kok_hazirla(KATALOG_KOK)
    try:
        with _KILIT:
            _atomik_yaz(os.path.join(KATALOG_KOK, is_id + ".json"),
                        is_verisi)
    except OSError as e:
        logger.warning("Katalog yazilamadi: %s", e)
        return {"error": "Katalog saklanamadı."}
    ozet = [{"kart_id": k["kart_id"], "ad": k["ad"],
             "varyant": len(k["varyantlar"]),
             "toplam_adet": k["toplam_adet"],
             "stok": k["stok_durumu"]} for k in kartlar]
    return {"result": _j({"is_id": is_id, "durum": "taslak",
                          "kart_sayisi": len(kartlar),
                          "toplam_adet": sum(
                              k["toplam_adet"] for k in kartlar),
                          "kartlar": ozet, "uyarilar": uyarilar,
                          "sorulacaklar": sorulacaklar})}


def _is_yukle(is_id):
    if not _guvenli_id(is_id):
        return None
    yol = os.path.realpath(os.path.join(KATALOG_KOK, str(is_id) + ".json"))
    if os.path.commonpath([yol, os.path.realpath(KATALOG_KOK)]) != \
            os.path.realpath(KATALOG_KOK):
        return None
    try:
        veri = _yukle_json(yol)
    except (OSError, ValueError):
        return None
    return veri if isinstance(veri, dict) else None


def katalog_getir(is_id):
    """Katalog işinin tamamını + marka izin kapsamını JSON döner."""
    veri = _is_yukle(is_id)
    if veri is None:
        return {"error": "Katalog işi bulunamadı: '%s'." % (is_id or "")}
    veri["marka_kapsama"] = {
        ad: marka_kapsama(norm)
        for norm, ad in _is_markalari(veri).items()}
    return {"result": _j(veri)}


def katalog_listele():
    """Katalog işlerini listeler: is_id, durum, kart sayısı."""
    try:
        dosyalar = sorted(
            (d for d in os.listdir(KATALOG_KOK) if d.endswith(".json")),
            reverse=True)
    except OSError:
        return {"result": _j([])}
    ozet = []
    for dosya in dosyalar[:100]:
        try:
            veri = _yukle_json(os.path.join(KATALOG_KOK, dosya))
            ozet.append({"is_id": veri.get("is_id", dosya[:-5]),
                         "durum": veri.get("durum", "?"),
                         "kart_sayisi": len(veri.get("kartlar", [])),
                         "olusturma": veri.get("olusturma", "")})
        except (OSError, ValueError, AttributeError):
            continue
    return {"result": _j(ozet)}


def katalog_fiyat_guncelle(is_id, kart_id, satis_fiyat):
    """Kartın satış fiyatını yazar. Fiyat metin veya sayı olur."""
    veri = _is_yukle(is_id)
    if veri is None:
        return {"error": "Katalog işi bulunamadı: '%s'." % (is_id or "")}
    kart = next((k for k in veri.get("kartlar", [])
                 if k.get("kart_id") == kart_id), None)
    if kart is None:
        return {"error": "Kart bulunamadı: '%s'." % (kart_id or "")}
    deger, uyari = fiyat_coz(satis_fiyat)
    if uyari:
        return {"error": uyari}
    if deger is None:
        return {"error": "Satış fiyatı boş olamaz."}
    kart["satis_fiyat"] = deger
    try:
        with _KILIT:
            _atomik_yaz(os.path.join(KATALOG_KOK, veri["is_id"] + ".json"),
                        veri)
    except (OSError, KeyError) as e:
        logger.warning("Fiyat yazilamadi: %s", e)
        return {"error": "Fiyat saklanamadı."}
    return {"result": _j({"is_id": veri["is_id"], "kart_id": kart_id,
                          "satis_fiyat": deger})}


# ── F4: Vixrex çıktıları ──────────────────────────────────────────

def _kart_gorsel(kart):
    """Yayınlanabilir görsel: eşleşme varsa ve marka izinliyse ilk aday.

    İzin yoksa boş döner; görseller kartta aday olarak durur.
    """
    eslesme = kart.get("eslesme") or {}
    gorseller = eslesme.get("gorseller") or []
    if not gorseller:
        return ""
    if marka_kapsama(kodu_normla(kart.get("marka", ""))) is None:
        return ""
    return gorseller[0]

def _kart_fiyat(kart):
    if kart.get("satis_fiyat") is not None:
        return kart["satis_fiyat"], True
    fiyatlar = [v.get("alis_fiyat") for v in kart.get("varyantlar", [])
                if v.get("alis_fiyat") is not None]
    if fiyatlar:
        return max(fiyatlar), False
    return None, False


def _csv_uret(kartlar):
    cikti = io.StringIO()
    yazici = csv.writer(cikti, lineterminator="\r\n")
    yazici.writerow(CSV_BASLIK)
    for kart in kartlar:
        fiyat, _onayli = _kart_fiyat(kart)
        yazici.writerow([kart.get("ad", ""), fiyat_yaz(fiyat),
                         kart.get("aciklama", ""),
                         kart.get("kategori", "Genel"),
                         kart.get("stok_durumu", STOK_VAR),
                         _kart_gorsel(kart)])
    return cikti.getvalue()


def _batch_uret(kartlar):
    ogeler = []
    for sira, kart in enumerate(kartlar):
        fiyat, _onayli = _kart_fiyat(kart)
        gorsel = _kart_gorsel(kart)
        ogeler.append({
            "name": kart.get("ad", ""),
            "description": kart.get("aciklama", ""),
            "price_text": fiyat_yaz(fiyat),
            "category_id": "",
            "image_urls": [gorsel] if gorsel else [],
            "source_type": "basak_fatura",
            "external_product_id": kart.get("kod", ""),
            "sort_order": sira,
            "isVisible": True,
        })
    return ogeler


def katalog_onayla(is_id):
    """Katalogdan Vixrex CSV + batch JSON + tam katalog üretir.

    Satış fiyatı girilmemiş kart alış fiyatıyla çıkar; uyarıda
    adı geçer. Yolları JSON döner.
    """
    veri = _is_yukle(is_id)
    if veri is None:
        return {"error": "Katalog işi bulunamadı: '%s'." % (is_id or "")}
    kartlar = veri.get("kartlar", [])
    if not kartlar:
        return {"error": "Katalogda kart yok."}
    # veri["uyarilar"] kurulum anının kaydıdır, değişmez; yayına
    # özel uyarılar her onayda taze hesaplanır (onayla idempotent).
    taban = list(veri.get("uyarilar", []))
    uyarilar = list(taban)
    onaysiz = [k["kart_id"] for k in kartlar
               if k.get("satis_fiyat") is None]
    if onaysiz:
        uyarilar.append("Satış fiyatı girilmemiş kartlar alış fiyatıyla "
                        "çıktı: %s." % ", ".join(onaysiz))
    izinsiz = sorted(ad for norm, ad in _is_markalari(veri).items()
                     if marka_kapsama(norm) is None)
    if izinsiz:
        uyarilar.append("Kullanım izni belgesi yok: %s. Vitrinde "
                        "kullanmadan önce üreticiden bir kerelik izin "
                        "belgesi ekle." % ", ".join(izinsiz))
    dusuk = [k["kart_id"] for k in kartlar
             if (k.get("eslesme") or {}).get("guven") == "dusuk"]
    if dusuk:
        uyarilar.append("Düşük güvenli eşleşme, yayından önce karta bak: "
                        "%s." % ", ".join(dusuk))
    bekleyen_gorsel = [
        k["kart_id"] for k in kartlar
        if (k.get("eslesme") or {}).get("gorseller")
        and not _kart_gorsel(k)]
    if bekleyen_gorsel:
        uyarilar.append("Görseller izin belgesi sonrası eklenir: %s."
                        % ", ".join(bekleyen_gorsel))
    csv_metni = _csv_uret(kartlar)
    if len(csv_metni.encode("utf-8-sig")) > 5 * 1024 * 1024:
        return {"error": "Çıktı 5MB sınırını aştı (Vixrex kabul etmez)."}
    batch = _batch_uret(kartlar)
    klasor = os.path.join(KATALOG_KOK, veri["is_id"])
    _kok_hazirla(klasor)
    try:
        with _KILIT:
            with open(os.path.join(klasor, DOSYA_CSV), "w",
                      encoding="utf-8-sig", newline="") as f:
                f.write(csv_metni)
            _atomik_yaz(os.path.join(klasor, DOSYA_BATCH), batch)
            _atomik_yaz(os.path.join(klasor, DOSYA_KATALOG),
                        {**veri, "uyarilar": uyarilar})
            veri["durum"] = "hazir"
            _atomik_yaz(os.path.join(KATALOG_KOK,
                                     veri["is_id"] + ".json"), veri)
    except OSError as e:
        logger.warning("Cikti yazilamadi: %s", e)
        return {"error": "Çıktı dosyaları yazılamadı."}
    return {"result": _j({"is_id": veri["is_id"], "durum": "hazir",
                          "kart_sayisi": len(kartlar),
                          "csv": DOSYA_CSV, "batch": DOSYA_BATCH,
                          "katalog": DOSYA_KATALOG,
                          "fiyat_onaysiz": onaysiz,
                          "uyarilar": uyarilar})}


def cikti_oku(is_id, dosya):
    """Onay çıktısını metin döner (UI indirme düğmesi için)."""
    if dosya not in (DOSYA_CSV, DOSYA_BATCH, DOSYA_KATALOG):
        return {"error": "Bilinmeyen çıktı: '%s'." % (dosya or "")}
    veri = _is_yukle(is_id)
    if veri is None or veri.get("durum") != "hazir":
        return {"error": "Hazır çıktı yok; önce katalog_onayla."}
    yol = os.path.realpath(os.path.join(KATALOG_KOK, veri["is_id"],
                                        dosya))
    kok = os.path.realpath(KATALOG_KOK)
    if os.path.commonpath([yol, kok]) != kok:
        return {"error": "Yol reddedildi."}
    try:
        with open(yol, "r", encoding="utf-8-sig") as f:
            return {"result": f.read()}
    except OSError:
        return {"error": "Çıktı okunamadı."}


# ── D: yayın paketi (Vixrex kabul provası) ────────────────────────
#
# Vixrex toplu API'si sahip oturumu istediği için Başak doğrudan
# ürün basamaz. Bunun yerine dosya, Vixrex'in toplu yükleme
# kurallarına göre ÖNDEN denetlenir (boyut, başlık, satır); esnaf
# dosyayı panele yükler. Kurallar bulk_product_upload_service.dart
# ile aynıdır.

DESTEK_PLATFORM = ("vixrex",)


def _vixrex_baslik_norm(baslik):
    norm = _tr_duzelt(baslik).lower()
    for a, b in (("ü", "u"), ("û", "u"), ("ö", "o"), ("ç", "c"),
                 ("ş", "s"), ("ğ", "g"), ("ı", "i"), ("î", "i")):
        norm = norm.replace(a, b)
    return re.sub(r"[^a-z0-9]", "", norm).strip()


def _vixrex_satir_denetle(basliklar, satir, sira):
    """Tek CSV satırı Vixrex'ten geçer mi? Hata listesi döner."""
    hatalar = []
    hucre = dict(zip(basliklar, satir))
    ad = (hucre.get("urunadi", "") or "").strip()
    if not ad:
        hatalar.append("%d. satır: ürün adı boş, atlanır." % sira)
    fiyat = (hucre.get("fiyat", "") or "").strip()
    if fiyat:
        try:
            float(fiyat)
        except ValueError:
            hatalar.append("%d. satır: fiyat sayı değil: '%s'."
                           % (sira, fiyat[:20]))
    stok = (hucre.get("stokdurumu", "") or "").strip()
    if stok and stok not in (STOK_VAR, STOK_BITTI, STOK_AZ):
        hatalar.append("%d. satır: stok etiketi tanınmadı: '%s'."
                       % (sira, stok[:20]))
    gorsel = (hucre.get("gorselurl", "") or "").strip()
    if gorsel and not gorsel.startswith(("http://", "https://")):
        hatalar.append("%d. satır: görsel adresi http(s) değil." % sira)
    return hatalar


def yayin_paketi(is_id, platform="vixrex"):
    """Çıktıyı platformun yükleme kurallarına göre denetler.

    Dönüş: kabul kararı + dosya adları + esnafın izleyeceği adım.
    Dosya reddedilirse nedenleri listelenir; Vixrex'e yazma yok.
    """
    if (platform or "") not in DESTEK_PLATFORM:
        return {"error": ("'%s' desteklenmiyor; CSV dosyasını indirip "
                          "platformun toplu yüklemesine ver."
                          % (platform or ""))}
    veri = _is_yukle(is_id)
    if veri is None:
        return {"error": "Katalog işi bulunamadı: '%s'." % (is_id or "")}
    if veri.get("durum") != "hazir":
        return {"error": "Önce katalog_onayla ile çıktı üret."}
    yol = os.path.join(KATALOG_KOK, veri["is_id"], DOSYA_CSV)
    try:
        with open(yol, "rb") as f:
            ham = f.read()
    except OSError:
        return {"error": "CSV çıktısı okunamadı."}
    hatalar = []
    if len(ham) > 5 * 1024 * 1024:
        hatalar.append("Dosya 5MB sınırını aşıyor.")
    try:
        metin = ham.decode("utf-8-sig")
    except ValueError:
        return {"error": "CSV kodlaması bozuk."}
    satirlar = list(csv.reader(io.StringIO(metin)))
    satirlar = [s for s in satirlar if any(c.strip() for c in s)]
    if len(satirlar) < 2:
        hatalar.append("CSV'de başlık + en az 1 ürün satırı olmalı.")
        return {"result": _j({"hazir": False, "hatalar": hatalar})}
    basliklar = [_vixrex_baslik_norm(h) for h in satirlar[0]]
    if "urunadi" not in basliklar:
        hatalar.append("Başlıkta ürün adı sütunu yok.")
    for i, satir in enumerate(satirlar[1:], 2):
        hatalar.extend(_vixrex_satir_denetle(basliklar, satir, i))
    # Is uyarilari (onayla aninin): sekil karari (hazir) ayri, is karari
    # ayri tasinir — izinsiz/fiyatsiz is "hazir" CSV ile karismasin.
    kartlar = veri.get("kartlar", [])
    onaysiz = [k.get("kart_id", "?") for k in kartlar
               if k.get("satis_fiyat") is None]
    izinsiz = sorted(ad for norm, ad in _is_markalari(veri).items()
                     if marka_kapsama(norm) is None)
    dusuk = [k.get("kart_id", "?") for k in kartlar
             if (k.get("eslesme") or {}).get("guven") == "dusuk"]
    is_uyarilari = []
    if onaysiz:
        is_uyarilari.append("Satış fiyatı girilmemiş kartlar alış "
                            "fiyatıyla çıktı: %s." % ", ".join(onaysiz))
    if izinsiz:
        is_uyarilari.append("Kullanım izni belgesi yok: %s."
                            % ", ".join(izinsiz))
    if dusuk:
        is_uyarilari.append("Düşük güvenli eşleşme, yayından önce karta "
                            "bak: %s." % ", ".join(dusuk))
    adim = ("Vixrex paneli → Ürünler → Toplu yükle → "
            + DOSYA_CSV + " dosyasını seç.")
    if izinsiz or onaysiz:
        adim += (" Önce eksikleri kapat: " +
                 "; ".join(is_uyarilari))
    return {"result": _j({
        "hazir": not hatalar,
        "platform": "vixrex",
        "kart": len(satirlar) - 1,
        "hatalar": hatalar,
        "is_uyarilari": is_uyarilari,
        "dosyalar": [DOSYA_CSV, DOSYA_BATCH, DOSYA_KATALOG],
        "sonraki_adim": adim,
    })}


# ── F5: kullanım izni belgesi (marka başına bir kerelik) ──────────
#
# İzin markaya verilir, işe değil: bir kez eklenen Tutku belgesi
# sonraki bütün Tutku işlerini kapsar. data/yetki/ altında her
# belgenin üstverisi (<yetki_id>.json) durur; işe bağlanan
# yetki_id yalnız gösterim içindir, kapsama markadan okunur.

def _yetki_tara():
    """Üstveri dosyalarını okur; bozuk olanı atlar."""
    try:
        dosyalar = [d for d in os.listdir(YETKI_KOK)
                    if d.endswith(".json")]
    except OSError:
        return []
    kayitlar = []
    for dosya in dosyalar:
        try:
            with open(os.path.join(YETKI_KOK, dosya), "r",
                      encoding="utf-8-sig") as f:
                veri = json.load(f)
            if isinstance(veri, dict) and veri.get("yetki_id"):
                kayitlar.append(veri)
        except (OSError, ValueError):
            continue
    return kayitlar


def marka_kapsama(marka):
    """Markayı kapsayan yetki_id döner; yoksa None."""
    norm = kodu_normla(marka)
    if not norm:
        return None
    for kayit in _yetki_tara():
        if kayit.get("marka_norm") == norm:
            return kayit["yetki_id"]
    return None


def _is_markalari(veri):
    markalar = {}
    for kart in veri.get("kartlar", []):
        ad = (kart.get("marka", "") or "").strip()
        if ad:
            markalar.setdefault(kodu_normla(ad), ad)
    return markalar


def yetki_belgesi_ekle(is_id, b64_veri, ad, marka=""):
    """Üretici kullanım izni belgesini markaya bağlayarak saklar.

    Marka boşsa ve iş verildiyse işin baskın markası alınır.
    Belge bir kereliktir: aynı markanın sonraki işlerini kapsar.
    """
    if not b64_veri or not str(b64_veri).strip():
        return {"error": "Belge verisi boş."}
    govde = str(b64_veri)
    if "," in govde and govde.startswith("data:"):
        govde = govde.split(",", 1)[1]
    try:
        ham = base64.b64decode(govde, validate=True)
    except (binascii.Error, ValueError):
        return {"error": "Belge verisi bozuk (base64 çözülmedi)."}
    if not ham:
        return {"error": "Belge boş."}
    if len(ham) > MAX_BOYUT:
        return {"error": "Belge çok büyük (en fazla 10MB)."}
    uzanti = os.path.splitext(str(ad or ""))[1].lower()
    if uzanti not in DESTEK_BELGE:
        return {"error": ("Desteklenmeyen belge: '%s'. " % uzanti
                          + "Fotoğraf veya PDF gönder.")}
    veri = None
    if is_id:
        veri = _is_yukle(is_id)
        if veri is None:
            return {"error": "Katalog işi bulunamadı: '%s'." % is_id}
    secili = str(marka or "").strip()
    if not secili and veri is not None:
        markalar = _is_markalari(veri)
        if markalar:
            norm = max(markalar,
                       key=lambda n: sum(
                           1 for k in veri.get("kartlar", [])
                           if kodu_normla(k.get("marka", "")) == n))
            secili = markalar[norm]
    if not secili:
        # Isimsiz belge saklanmaz: kapsama bos norma hic eslesmez,
        # basari donmek oksuz kayit uretir.
        return {"error": "Marka ver (isimsiz belge saklanmaz)."}
    _kok_hazirla(YETKI_KOK)
    yetki_id = _id("yzk")
    try:
        with _KILIT:
            with open(os.path.join(YETKI_KOK, yetki_id + uzanti),
                      "wb") as f:
                f.write(ham)
            _atomik_yaz(os.path.join(YETKI_KOK, yetki_id + ".json"),
                        {"yetki_id": yetki_id, "marka": secili,
                         "marka_norm": kodu_normla(secili),
                         "dosya": yetki_id + uzanti, "tarih": _simdi()})
            if veri is not None:
                veri["yetki_id"] = yetki_id
                _atomik_yaz(os.path.join(KATALOG_KOK,
                                         veri["is_id"] + ".json"), veri)
    except OSError as e:
        logger.warning("Yetki yazilamadi: %s", e)
        return {"error": "Belge saklanamadı."}
    return {"result": _j({"yetki_id": yetki_id, "marka": secili,
                          "bagli_is": veri["is_id"] if veri else None})}


# ── F6: resmi kaynak eşleştirme (Tutku pilotu) ───────────────────
#
# Kayıtlı tedarikçinin resmi sitesinde ürün kodu aranır; bulunan
# sayfanın başlığı ve görselleri karta işlenir. Görsel YAYINA
# yalnız marka izinliyse girer (_kart_gorsel); değilse aday durur.
#
# 2026-09-18 (Faz A): "alias" desteği — fişlerde aynı üreticinin
# farklı yazımları (TUTKU / ELİT / TUT ...) aynı tedarikçiye bağlanır.
# Anahtar kodu_normla çıktısıdır; değer ya tedarikçi sözlüğü ya da
# başka bir anahtara yönlendirmedir (str = alias).

TEDARIKCILER = {
    "TUTKU": {"site": "tutkuelit.com.tr", "ad": "Tutku"},
    "ELIT": "TUTKU",
    "TUT": "TUTKU",
}

# Sırrı olmayan, esnafın fişinde geçen marka kısaltmaları; jargon
# çözümünde marka olarak da kullanılır.
MARKA_TAKMA = {
    "ELIT": "Tutku Elit",
}


def tedarikci_coz(marka):
    """Marka adını (alias dâhil) tedarikçi kaydına çözer.

    Türkçe büyük İ önce ASCII I'ya indirilir (ELİT → ELIT),
    sonra alias zinciri en fazla 3 adım çözülür (döngü koruması).
    Dönüş: (kayit, cozulen_ad) — kayıtsız markada (None, ad).
    """
    anahtar = kodu_normla(_tr_duzelt(marka).replace("İ", "I"))
    ad = str(marka or "").strip()
    for _ in range(3):
        kayit = TEDARIKCILER.get(anahtar)
        if kayit is None:
            return None, ad
        if isinstance(kayit, str):
            anahtar = kodu_normla(_tr_duzelt(kayit).replace("İ", "I"))
            ad = TEDARIKCILER.get(anahtar, {}).get("ad", ad) \
                if isinstance(TEDARIKCILER.get(anahtar), dict) \
                else ad
            continue
        return kayit, ad
    return None, ad

_URL_RE = re.compile(r"https?://[^\s\"'<>]+")


def _alnum(metin):
    return re.sub(r"[^a-z0-9]", "", _tr_duzelt(metin).lower())


def _eslesme_skor(kod, marka, adres, yazi):
    """3 adres + 2 başlık/yazı + 1 marka + 2 ürün sayfası - 1 kategori;
    5+ yüksek, 3+ orta."""
    skor = 0
    kod_a = _alnum(kod)
    yol_a = ""
    if kod_a:
        from urllib.parse import urlparse as _coz
        try:
            yol_a = _alnum(_coz(adres).path)
        except ValueError:
            yol_a = ""
        if kod_a in yol_a:
            skor += 3
        if kod_a in _alnum((yazi or "")[:2000]):
            skor += 2
    if _alnum(marka) and _alnum(marka) in _alnum(yazi or ""):
        skor += 1
    if "urun" in yol_a or "product" in yol_a:
        skor += 2
    if "kategori" in yol_a or "category" in yol_a:
        skor -= 1
    return skor


def urun_eslestir(is_id, kart_id):
    """Kartı resmi sitede arar; kaynak, güven ve görselleri karta işler.

    Eşleşme bulunamazsa veya marka kayıtsızsa hata döner; karta
    dokunulmaz. Görsellerin yayına girmesi izne bağlıdır.
    """
    veri = _is_yukle(is_id)
    if veri is None:
        return {"error": "Katalog işi bulunamadı: '%s'." % (is_id or "")}
    kart = next((k for k in veri.get("kartlar", [])
                 if k.get("kart_id") == kart_id), None)
    if kart is None:
        return {"error": "Kart bulunamadı: '%s'." % (kart_id or "")}
    tedarikci, cozulen_ad = tedarikci_coz(kart.get("marka", ""))
    if tedarikci is None:
        return {"error": ("'%s' için eşleştirme kaydı yok; "
                          "kart faturasıyla çıkar."
                          % (kart.get("marka", "") or "?"))}
    from tools import web_search as ws
    arama = ws.web_search("site:%s %s" % (tedarikci["site"],
                                          kart.get("kod", "")))
    if arama.get("error"):
        return {"error": "Arama yapılamadı: %s" % arama["error"]}
    adaylar = []
    for adres in _URL_RE.findall(arama.get("result", "")):
        try:
            from urllib.parse import urlparse as _coz
            host = (_coz(adres).hostname or "").lower()
        except ValueError:
            continue
        if host == tedarikci["site"] or \
                host.endswith("." + tedarikci["site"]):
            if adres not in adaylar:
                adaylar.append(adres)
    if not adaylar:
        return {"error": ("Resmi sitede eşleşme bulunamadı: %s."
                          % kart.get("kod", ""))}
    en_iyi, en_skor, en_yazi = None, 0, ""
    eksikler = []
    for adres in adaylar[:5]:
        okuma = ws.sayfa_oku(adres)
        yazi = "" if okuma.get("error") else okuma.get("result", "")
        if okuma.get("error") and "sayfa_oku" not in eksikler:
            eksikler.append("sayfa_oku")
        skor = _eslesme_skor(kart.get("kod", ""), kart.get("marka", ""),
                             adres, yazi)
        if skor > en_skor:
            en_iyi, en_skor, en_yazi = adres, skor, yazi
    if en_iyi is None:
        return {"error": ("Resmi sitede eşleşme bulunamadı: %s."
                          % kart.get("kod", ""))}
    gorseller = []
    gorsel = ws.sayfa_gorseller(en_iyi)
    if not gorsel.get("error"):
        try:
            bulunan = json.loads(gorsel["result"])
            if isinstance(bulunan, list):
                gorseller = [g for g in bulunan if isinstance(g, str)][:10]
        except ValueError:
            eksikler.append("gorsel_cozumleme")
    else:
        eksikler.append("gorsel")
    guven = "yuksek" if en_skor >= 5 else "orta" if en_skor >= 3 \
        else "dusuk"
    kart["eslesme"] = {
        "kaynak": en_iyi,
        "baslik": (en_yazi or "")[:120],
        "guven": guven,
        "gorseller": gorseller,
        "eksik": sorted(set(eksikler)),
        "tarih": _simdi(),
    }
    try:
        with _KILIT:
            _atomik_yaz(os.path.join(KATALOG_KOK, veri["is_id"] + ".json"),
                        veri)
    except OSError as e:
        logger.warning("Eslesme yazilamadi: %s", e)
        return {"error": "Eşleşme saklanamadı."}
    return {"result": _j({"is_id": veri["is_id"], "kart_id": kart_id,
                          "guven": guven, "kaynak": en_iyi,
                          "gorsel_sayisi": len(gorseller)})}

def eslesme_adayi(marka, kod):
    """Eşleştirme için normalize kimlik + aday sorgular üretir.

    Ağ adresi kurmaz, sayfa okumaz; pilot marka başlayınca
    web_search/sayfa_oku bu sorguları kullanır.
    """
    return {"marka": str(marka or "").strip(),
            "kod": kodu_normla(kod)}


# ── Faz B: şirket kartı araştırma ────────────────────────────────
# Markanın resmi sitesi + iletişim/vergi bilgisi. Salt-okunur:
# yalnız web_search + sayfa_oku; disk yazımı yok. Alan regex'le
# sayfa metninden çıkarılır; bulunamayan alan boş kalır (uydurma
# yok). Model eksik alanları esnafa sorar ya da açık bırakır.

_SIRKET_TEL_RE = re.compile(
    r"(?:\+90|0)\s?5\d{2}\s?\d{3}\s?\d{2}\s?\d{2}"
    r"|(?:\+90|0)\s?2\d{2}\s?\d{3}\s?\d{2}\s?\d{2}"
    r"|(?:\+90|0)\s?3\d{2}\s?\d{3}\s?\d{2}\s?\d{2}")
_SIRKET_EPOSTA_RE = re.compile(
    r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
_SIRKET_ADRES_KELIMELERI = ("adres", "mahalle", "mah.", "cadde", "cad.",
                            "sokak", "sk.", "osb", "organize sanayi",
                            "sitesi", "bulvar")
_SIRKET_KELIME_SKORLARI = ("adres", "iletişim", "iletisim", "telefon",
                           "tel:", "tel ", "faks", "vergi", "e-posta",
                           "eposta", "bize ulaşın")
_SOSYAL_HOST = ("facebook.com", "instagram.com", "twitter.com",
                "x.com", "linkedin.com", "youtube.com", "tiktok.com")


def _sirket_adres_meti(satir):
    """Satır adres cümlesine benziyor mu (kelime + uzunluk)?"""
    kucuk = _tr_duzelt(satir).lower()
    if not (5 <= len(satir) <= 200):
        return False
    return any(k in kucuk for k in _SIRKET_ADRES_KELIMELERI)


def _sirket_sayfa_skor(yazi):
    """İletişim sayfası adayı skorü: bilinen kelime geçişleri."""
    if not yazi:
        return 0
    kucuk = _tr_duzelt(yazi[:8000]).lower()
    return sum(kucuk.count(k) for k in _SIRKET_KELIME_SKORLARI)


def _sirket_iletisim_yollari(site):
    """Tedarikçi sitesinin olası iletişim sayfası yolları."""
    temel = "https://%s" % site.rstrip("/")
    return [temel + "/iletisim", temel + "/iletisim.html",
            temel + "/contact", temel + "/contact-us",
            temel + "/hakkimizda", temel + "/"]


def sirket_ara(marka):
    """Markanın resmi sitesini + iletişim/vergi bilgilerini arar.

    Yalnız web_search + sayfa_oku (salt-okunur); disk yazımı yok.
    Dönüş JSON: {marka, site, unvan, telefonlar, eposta, adresler,
    kaynak, eksik}. Bulunamayan alan boş döner — uydurma yok.
    """
    marka = str(marka or "").strip()
    if not marka:
        return {"error": "Marka boş olamaz."}
    from tools import web_search as ws

    kayit, cozulen_ad = tedarikci_coz(marka)
    site = (kayit or {}).get("site", "")
    adaylar = []
    if site:
        adaylar = _sirket_iletisim_yollari(site)
    else:
        arama = ws.web_search(
            "%s iletişim adres telefon resmi site" % cozulen_ad)
        if arama.get("error"):
            return {"error": "Arama yapılamadı: %s" % arama["error"]}
        for adres in _URL_RE.findall(arama.get("result", "")):
            try:
                from urllib.parse import urlparse as _coz
                host = (_coz(adres).hostname or "").lower()
            except ValueError:
                continue
            if any(host.endswith(h) for h in _SOSYAL_HOST):
                continue
            temel = "%s://%s" % (_coz(adres).scheme, host)
            if temel not in adaylar:
                adaylar.append(temel)
            if len(adaylar) >= 5:
                break
    if not adaylar:
        return {"error": "'%s' için site bulunamadı." % cozulen_ad}

    en_iyi, en_skor, en_site = "", 0, ""
    for aday in adaylar[:5]:
        okuma = ws.sayfa_oku(aday)
        if okuma.get("error"):
            continue
        skor = _sirket_sayfa_skor(okuma.get("result", ""))
        if skor > en_skor:
            en_iyi, en_skor, en_site = adres if False else aday, skor, aday
    if not en_iyi:
        return {"error": "'%s' için iletişim sayfası okunamadı."
                         % cozulen_ad}
    okuma = ws.sayfa_oku(en_iyi)
    if okuma.get("error"):
        return {"error": "Sayfa okunamadı: %s" % okuma["error"]}
    metin = okuma.get("result", "")
    baslangic = metin[:6000]
    telefonlar = []
    for m in _SIRKET_TEL_RE.finditer(baslangic):
        tel = re.sub(r"\s+", " ", m.group(0)).strip()
        if tel not in telefonlar:
            telefonlar.append(tel)
    eposta = []
    for m in _SIRKET_EPOSTA_RE.finditer(baslangic):
        ad = m.group(0).strip().lower()
        if ad not in eposta:
            eposta.append(ad)
    adresler = []
    for satir in baslangic.splitlines():
        satir = satir.strip()
        if _sirket_adres_meti(satir) and satir not in adresler:
            adresler.append(satir)
        if len(adresler) >= 3:
            break
    m = re.search(r"vergi[^0-9]{0,40}(\d{10,11})", baslangic,
                  re.IGNORECASE)
    vergi_no = m.group(1) if m else ""
    sonuc = {
        "marka": cozulen_ad,
        "site": en_site,
        "unvan": "",
        "telefonlar": telefonlar[:3],
        "eposta": eposta[:3],
        "adresler": adresler,
        "vergi_no": vergi_no,
        "kaynak": en_iyi,
        "eksik": [alan for alan, deger in (
            ("telefon", telefonlar), ("eposta", eposta),
            ("adres", adresler), ("vergi_no", vergi_no))
            if not deger],
    }
    return {"result": _j(sonuc)}


def eslesme_adayi(marka, kod):
    """Eşleştirme için normalize kimlik + aday sorgular üretir.

    Ağ adresi kurmaz, sayfa okumaz; pilot marka başlayınca
    web_search/sayfa_oku bu sorguları kullanır.
    """
    return {"marka": str(marka or "").strip(),
            "kod": str(kod or "").strip(),
            "marka_norm": kodu_normla(marka),
            "kod_norm": kodu_normla(kod),
            "sorgular": [
                "%s %s" % (str(marka or "").strip(),
                           str(kod or "").strip()),
                "%s resmi katalog" % str(marka or "").strip(),
            ]}
