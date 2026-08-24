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


# [Y] bağlantı denetimi (2026-08-23, Casper'in bulduğu açık): [Y] yalnızca
# cevapta HERHANGİ bir ölçüm ayakta kaldığı için geçiyordu; gerçek git
# çıktısının altına alakasız bir [Y] iddiası sızabiliyordu. Kapı semantik
# anlamaz — ama sözcük çapası denetleyebilir: [Ö]'ye yaslanan [Y], hayatta
# kalan ölçüm alıntısıyla en az bir içerik kökü paylaşmalı (Türkçe eklerine
# toleranslı: dal ↔ dalında). Salt-[A] durumunda denetim uygulanmaz — alıntı
# belgeyi kanıtlar, iddia bağlamdaki geniş notlardan gelebilir.
_Y_DURAK = frozenset((
    "bir", "ve", "ile", "icin", "bu", "su", "var", "yok", "daha", "gore",
    "olarak", "degil", "ama", "veya", "gibi", "kadar", "sonra", "once",
    "hangi", "cok", "en", "diye", "sey", "sen", "ben", "bunu", "buna",
    "the", "and",
))


def _icerik_kokleri(metin):
    """Durak ve kısa parçalar dışındaki içerik tokenleri (normalize metin)."""
    return {t for t in re.findall(r"[a-z0-9]+", metin)
            if len(t) >= 3 and t not in _Y_DURAK}


def _baglanti_var_mi(cumle, kanit_alintilari):
    """[Y] cümlesi kanıt alıntılarıyla içerik kökü paylaşıyor mu?"""
    y_tok = _icerik_kokleri(_norm(cumle))
    k_tok = set()
    for m in kanit_alintilari:
        k_tok |= _icerik_kokleri(m)
    for t in y_tok:
        if t in k_tok:
            return True
        for k in k_tok:
            kisa, uzun = (t, k) if len(t) <= len(k) else (k, t)
            if len(kisa) >= 3 and kisa in uzun:
                return True
    return False


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
    o_hayatta_alintilar = []   # ayakta kalan [Ö] alıntıları (normalize)

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
            y_yerleri.append((len(gecen), cumle))
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
            o_hayatta_alintilar.append(aranan)
            if no:
                gecen_o_nolari.add(no)

        elif tip == "C":
            dayanaklar = _DAYANAK.findall(cumle)
            if len(dayanaklar) >= 2 and all(d in gecen_o_nolari
                                            for d in dayanaklar):
                gecen.append(_isaret_degistir(cumle, "Ç"))
            else:
                rapor.append("SILINDI ([C] dayanak eksik): " + cumle[:80])

    # [Y] temizliği — iki kural:
    # 1) Ayakta [Ö] varsa: her [Y] hayatta kalan ölçüm alıntısıyla sözcük
    #    çapası paylaşmalı; alakasız iddia elenir.
    # 2) Hiç dayanak ayakta kalmadıysa: tüm [Y]'ler düşer (eski davranış).
    if y_yerleri:
        if o_hayatta_alintilar:
            for i, y_cumle in reversed(y_yerleri):
                if not _baglanti_var_mi(y_cumle, o_hayatta_alintilar):
                    rapor.append("SILINDI ([Y] kanitla baglantisi yok): "
                                 + y_cumle[:80])
                    del gecen[i]
        elif not dayanak_hayatta:
            for i, _c in reversed(y_yerleri):
                rapor.append("SILINDI ([Y] dayanaksiz — ayakta olcum/alinti "
                             "yok): " + gecen[i][:80])
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


# ---------------------------------------------------------------------------
# FAZ 1.2 — Cevap sözleşmesi kapısı (answer contract gate)
#
# Model artık işaretli serbest metin yerine TEK bir JSON sözleşme üretir:
#   {"yanit": ..., "iddialar": [{"metin","tur","dayanak":{"arac"}}]}
# Kapı; beyan edilen "olcum" iddialarını bu turda koşan araçlara karşı
# denetler, beyan edilmemiş eylem/ölçüm cümlelerini eler. Düz sohbet sözleşme
# modunda asla elenmez. Kapı yine yapay zeka değil; yapı + sözcük kontrolü.

import json

