"""olcu.py — Çıkış kapısı (ÖLÇÜ zemini, OLCU.md §2).

Başak'ın cevabındaki her cümle kullanıcıya gitmeden denetlenir:

  [A] dosya.yolu "alinti" -> dosyada birebir arama (uydurma alinti elenir)
  [O1] arac "alinti"      -> bu turda calisan arac ciktisinda birebir arama
  [C] [O1][O2] ...        -> dayanaklar bu turda dogrulanmis [O] cumleleri olmali
  [B]                     -> gecer (bilmiyorum / olculemez / nezaket)

Isaretsiz cumle silinir. Elenen cumle varsa cevabin sonuna tek satir
"Bunu ölçemedim." eklenir. Kapinin kendisi yapay zeka degildir; metin
kontrolu ve dosya aramasidir.

Dosya erisimi yalniz proje koku altindaki dosyalarla sinirlidir;
ayarlar.json gibi sifir tasiyabilecek dosyalar acilmaz (AGENTS.md §5).
"""

import logging
import os
import re

logger = logging.getLogger(__name__)

BASE = os.path.dirname(os.path.abspath(__file__))

# Kapinin acmayi reddettigi desenler — sifirlar disariya/sayaca girmez
_YASAKLI = ("ayarlar", ".env", "api_key", "_key", "gecmis.json")

_MARKER = re.compile(r"^\[(Ö|O|Ç|C|B|A)\s*(\d*)\]", re.IGNORECASE)
_ALINTI = re.compile(r'"([^"]{3,400})"')
_KONUM_A = re.compile(r'^\[A\]\s*([^\s"]+)', re.IGNORECASE)
_DAYANAK = re.compile(r"\[(?:Ö|O)\s*(\d+)\]", re.IGNORECASE)

_SONLANDIRAN = re.compile(
    r'(?<=[.!?…])\s+(?=["«(\[]?[A-ZÀ-ÞĞİÖŞÜ0-9\-\|])')

YEDEK_CUMLE = "Bunu ölçemedim."


# Araclar ASCII Turkce dondurur, model duzgun Turkce alintilar;
# karsilastirma oncesi karakterler esitlenir (icerik degismez, sesli harf kalinir)
_TURKCE_FOLD = str.maketrans({
    "ı": "i", "I": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
})


def _norm(metin):
    """Birebirlik karsilastirmasi icin esnek normalizasyon.

    Turkce karakter katlamasi + markdown vurgu kalintilarinin soyulmasi;
    icerigin kendisi degismez, yuzey farklari tolere edilir.
    """
    t = (metin or "").translate(_TURKCE_FOLD).lower()
    for a, b in (("“", '"'), ("”", '"'), ("„", '"'), ("’", "'"),
                 ("‘", "'"), ("–", "-"), ("—", "-"), ("…", "...")):
        t = t.replace(a, b)
    t = re.sub(r"[*_`#>]+", "", t)
    return re.sub(r"\s+", " ", t).strip()


def _tip_bul(cumle):
    """Cumlenin isaretini dondurur: (tip, numara). Isaretsizse (None, '').

    Turkce harfler ASCII eslerine indirgenir: Ö->O, Ç->C.
    """
    m = _MARKER.match(cumle)
    if not m:
        return None, ""
    tip = m.group(1).upper()
    if tip == "Ö":
        tip = "O"
    elif tip == "Ç":
        tip = "C"
    return tip, m.group(2) or ""


def bol_cumleler(metin):
    """Cevabi denetlenecek birimlere boler.

    Isaretli cumleler ve tablo/madde satirlari tek birim sayilir;
    duz metin satirlari sonlandiranlara gore ayrilir.
    """
    parcalar = []
    for satir in (metin or "").splitlines():
        satir = satir.strip()
        if not satir:
            continue
        tip, _ = _tip_bul(satir)
        if tip or satir.startswith(("|", "-", "*", "#")):
            parcalar.append(satir)
        else:
            parcalar.extend(p.strip() for p in _SONLANDIRAN.split(satir)
                            if p.strip())
    return parcalar


# Model dosya adini klasorsuz yazabilir — bu alt klasorlerde de aranir
_ALT_KOKLER = ("", "knowledge", "defter", "data", "Basak", "ui",
               "brain", "tools", "voice", "memory")


