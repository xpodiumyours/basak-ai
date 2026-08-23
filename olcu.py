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

_MARKER = re.compile(r"^\[(Ö|O|Ç|C|B|A|Y)\s*(\d*)\]", re.IGNORECASE)
_ALINTI = re.compile(r'"([^"]{3,400})"')
_KONUM_A = re.compile(r'^\[A\]\s*([^\s"]+)', re.IGNORECASE)
# [Ö1] arac-adi "cikti" → cumlenin dayandigini SOYLEDIGI arac
_KONUM_O = re.compile(r'^\[(?:Ö|O)\s*\d*\]\s*([^\s"]+)', re.IGNORECASE)
_DAYANAK = re.compile(r"\[(?:Ö|O)\s*(\d+)\]", re.IGNORECASE)

# [B] eylem denetimi (2026-08-23 olculen gercek ariza): model yapmadigi isi
# "[B] ... deftere kaydedildi" diyebiliyordu — [B] kapidan serbest geciyor,
# icerigi hicbakilmadan yasiyordu. Eylem iddiasi tasiyan [B] cumlesi,
# ilgili arac O TURDA basarili calismadiysa elenir.
_YAZMA_ARACLARI = frozenset((
    "deftere_kaydet", "save_note", "add_task", "complete_task",
    "write_file_tool",
))
# (desen, iddiayi kanitlayabilecek araclar) — sirasi onemli, ozeli once dener.
# Bos liste = hicbir arac kanitlayamaz (silme/gonderme araci yok).
_EYLEM_DESENLERI = (
    (r"\bdefter\w*\b", ("deftere_kaydet",)),
    (r"\bnot\w*\s+(?:al|dus|kayd)|kayd\w*\s+not",
     ("save_note", "deftere_kaydet")),
    (r"\bgorev\w*\s+(?:liste\w*\s+)?ekle|\bekle\w*\s+gorev", ("add_task",)),
    (r"\bgorev\w*.{0,40}(?:tamamla|isaretl)|tamamladim|isaretledim",
     ("complete_task",)),
    (r"\bdosya\w*.{0,40}(?:yazil|olusturul|guncellen)",
     ("write_file_tool",)),
    (r"\bsil(?:in)?di\b|\bsildim\b|\bgonder(?:il)?di\b|\bgonderdim\b", ()),
    (r"kaydedildi|kaydettim|eklendi|ekledim|olusturuldu|olusturdum|"
     r"guncellendi|guncelledim|yazildi",
     _YAZMA_ARACLARI),
)
# Olumsuz eylem ("eklenmedi") iddia degildir — dogru soyleyen elenmez
_OLUMSUZ_EYLEM = (
    "kaydetmedim", "kaydedilmedi", "eklemedim", "eklenmedi", "silmedim",
    "silinmedi", "gondermedim", "gonderilmedi", "yazmadi", "yazilmadi",
    "olusturmadi", "olusturulmadi", "guncellemedim", "guncellenmedi",
    "tamamlamadi", "tamamlanmadi", "isaretlemedim", "isaretlenmedi",
)

_SONLANDIRAN = re.compile(
    r'(?<=[.!?…])\s+(?=["«(\[]?[A-ZÀ-ÞĞİÖŞÜ0-9\-\|])')

YEDEK_CUMLE = "Bunu ölçemedim."


# Araclar ASCII Turkce dondurur, model duzgun Turkce alintilar;
# karsilastirma oncesi karakterler esitlenir (icerik degismez, sesli harf kalinir)
_TURKCE_FOLD = str.maketrans({
    "ı": "i", "I": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
})


def _isaret_degistir(cumle, tip):
    """Cümlenin [Ö]/[A]/[Ç]/[B] prefix'ini silip badge::X:: marker'ı ekler."""
    m = _MARKER.match(cumle)
    if m:
        return "badge::" + tip + "::" + cumle[m.end():].strip()
    return cumle


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


# İşaretsiz geçişte tehlike sinyalleri (ölçü-alanı): bu izler cümlede
# varsa "sohbet" sayılmaz, kanıt bekler.
_PROJE_ADLARI = ("vixrex", "numeramatch", "xses")
_COMMIT_HASH = re.compile(r"\b[0-9a-f]{7,40}\b")