SOZLESME_PROMPTU = (
    'CEVAP SOZLESMESI (ZORUNLU): Yalnizca kucultulmus JSON dondur; baska '
    "metin, markdown citi veya aciklama YOK. Sem:\n"
    '{"yanit":"<kullaniciya gorunecek tam cevap>","iddialar":[{"metin":'
    '"<yanit icindeki iddia cumlesi/koku>","tur":"olcum"|"yok",'
    '"dayanak":{"arac":"<arac adi>"}}]}\n'
    'tur "olcum" = dosya/git/gorev/sistem hakkindaki HER olgu veya eylem '
    "iddiasi; dayanak.arac bu iddiayi KANITLAYAN aracin TAM adi olmali "
    "(git_durum, list_tasks gibi). Emin degilsen iddia bildirme, supheni "
    'yanit icinde duz cumleyle soyle. Gorus/sohbet icin tur "yok"; salt '
    'konusmada iddialar: [] birak.\n'
    'Ornek: {"yanit":"Gorev listenizde 2 acik gorev var.","iddialar":'
    '[{"metin":"2 acik gorev var","tur":"olcum","dayanak":{"arac":'
    '"list_tasks"}}]}'
)

_SOZLESME_TURLERI = frozenset(("olcum", "yok"))

# Beyan edilmemis eylem kokleri — _norm Turkce katlamasiyla eslesir,
# noktali/noktasiz yazim farkini tek kok yakalar (tamamlandi == tamamlandı).
_EYLEM_KOKLERI = frozenset((
    "kaydedildi", "kaydettim", "eklendi", "ekledim", "silindi", "sildim",
    "tamamlandi", "tamamlandı", "olusturuldu", "oluşturuldu",
    "yazildi", "yazıldı", "guncellendi", "güncellendi",
    "gonderildi", "gönderildi", "ayarlandi", "ayarlandı",
    "kuruldu", "kurdum", "bulundu", "listedim",
))

# Olcu-alani sinyali: arac kosan turda beyansiz gecemez (AGENTS.md §18 felsefesi)
_DOSYA_YOLU = re.compile(
    r"(?:[\w\-.]+/)+[\w\-.]+|\b[\w\-.]+\.(?:py|md|txt|json|toml|ya?ml|"
    r"cfg|ini|html|css|js|ts|sh|bat)\b")


def _eylem_sinyali(norm_cumle):
    """Pozitif eylem kökü var mı? Olumsuz ('eklenmedi') iddia değildir."""
    if not norm_cumle:
        return False
    if any(x in norm_cumle for x in _OLUMSUZ_EYLEM):
        return False
    return any(k in norm_cumle for k in _EYLEM_KOKLERI)


def _olcu_alani_sinyali(norm_cumle):
    """Ölçü-alanı izi: proje adı / commit hash / dosya yolu / dal-commit."""
    if not norm_cumle:
        return False
    if any(p in norm_cumle for p in _PROJE_ADLARI):
        return True
    if _COMMIT_HASH.search(norm_cumle) or _DOSYA_YOLU.search(norm_cumle):
        return True
    return "dal:" in norm_cumle or "commit" in norm_cumle


def sozlesme_gecerli_mi(s):
    """Sözleşme şeması denetimi. Ekstra anahtarlar umursanmaz."""
    try:
        if not isinstance(s, dict):
            return False
        yanit = s.get("yanit")
        if not isinstance(yanit, str) or not yanit.strip():
            return False
        iddialar = s.get("iddialar")
        if not isinstance(iddialar, list):
            return False
        for i in iddialar:
            if not isinstance(i, dict):
                return False
            metin = i.get("metin")
            if not isinstance(metin, str) or not metin.strip():
                return False
            if i.get("tur") not in _SOZLESME_TURLERI:
                return False
            if i["tur"] == "olcum":
                dayanak = i.get("dayanak")
                arac = dayanak.get("arac") if isinstance(dayanak, dict) else None
                if not isinstance(arac, str) or not arac.strip():
                    return False
        return True
    except Exception:
        return False


def _dengeli_json_bul(metin):
    """İlk dengeli {...} bloğu; string içi süslü parantez ve kaçışlı
    tırnak saygılı. Yoksa None."""
    baslangic = metin.find("{")
    while baslangic != -1:
        derinlik = 0
        icinde_str = kacti = False
        for i in range(baslangic, len(metin)):
            c = metin[i]
            if icinde_str:
                if kacti:
                    kacti = False
                elif c == "\\":
                    kacti = True
                elif c == '"':
                    icinde_str = False
                continue
            if c == '"':
                icinde_str = True
            elif c == "{":
                derinlik += 1
            elif c == "}":
                derinlik -= 1
                if derinlik == 0:
                    return metin[baslangic:i + 1]
        baslangic = metin.find("{", baslangic + 1)
    return None