def _guvenli_yol(konum):
    """[A] konumunu cozup mutlak yolu dondurur; disari/yasakli ise None."""
    yol = konum.split(":")[0].strip()
    if not yol:
        return None
    kok = os.path.realpath(BASE)
    for alt in _ALT_KOKLER:
        tam = os.path.realpath(os.path.join(kok, alt, yol))
        if tam == kok or tam.startswith(kok + os.sep):
            ad = os.path.basename(tam).lower()
            ust = os.path.basename(os.path.dirname(tam)).lower()
            if any(x in ad or x in ust for x in _YASAKLI):
                return None
            if os.path.isfile(tam):
                return tam
    return None


def _alinti_dogrula(konum, alinti):
    """Alinti, konumdaki dosyanin iceriginde birebir (normalize) var mi?"""
    yol = _guvenli_yol(konum)
    if yol is None or not os.path.isfile(yol):
        return False
    try:
        with open(yol, "r", encoding="utf-8-sig") as f:
            icerik = f.read()
    except (OSError, UnicodeDecodeError, ValueError):
        return False
    return _norm(alinti) in _norm(icerik)


def cikis_kapisi(metin, olcumler=None):
    """Cevabi denetler. Donus: (gecen_metin, rapor).

    olcumler: bu turda calisan arac ciktilarinin metinleri;
    [O] cumleleri bunlara karsi dogrulanir.
    """
    olcum_norm = [_norm(o) for o in (olcumler or []) if o]

    gecen, rapor = [], []
    gecen_o_nolari = set()

    for cumle in bol_cumleler(metin):
        tip, no = _tip_bul(cumle)

        if tip is None:
            rapor.append("SILINDI (isaretsiz): " + cumle[:80])

        elif tip == "B":
            gecen.append(cumle)

        elif tip == "A":
            alinti = _ALINTI.search(cumle)
            konum = _KONUM_A.match(cumle)
            if (alinti and konum
                    and _alinti_dogrula(konum.group(1), alinti.group(1))):
                gecen.append(cumle)
            else:
                rapor.append("SILINDI ([A] dogrulanamadi): " + cumle[:80])

        elif tip == "O":
            alinti = _ALINTI.search(cumle)
            dogru = bool(alinti) and any(
                _norm(alinti.group(1)) in o for o in olcum_norm)
            if dogru:
                gecen.append(cumle)
                if no:
                    gecen_o_nolari.add(no)
            else:
                rapor.append("SILINDI ([O] bu turun ciktisinde yok): "
                             + cumle[:80])

        elif tip == "C":
            dayanaklar = _DAYANAK.findall(cumle)
            if len(dayanaklar) >= 2 and all(d in gecen_o_nolari
                                            for d in dayanaklar):
                gecen.append(cumle)
            else:
                rapor.append("SILINDI ([C] dayanak eksik): " + cumle[:80])

    temiz = "\n".join(gecen).strip()
    if rapor and temiz:
        temiz += "\n\n" + YEDEK_CUMLE
    elif rapor:
        temiz = YEDEK_CUMLE

    if rapor:
        logger.info("Olcu kapisi %d cumleyi eledi", len(rapor))
    return temiz, rapor


PROMPT_BLOGU = (
    "\nCEVAP BİÇİMİ — ÖLÇÜ KURALI (ZORUNLU):\n"
    "Her cümle şu işaretlerden biriyle BAŞLAR:\n"
    '1) Belge/not/defter alıntısı → [A] dosya-adi.md "belgedeki satırın '
    'AYNISI"\n'
    '   (bağlamdaki not bloklarının başlığında dosya adı yazar; örn: '
    '[A] casper-hakkinda.md "Furkan Ankara\'da yaşıyor")\n'
    "2) Bu turda çalıştırdığın aracın çıktısı → "
    '[Ö1] arac-adı "aracın döndürdüğü metnin AYNISI"\n'
    "3) En az iki ölçümden çıkardığın sonuç → "
    "[Ç] [Ö1][Ö2] tek cümlelik sonuc\n"
    "4) Bilmiyorsan, bağlamda kaynağı yoksa, geleceğe dönükse ya da "
    "sohbet/nezaketse → [B] kısa açıklama\n"
    "KURALLAR: Bir cümlede TEK alıntı olur. Alıntı AYNEN taşınır. "
    "İşaretsiz cümle ile uydurma alıntı CEVAPTAN SİLİNİR — sessiz kalmak "
    "yanlış bilgi vermekten iyidir.\n"
)
