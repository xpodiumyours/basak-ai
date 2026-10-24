# -*- coding: utf-8 -*-
"""chat/belge.py — Belgeden metin çıkarma.

Neden var: web kullanıcısı elindeki PDF/DOCX/TXT/CSV'yi verip soru
sorabilsin. Ekran yalnız fotoğraf kabul ediyordu.

Akış: dosya `/api/belge` ucunda çözülür, metin istemciye döner; istemci
aynı metni mesajla birlikte geri gönderir. Sunucu belge SAKLAMAZ — yeni
bir depo katmanı yok, mevcut sohbet akışı aynen kullanılır.

Kurallar:
- Tür UZANTIDAN DEĞİL İÇERİKTEN anlaşılır (`%PDF-`, DOCX için ZIP imzası
  + `word/document.xml`, metin için geçerli kod çözümü + NUL yok).
- Dosya ASLA çalıştırılmaz; yalnız bayt okunur ve metin ayrıştırılır.
- Sessiz başarısızlık yok: şifreli PDF, taranmış PDF (metin katmanı yok),
  bozuk dosya ve sınır aşımı ayrı ve anlaşılır hata verir.
- Bu modül karar vermez: hangi belgenin açılacağı çağıranın kararıdır.

Dönüş biçimi (metin_cikar): {"tur", "sayfalar": [{"sayfa": 1,
"metin": "..."}], "kirpildi": bool}
"""

import io
import logging
import re
import zipfile

logger = logging.getLogger(__name__)

BOYUT_SINIR = 10 * 1024 * 1024      # 10 MB — yükleme sınırı
CIKARMA_SURE_SINIR = 20.0           # tek belge için metin çıkarma süresi (sn)
METIN_SINIR = 200_000               # çıkarılan metnin toplam karakter tavanı
_ACILMIS_SINIR = 40 * 1024 * 1024   # zip bombasına karşı açılmış boyut tavanı

DESTEKLENEN = ("pdf", "docx", "txt", "md", "csv")

_ETIKET = {
    "pdf": "PDF",
    "docx": "Word (DOCX)",
    "txt": "metin",
    "md": "Markdown",
    "csv": "CSV",
}


class BelgeHatasi(ValueError):
    """Kullanıcıya gösterilebilir belge hatası."""


def _uzanti(ad):
    ad = str(ad or "").strip().lower()
    if "." not in ad:
        return ""
    return ad.rsplit(".", 1)[1][:8]


def tur_belirle(ad, ham):
    """İçeriğe bakarak türü belirler. Uzantı yalnız metin ailesinde ipucu.

    Bayt imzası uzantıyla çelişirse İÇERİK kazanır (yanlış adlandırılmış
    dosya, uzantı hilesiyle sınır atlatamaz).
    """
    if not isinstance(ham, (bytes, bytearray)) or not ham:
        raise BelgeHatasi("Boş dosya yüklenemez.")
    if ham[:5] == b"%PDF-":
        return "pdf"
    if ham[:2] == b"PK":
        try:
            with zipfile.ZipFile(io.BytesIO(bytes(ham))) as z:
                adlar = set(z.namelist())
        except zipfile.BadZipFile as e:
            raise BelgeHatasi(
                "Dosya bozuk: sıkıştırılmış içerik açılamadı.") from e
        if "word/document.xml" in adlar:
            return "docx"
        raise BelgeHatasi(
            "Bu sıkıştırılmış dosya bir Word belgesi değil. "
            "Desteklenen türler: %s." % ", ".join(DESTEKLENEN))
    if b"\x00" in ham[:4096]:
        raise BelgeHatasi(
            "Dosya metin değil (ikili içerik). Desteklenen türler: %s."
            % ", ".join(DESTEKLENEN))
    uzanti = _uzanti(ad)
    if uzanti in ("txt", "md", "csv"):
        return uzanti
    # Uzantı yok/başka: içerik metinse metin sayılır (kopyala-yapıştır
    # dosyaları yaygın). Tür adı "txt" olur.
    return "txt"


def _coz_metin(ham):
    """Baytı metne çevirir: UTF-8 (BOM'lu dahil), sonra cp1254."""
    for kodlama in ("utf-8-sig", "cp1254"):
        try:
            return ham.decode(kodlama)
        except UnicodeDecodeError:
            continue
    raise BelgeHatasi(
        "Dosyanın kodlaması okunamadı (UTF-8 ya da Windows-1254 beklenir).")