def _isaretsiz_gecis(tum_cumleler):
    """İşaretsiz + araçsız cevap için yumuşak denetim.

    Düz sohbet cümleleri olduğu gibi yaşar; yalnız ölçü-alanı sinyali
    (proje adı / commit hash / eylem iddiası) taşıyan cümleler elenir —
    bunlar işaretle ve kanıtla gelmek zorundadır.
    """
    hayatta, rapor = [], []
    for cumle in tum_cumleler:
        norm = _norm(cumle)
        tehlike = (any(p in norm for p in _PROJE_ADLARI)
                   or bool(_COMMIT_HASH.search(norm))
                   or _b_eylem_denetimi(cumle, []))
        if tehlike:
            rapor.append("SILINDI (isaretsiz olcu/eylem iddiasi): "
                         + cumle[:80])
        else:
            hayatta.append(cumle)
    temiz = "\n".join(hayatta).strip()
    if rapor and temiz:
        temiz += "\n\n" + YEDEK_CUMLE
    elif rapor:
        temiz = YEDEK_CUMLE
    if rapor:
        logger.info("Olcu kapisi %d isaretsiz tehlikeli cumleyi eledi",
                    len(rapor))
    return temiz, rapor


def _b_eylem_denetimi(cumle, olcum_kayitlari):
    """Eylem iddialı [B] cümlesini bu turun araç geçmişine karşı denetler.

    Dönüş: True = cümle elenmeli (iddia kanıtsız), False = geçebilir.
    Kural: [B] bilmiyorum/ölçülemez içindir; "kaydedildi/eklendi" gibi bir
    eylem iddiası, o eylemi yapan aracın O TURDA hatasız koşmuş olmasını
    gerektirir. Hata döndüren aracın çıktısı ("Hata: ...") kanıt sayılmaz.
    """
    norm = _norm(cumle)
    if any(x in norm for x in _OLUMSUZ_EYLEM):
        return False
    gerekenler = None
    for desen, araclar in _EYLEM_DESENLERI:
        if re.search(desen, norm):
            # Kayitlardaki arac adlari _norm'dan gecmis (alt cizgiler
            # soyulur) — karsilastirma ayni normalizasyonla yapilir.
            gerekenler = {_norm(a) for a in araclar}
            break
    if not gerekenler:
        return bool(gerekenler is not None)
    for ad, cikti in olcum_kayitlari:
        if _norm(ad) in gerekenler and not cikti.startswith("hata:"):
            return False
    return True