def sozlesme_coz(metin):
    """Ham model çıktısından sözleşme JSON'unu çıkarır: dict | None.

    ```json çitlerini ve çevre prosi soyar, ilk dengeli {...} bloğunu
    bulur; şema geçerliyse dict döndürür. Asla yükseltmez.
    """
    try:
        ham = metin
        if isinstance(ham, bytes):
            ham = ham.decode("utf-8", errors="replace")
        ham = str(ham or "")
        ham = re.sub(r"```(?:json)?", "", ham)
        blok = _dengeli_json_bul(ham)
        if not blok:
            return None
        veri = json.loads(blok)
        if sozlesme_gecerli_mi(veri):
            return veri
        return None
    except Exception:
        return None


def sozlesme_kapisi(sozlesme, olcumler=None):
    """Sözleşme kapısı: (temiz_metin, rapor).

    olcumler: cikis_kapisi ile aynı bicim — [("arac","cikti")] veya
    ["cikti"]. Dönüşteki rapor:
      {"kullanan_yapi", "gecerli", "elnen_sayisi", "elennen",
       "kosan_araclar"}
    Tüm cümle elenirse araç koştuysa HAM ölçüm satırları, koşmadıysa
    YEDEK_CUMLE döndürülür. Asla yükseltmez.
    """
    rapor = {"kullanan_yapi": True, "gecerli": False, "elnen_sayisi": 0,
             "elennen": [], "kosan_araclar": []}
    try:
        if isinstance(sozlesme, str):
            sozlesme = sozlesme_coz(sozlesme)
        if not sozlesme_gecerli_mi(sozlesme):
            return YEDEK_CUMLE, rapor
        rapor["gecerli"] = True

        # cikis_kapisi ile aynı normalizasyon: [(arac|None, cikti)]
        kayitlar = []
        for o in (olcumler or []):
            if isinstance(o, (tuple, list)) and len(o) == 2:
                ad, cikti = o
                if cikti:
                    kayitlar.append((_norm(ad) if ad else None, cikti))
            elif o:
                kayitlar.append((None, o))
        kosan = {ad for ad, _ in kayitlar if ad}
        rapor["kosan_araclar"] = sorted(kosan)

        cumleler = bol_cumleler(sozlesme.get("yanit"))
        normlar = [_norm(c) for c in cumleler]

        # İddia → cümle eşlemesi (normalize alt-küme, iki yönlü)
        beyanli, kanitsiz = set(), set()
        for iddia in (sozlesme.get("iddialar") or []):
            metin_norm = _norm(iddia.get("metin") or "")
            yer = None
            if metin_norm:
                for i, n in enumerate(normlar):
                    if n and (metin_norm in n or n in metin_norm):
                        yer = i
                        break
            if yer is None:
                continue
            beyanli.add(yer)
            if iddia.get("tur") == "olcum":
                dayanak = iddia.get("dayanak")
                arac = _norm(dayanak.get("arac")) \
                    if isinstance(dayanak, dict) else ""
                if arac and arac not in kosan:
                    kanitsiz.add(yer)

        hayatta, elennen = [], []
        for i, cumle in enumerate(cumleler):
            n = normlar[i]
            if i in kanitsiz:
                elennen.append({"metin": cumle, "neden": "kanit_yok"})
            elif i in beyanli:
                hayatta.append(cumle)
            elif _eylem_sinyali(n):
                elennen.append(
                    {"metin": cumle, "neden": "beyan_edilmemis_eylem"})
            elif kosan and _olcu_alani_sinyali(n):
                elennen.append(
                    {"metin": cumle, "neden": "olcum_alani_beyansiz"})
            else:
                hayatta.append(cumle)

        rapor["elnen_sayisi"] = len(elennen)
        rapor["elennen"] = elennen

        if hayatta:
            return "\n".join(hayatta).strip(), rapor
        if kosan:
            ham = "\n".join(ham_olcum_satirlari(olcumler)).strip()
            return (ham or YEDEK_CUMLE), rapor
        return YEDEK_CUMLE, rapor
    except Exception:
        logger.exception("Sozlesme kapisi beklenmedik hata")
        return YEDEK_CUMLE, rapor