def _pdf_sayfalari(ham):
    try:
        from pypdf import PdfReader
        from pypdf.errors import PdfReadError
    except ImportError as e:  # pragma: no cover — kurulum hatası
        raise BelgeHatasi(
            "PDF desteği kurulu değil (pypdf). Diğer türler çalışır."
        ) from e

    try:
        okuyucu = PdfReader(io.BytesIO(bytes(ham)))
    except PdfReadError as e:
        raise BelgeHatasi("PDF açılamadı: dosya bozuk olabilir.") from e
    except Exception as e:  # noqa: BLE001 — pypdf çeşitli istisna atar
        raise BelgeHatasi("PDF açılamadı: %s" % str(e)[:120]) from e

    if getattr(okuyucu, "is_encrypted", False):
        try:
            cozuldu = okuyucu.decrypt("")
        except Exception:  # noqa: BLE001 — parola yoksa çözülemez
            cozuldu = 0
        if not cozuldu:
            raise BelgeHatasi(
                "PDF şifreli. Şifresi kaldırılmış bir kopya yükleyin.")

    sayfalar = []
    for i, sayfa in enumerate(getattr(okuyucu, "pages", []) or [], start=1):
        try:
            metin = sayfa.extract_text() or ""
        except Exception as e:  # noqa: BLE001 — tek sayfa hatası tümünü düşürmesin
            logger.warning("PDF sayfa %d okunamadı: %s", i, e)
            metin = ""
        if metin.strip():
            sayfalar.append({"sayfa": i, "metin": metin})
    if not sayfalar:
        raise BelgeHatasi(
            "Bu PDF'te metin katmanı yok (taranmış görüntü olabilir). "
            "Metni seçilebilen bir PDF ya da metin dosyası yükleyin.")
    return sayfalar