def cikis_kapisi(metin, olcumler=None):
    """Cevabi denetler. Donus: (gecen_metin, rapor).

    olcumler: bu turda calisan arac ciktilari. Iki bicim kabul edilir:
      - ["cikti metni", ...]                  (eski bicim)
      - [("arac_adi", "cikti metni"), ...]    (kaynak bilgili bicim)
    [O] cumleleri bunlara karsi dogrulanir.

    Kaynak bilgili bicimde ATIF da denetlenir: cumle "[Ö] list_files ..."
    diyorsa alinti list_files'in ciktisinda gecmeli. Baska bir aracin
    ciktisindan alinip bu araca mal edilen cumle elenir — 2026-08-23'te
    olculen gercek arıza: list_files o klasore bakamazken model uc dosya
    adi sayip [Ö] rozeti takti, cunku metin BASKA bir aracin ciktisinda
    geciyordu.

    Sohbet/nezaket cevaplari (hicbir cumlede isaret yoksa) oldugu gibi
    gecer — kucuk modeller (qwen2.5:3b) sohbette isaret kullanmaz,
    hepsini silmek konusmayi oldurur.
    """
    # Her iki bicimi de tek yapiya indir: [(arac_adi|None, normalize_cikti)]
    olcum_kayitlari = []
    for o in (olcumler or []):
        if isinstance(o, (tuple, list)) and len(o) == 2:
            ad, cikti = o   # DIKKAT: `metin` fonksiyonun kendi parametresi
            if cikti:
                olcum_kayitlari.append((_norm(ad) if ad else None, _norm(cikti)))
        elif o:
            olcum_kayitlari.append((None, _norm(o)))
    olcum_norm = [m for _, m in olcum_kayitlari]
    # Atif denetimi ancak arac adlari biliniyorsa yapilabilir
    bilinen_araclar = {ad for ad, _ in olcum_kayitlari if ad}

    tum_cumleler = bol_cumleler(metin)
    hic_isaret_var_mi = any(_tip_bul(c)[0] is not None for c in tum_cumleler)

    gecen, rapor = [], []
    gecen_o_nolari = set()
    # [Y] cumleleri once yer tutucu olarak girer; ayni cevapta ayakta kalan
    # bir [O]/[A] varsa yasar, yoksa elenir (dayanaksiz yorum cikmasin).
    y_yerleri = []
    dayanak_hayatta = False

    # İşaretsiz serbest geçişi iki istisna sıkar (2026-08-23, Casper'in
    # bulduğu açık: "sohbet" varsayımı denetimsizdi, uydurma olgu kaçardı):
    # (a) bu turda araç koştuysa tam denetim — ölçüm turu işaretsiz geçemez;
    # (b) araçsız turda bile cümle ölçü-alanı sinyali (proje adı / commit
    #     hash) veya eylem iddiası taşıyorsa o cümle elenir. Düz sohbet
    #     (selam, fikir, plan) olduğu gibi yaşar — küçük model konuşması
    #     öldürülmez.
    if not hic_isaret_var_mi and tum_cumleler:
        if olcum_kayitlari:
            gecen = []
            rapor = ["SILINDI (isaretsiz — ölçüm turunda işaret zorunlu): "
                     + c[:80] for c in tum_cumleler]
            temiz = YEDEK_CUMLE
            logger.info("Olcu kapisi %d isaretsiz cumleyi eledi "
                        "(olcum turu)", len(rapor))
            return temiz, rapor
        return _isaretsiz_gecis(tum_cumleler)

    for cumle in tum_cumleler:
        tip, no = _tip_bul(cumle)

        if tip is None:
            rapor.append("SILINDI (isaretsiz): " + cumle[:80])

        elif tip == "B":
            if _b_eylem_denetimi(cumle, olcum_kayitlari):
                rapor.append("SILINDI ([B] eylem iddiası — ilgili araç bu "
                             "turda çalışmadı): " + cumle[:80])
                continue
            gecen.append(_isaret_degistir(cumle, "B"))

        elif tip == "Y":
            # Kararı sona birakiyoruz: dayanak ayakta mi, cevabin tamami
            # denetlenmeden bilinmez.
            y_yerleri.append(len(gecen))
            gecen.append(_isaret_degistir(cumle, "Y"))

        elif tip == "A":
            alinti = _ALINTI.search(cumle)
            konum = _KONUM_A.match(cumle)
            if (alinti and konum
                    and _alinti_dogrula(konum.group(1), alinti.group(1))):
                gecen.append(_isaret_degistir(cumle, "A"))
                dayanak_hayatta = True
            else:
                rapor.append("SILINDI ([A] dogrulanamadi): " + cumle[:80])

        elif tip == "O":
            alinti = _ALINTI.search(cumle)
            iddia = _KONUM_O.match(cumle)
            iddia_edilen = _norm(iddia.group(1)) if iddia else None

            if not alinti:
                rapor.append("SILINDI ([O] alinti yok): " + cumle[:80])
                continue

            aranan = _norm(alinti.group(1))

            if iddia_edilen and bilinen_araclar:
                # Cumle bir arac adi veriyor: alinti O aracin ciktisinda olmali.
                if iddia_edilen not in bilinen_araclar:
                    rapor.append("SILINDI ([O] bu turda calismayan araca "
                                 "atfedildi): " + cumle[:80])
                    continue
                kaynaklar = [m for ad, m in olcum_kayitlari
                             if ad == iddia_edilen]
                if not any(aranan in m for m in kaynaklar):
                    rapor.append("SILINDI ([O] atif yanlis — metin o aracin "
                                 "ciktisinda yok): " + cumle[:80])
                    continue
            elif not any(aranan in m for m in olcum_norm):
                rapor.append("SILINDI ([O] bu turun ciktisinde yok): "
                             + cumle[:80])
                continue

            gecen.append(_isaret_degistir(cumle, "Ö"))
            dayanak_hayatta = True
            if no:
                gecen_o_nolari.add(no)

        elif tip == "C":
            dayanaklar = _DAYANAK.findall(cumle)
            if len(dayanaklar) >= 2 and all(d in gecen_o_nolari
                                            for d in dayanaklar):
                gecen.append(_isaret_degistir(cumle, "Ç"))
            else:
                rapor.append("SILINDI ([C] dayanak eksik): " + cumle[:80])

    # [Y] ancak ayakta kalan bir olcume/alintiya yaslanabilir
    if y_yerleri and not dayanak_hayatta:
        for i in reversed(y_yerleri):
            rapor.append("SILINDI ([Y] dayanaksiz — ayakta olcum/alinti yok): "
                         + gecen[i][:80])
            del gecen[i]

    temiz = "\n".join(gecen).strip()
    if rapor and temiz:
        temiz += "\n\n" + YEDEK_CUMLE
    elif rapor:
        temiz = YEDEK_CUMLE

    if rapor:
        logger.info("Olcu kapisi %d cumleyi eledi", len(rapor))
    return temiz, rapor


HAM_BASLIK = "Cümleyi kuramadım, ölçümün kendisi şu:"


def ham_olcum_satirlari(olcumler, sinir=400):
    """Model cumlesi elendiginde gosterilecek GERCEK olcum satirlari.

    Kapi modelin cumlesini eledigi zaman kullaniciya bos ekran birakmak
    dogru degil: olcum gercekten alindiysa ham hali gosterilir. Bu satirlari
    model degil KOD uretir — bu yuzden birebirligi tanim geregi kesindir.
    """
    satirlar = []
    for o in (olcumler or []):
        if isinstance(o, (tuple, list)) and len(o) == 2:
            ad, cikti = o
        else:
            ad, cikti = "", o
        cikti = re.sub(r"\s+", " ", str(cikti or "")).strip()
        if not cikti:
            continue
        if len(cikti) > sinir:
            cikti = cikti[:sinir].rstrip() + "..."
        cikti = cikti.replace('"', "'")
        satirlar.append('badge::Ö::%s "%s"' % (ad or "araç", cikti))
    return satirlar


PROMPT_BLOGU = (
    "\nCEVAP BİÇİMİ — ÖLÇÜ KURALI (ZORUNLU):\n"
    "Ölçüm ya da alıntı yaptıysan cevabın İLK satırı [Y] olsun: sorunun "
    "cevabını sade Türkçe, tek cümlede söyle. Kanıt satırları ([Ö]/[A]) "
    "onun ALTINA gelir. Kullanıcı önce cevabı okur, kanıtı sonra.\n"
    "Her cümle şu işaretlerden biriyle BAŞLAR:\n"
    "0) Ölçüme/alıntıya dayanan sade cevap cümlesi → [Y] cevap\n"
    "   (yeni olgu EKLEME — yalnız altındaki ölçümü insan diline çevir; "
    "ölçüm yoksa [Y] kullanma)\n"
    '1) Belge/not/defter alıntısı → [A] dosya-adi.md "belgedeki satırın '
    'AYNISI"\n'
    '   (bağlamdaki not bloklarının başlığında dosya adı yazar; örn: '
    '[A] casper-hakkinda.md "Furkan Ankara\'da yaşıyor")\n'
    "2) Bu turda çalıştırdığın aracın çıktısı → "
    '[Ö1] arac-adı "çıktıdan KISA birebir parça" — sonra kendi '
    "cümlenle Türkçe anlat\n"
    "   Alıntı kanıttır, cevap değildir: en fazla bir-iki satır al, "
    "gerisini insan gibi anlat. Çıktının tamamını yapıştırma.\n"
    '   DOĞRU: [Ö1] git_durum "Dal: main" — VixRex şu an main dalında, '
    "son commit Faz 4 değişikliği.\n"
    '   YANLIŞ: [Ö1] git_durum "Proje: vixrex Dal: main Son commit: '
    '20da1a7 | 2026-08-23 16:31 | feat(vitrin)... Commit edilmemis '
    'dosya: 2 ??..."\n'
    "3) En az iki ölçümden çıkardığın sonuç → "
    "[Ç] [Ö1][Ö2] tek cümlelik sonuc\n"
    "4) Bilmiyorsan, bağlamda kaynağı yoksa, geleceğe dönükse ya da "
    "sohbet/nezaketse → [B] kısa açıklama\n"
    "KURALLAR: Bir cümlede TEK alıntı olur. Alıntı AYNEN taşınır. "
    "[Ö] cümlesinde yazdığın araç adı, o metni GERÇEKTEN döndüren araç "
    "olmalı — başka aracın çıktısını ona mal edersen cümle silinir. "
    "[B]'de eylem iddiası YOKTUR: 'kaydettim/eklendi/silindi' gibi yaptığın "
    "bir işi söylüyorsan ilgili araç o turda GERÇEKTEN çalışmış olmalı, "
    "yoksa cümle silinir. "
    "Araç izin vermediyse ya da hata döndürdüyse [B] ile söyle. "
    "İşaretsiz cümle ile uydurma alıntı CEVAPTAN SİLİNİR — sessiz kalmak "
    "yanlış bilgi vermekten iyidir.\n"
)