def _docx_metni(ham):
    try:
        with zipfile.ZipFile(io.BytesIO(bytes(ham))) as z:
            toplam = sum(i.file_size for i in z.infolist())
            if toplam > _ACILMIS_SINIR:
                raise BelgeHatasi(
                    "Belge açıldığında çok büyüyor (%d MB); reddedildi."
                    % (toplam // (1024 * 1024)))
            govde = z.read("word/document.xml")
    except KeyError as e:
        raise BelgeHatasi("Word belgesinin gövdesi bulunamadı.") from e
    except zipfile.BadZipFile as e:
        raise BelgeHatasi("Word belgesi bozuk.") from e

    try:
        xml = govde.decode("utf-8", "replace")
    except Exception as e:  # noqa: BLE001 — kod çözme beklenmedik hata
        raise BelgeHatasi("Word belgesinin metni okunamadı.") from e

    xml = xml.replace("</w:p>", "\n").replace("<w:tab/>", "\t")
    xml = xml.replace("<w:br/>", "\n")
    metin = re.sub(r"<[^>]+>", "", xml)
    metin = metin.replace("&amp;", "&").replace("&lt;", "<") \
        .replace("&gt;", ">").replace("&quot;", '"').replace("&apos;", "'")
    if not metin.strip():
        raise BelgeHatasi("Word belgesinde okunacak metin yok.")
    return [{"sayfa": 1, "metin": metin}]


def metin_cikar(ad, ham, sure_sinir=None):
    """Belgeden metni çıkarır; HESAPLAMA SÜRE SINIRIYLA yapılır.

    Bozuk/çok büyük bir PDF ayrıştırmayı dakikalarca meşgul edebilir ve
    sunucu isteği düşene kadar kaynak yer. Bu yüzden çıkarma ayrı bir
    iş parçacığında koşar ve sınır aşılırsa açık hata döner.

    SINIR: iş parçacığı zorla öldürülemez; C uzantısında kilitlenen bir
    çağrı arka planda ölürken kalır (daemon). Python tarafındaki gerçek
    kilitlenmeler bu yolla kesilir; sürecin kendisi istek bitince
    serbest kalır (serverless).
    """
    import threading

    sinir = CIKARMA_SURE_SINIR if sure_sinir is None else float(sure_sinir)
    kutu = {}

    def _kos():
        try:
            kutu["sonuc"] = _metin_cikar(ad, ham)
        except BaseException as e:  # noqa: BLE001 — çağırana aynen taşınır
            kutu["hata"] = e

    isci = threading.Thread(target=_kos, name="belge-cikar", daemon=True)
    isci.start()
    isci.join(sinir)
    if isci.is_alive():
        logger.warning("Belge cikarma zaman asimi: %s (%.0f sn)",
                       str(ad)[:80], sinir)
        raise BelgeHatasi(
            "Belge okuma süresi aşıldı (%.0f sn). Daha küçük ya da daha "
            "basit bir dosya deneyin." % sinir)
    if "hata" in kutu:
        raise kutu["hata"]
    return kutu["sonuc"]


def _metin_cikar(ad, ham):
    """Belgeden metni çıkarır. Hata durumunda `BelgeHatasi` yükselir."""
    if not isinstance(ham, (bytes, bytearray)):
        raise BelgeHatasi("Dosya içeriği bayt olmalı.")
    if len(ham) > BOYUT_SINIR:
        raise BelgeHatasi(
            "Dosya %.1f MB; sınır %d MB."
            % (len(ham) / (1024 * 1024), BOYUT_SINIR // (1024 * 1024)))

    tur = tur_belirle(ad, ham)
    if tur == "pdf":
        sayfalar = _pdf_sayfalari(ham)
    elif tur == "docx":
        sayfalar = _docx_metni(ham)
    else:
        sayfalar = [{"sayfa": 1, "metin": _coz_metin(bytes(ham))}]

    kirpildi = False
    kalan = METIN_SINIR
    temiz = []
    for parca in sayfalar:
        metin = str(parca.get("metin") or "")
        if kalan <= 0:
            kirpildi = True
            break
        if len(metin) > kalan:
            metin = metin[:kalan]
            kirpildi = True
        temiz.append({"sayfa": parca.get("sayfa") or 1, "metin": metin})
        kalan -= len(metin)
    if not temiz:
        raise BelgeHatasi("Belgede okunacak metin yok.")
    return {"tur": tur, "sayfalar": temiz, "kirpildi": kirpildi}


def kanit_blogu(ad, cikarim):
    """Modele giden kanıt etiketi: dosya adı + sayfa numarası.

    Uydurma savunması: her parça hangi dosyanın hangi sayfasından geldiğini
    kendi satırında taşır; model kaynak gösterirken uydurmak zorunda kalmaz.
    """
    ad = str(ad or "belge").strip() or "belge"
    satirlar = ["Belge: %s" % ad]
    for parca in (cikarim or {}).get("sayfalar") or []:
        satirlar.append("[%s · sayfa %s]" % (ad, parca.get("sayfa") or 1))
        satirlar.append(str(parca.get("metin") or "").strip())
    if (cikarim or {}).get("kirpildi"):
        satirlar.append("(Belgenin geri kalanı metin sınırı için okunmadı.)")
    return "\n".join(satirlar)


def istemciden_blogu(ham):
    """İstemcinin geri gönderdiği belge metnini doğrular ve etiketler.

    Sunucu belgeyi SAKLAMAZ: `/api/belge` metni bir kez çıkarır, istemci
    aynı metni mesajla birlikte geri gönderir. Burada yalnız şekil ve
    boyut denetlenir; metin değiştirilmez, sayfa numarası korunur.
    """
    if not isinstance(ham, dict):
        raise BelgeHatasi("Belge verisi okunamadı.")
    ad = str(ham.get("ad") or "belge").strip()[:120] or "belge"
    sayfalar = ham.get("sayfalar")
    if not isinstance(sayfalar, list) or not sayfalar:
        raise BelgeHatasi("Belge metni boş.")
    temiz = []
    kalan = METIN_SINIR
    kirpildi = bool(ham.get("kirpildi"))
    for parca in sayfalar:
        if not isinstance(parca, dict):
            continue
        metin = str(parca.get("metin") or "")
        if not metin.strip():
            continue
        if len(metin) > kalan:
            metin = metin[:kalan]
            kirpildi = True
        try:
            sayfa = int(parca.get("sayfa") or 1)
        except (TypeError, ValueError):
            sayfa = 1
        temiz.append({"sayfa": sayfa, "metin": metin})
        kalan -= len(metin)
        if kalan <= 0:
            kirpildi = True
            break
    if not temiz:
        raise BelgeHatasi("Belge metni boş.")
    return kanit_blogu(ad, {"sayfalar": temiz, "kirpildi": kirpildi})


def coz_data_url(data_url):
    """data:application/pdf;base64,... biçimini (ad, bayt) olarak çözer."""
    import base64
    import binascii

    if not isinstance(data_url, str) or "," not in data_url:
        raise BelgeHatasi("Dosya verisi okunamadı.")
    baslik, veri = data_url.split(",", 1)
    if "base64" not in baslik.lower():
        raise BelgeHatasi("Dosya verisi base64 değil.")
    try:
        ham = base64.b64decode(veri, validate=True)
    except (ValueError, binascii.Error) as e:
        raise BelgeHatasi("Dosya verisi çözülemedi.") from e
    return ham
