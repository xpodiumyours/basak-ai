"""tools/file_ops.py — Dosya okuma/yazma araçları.

Sadece izin verilen klasörlerde çalışır (whitelist).
Varsayılan olarak sadece knowledge/ klasörüne izin verilir.
E-1: dış projeler (vixrex, numeramatch, xses) salt-okunur olarak eklendi.
Her işlem loglanır.

Path güvenliği (2026-08-24, Casper'in bulduğu üç açık sonrası):
- Tüm kararlar os.path.realpath üzerinden verilir — symlink/junction
  çözülür, izinli klasör içine konmuş bir bağlantı dışarıyı göstermez
- Sınır kontrolü normcase + commonpath ile yapılır — "vixrex/../vixrex2"
  gibi benzer isimli KOMŞU klasör önek oyunları geçmez
- Yol tek yerde çözülür (_guvenli_yolu_coz); kontrol edilen yol ile
  açılan yol aynı olmak zorundadır
Bilinen sınır: kontrol ile açma arasındaki TOCTOU yarışı kapatılmadı.
"""

import logging
import os

logger = logging.getLogger(__name__)

# İzin verilen iç klasörler (whitelist)
IZINLI_KLASORLER = [
    "knowledge",
    "research-engine",
]

# Windows klasör isim haritası — küçük model "belgeler" dediğinde
# gerçek yola çevirir. Hem Türkçe hem İngilizce isimleri kapsar.
KLASOR_HARITASI = {
    # Türkçe isimler
    "belgeler": "Documents",
    "belge": "Documents",
    "bilgeler": "Documents",   # Yaygın yazım hatası
    "bilge": "Documents",
    "masaustu": "Desktop",
    "masaüstü": "Desktop",
    "indirilenler": "Downloads",
    "indirilen": "Downloads",
    "indirme": "Downloads",
    "resimler": "Pictures",
    "resim": "Pictures",
    "videolar": "Videos",
    "video": "Videos",
    "müzik": "Music",
    "muzik": "Music",
    "belgelerim": "Documents",
    "indirilenlerim": "Downloads",
    "resimlerim": "Pictures",
    "videolarim": "Videos",
    "klasör": None,  # Belirsiz — ev dizinine yönlendir
    "klasor": None,
    "dosyalar": "Documents",   # Yaygın alternatif
    "dosya": "Documents",
    # İngilizce isimler
    "documents": "Documents",
    "desktop": "Desktop",
    "downloads": "Downloads",
    "pictures": "Pictures",
    "videos": "Videos",
    "music": "Music",
}

# 2026-08-24: Casper'in bulgusu — Başak sadece knowledge/ ve research-engine/
# görebiliyor, bilgisayarın diğer dosyaları erişime kapalı. Bu whitelist
# security için gereklidir ama kullanıcının kendi dosyalarına erişimi
# engelliyordu. Çözüm: ev dizini (ve alt klasörlerini) OKUMA açmak,
# YAZMAYA kapalı tutmak. Security bozulmaz — write_file_ops hala
# sadece knowledge/ ve research-engine/'e yazabilir.
# Mutlak yolların izinli kökleri (realpath ile çözülür, connection/symlink
# outside'a bakmaz).
# 2026-08-25: Casper sikayeti — C:\Projects okunamiyordu.
# Okuma tum bilgisayara acildi; yazma bugunki gibi dar kaliyor.
IZINLI_KOKLER = [
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "knowledge"),
    os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                 "research-engine"),
    os.path.expanduser("~"),  # Ev dizini — salt okunur
    r"C:\Projects",          # Proje dizini — salt okunur
]

# Kara liste: OKUMA bile yasak (kimlik/parola sızmasın)
YASAK_YOLLAR = (
    r"C:\Windows",
    r"C:\Program Files",
    r"C:\Program Files (x86)",
    os.path.join(os.path.expanduser("~"), ".ssh"),
    os.path.join(os.path.expanduser("~"), ".aws"),
    os.path.join(os.path.expanduser("~"), ".gnupg"),
    os.path.join(os.path.expanduser("~"), ".config",
                 "manim"),  # tools konsolu
)

# Hassas dosya kaliplari (buyuk/kucuk harf duyarsiz)
YASAK_DOSYA_KALIPLARI = (
    ".env", ".env.",
    ".pem", ".key",
    "id_rsa",
    "ayarlar.json",  # acik API anahtarlari var
)

def _yasak_mi(mutlak_yol):
    """Verilen yol kara listede mi? Buyuk/kucuk harf duyarsiz kontrol."""
    yol_norm = os.path.normcase(os.path.realpath(mutlak_yol))
    # Klasor kara listesi
    for yk in YASAK_YOLLAR:
        if os.path.normcase(os.path.realpath(yk)) == yol_norm or            _altinda_mi(yol_norm, os.path.normcase(os.path.realpath(yk))):
            return True
    # Dosya kaliplari
    dosya_adi = os.path.basename(yol_norm)
    for kaliptir in YASAK_DOSYA_KALIPLARI:
        if kaliptir in dosya_adi:
            return True
    return False

# Hangi kökün ev olduğunu belirlemek için
EV_KOK = os.path.expanduser("~")

# E-1: Dış projeler — salt okunur, yazma yasak.
# Model yol veremez; yalnız bu anahtarlardan seçer.
DIS_PROJELER = {
    "vixrex": r"C:\Projects\vixrex",
    "numeramatch": r"C:\Users\Casper\source\NumeraMatch",
    "xses": r"C:\Projects\xses",
}


def _gercek_norm(p):
    """realpath (bağlantıları çözer) + normcase (Windows kiyas duygusuz)."""
    return os.path.normcase(os.path.realpath(p))


def _altinda_mi(aday, kok):
    """aday, kok'un GERCEK altinda mi? (baglanti/onek oyunlarina kapali)"""
    a, k = _gercek_norm(aday), _gercek_norm(kok)
    if a == k:
        return True
    try:
        return os.path.commonpath([a, k]) == k
    except ValueError:          # farkli suruculer (C:\ vs D:\)
        return False


def _dis_rel_yol(yol, ad):
    """'vixrex/alt/yol' -> 'alt/yol'; 'vixrex' -> ''; uyumsuzsa None."""
    rel = yol.strip()
    low = rel.lower()
    if low == ad:
        return ""
    for one in (ad + "/", ad + "\\"):
        if low.startswith(one):
            return rel[len(ad) + 1:]
    return None


def _klasor_cevir(klasor_adi):
    r"""Kullanicinin tanidigi klasor isimlerini gercek Windows yollarina cevirir.

    'belgeler' -> C:\Users\Casper\Documents
    'masaustu' -> C:\Users\Casper\Desktop
    'bilgisayarimda ki belgeler klasorunde kileri listele' -> Belgeler klasoru

    Donus: (cozulmus_yol, orijinal_mi) -- orijinal_mi=True ise dokunulmamis.
    """
    if not klasor_adi:
        return klasor_adi, True
    temiz = klasor_adi.strip().lower()
    # Tam eşleşme
    if temiz in KLASOR_HARITASI:
        hedef = KLASOR_HARITASI[temiz]
        if hedef is None:
            # Belirsiz "klasör" → ev dizini
            return os.path.expanduser("~"), False
        return os.path.join(os.path.expanduser("~"), hedef), False
    # Kısmi eşleşme: "bilgisayarımdaki belgeler" içinde "belgeler" ara
    for anahtar, hedef in KLASOR_HARITASI.items():
        if anahtar in temiz:
            if hedef is None:
                return os.path.expanduser("~"), False
            return os.path.join(os.path.expanduser("~"), hedef), False
    return klasor_adi, True


def _guvenli_yolu_coz(yol, base_dir):
    """Yolu tek merkezi kuralla cozer.

    Dönüş: (izinli, etiket|mesaj, mutlak_yol)
      - izinli=True : etiket 'dis:<ad>' veya izinli klasor adi,
        mutlak_yol = realpath uygulanmis acilacak yol
      - izinli=False: mesaj hata aciklamasi, mutlak_yol None
    """
    try:
        if not yol or not str(yol).strip():
            return False, "Dosya yolu boş olamaz", None

        # AKILLI YOL ÇEVİRME: "belgeler", "masaüstü" gibi klasör isimlerini
        # gerçek Windows yollarına çevir. Model küçükse doğru yol üretemez.
        cozulmus, orijinal = _klasor_cevir(yol)
        if not orijinal:
            yol = cozulmus

        # MUTLAK YOL — tum bilgisayar (2026-09-09, Casper karari):
        # Basak, Casper'in gordugu her yeri gorebilir: ev, C:\Projects,
        # knowledge/, research-engine/ VE bunlar disindaki tum suruculer.
        # TEK SINIR kara listedir: Windows, Program Files, sifre dosyalari
        # (.env/.pem/.key/id_rsa/ayarlar.json), .ssh/.aws/.gnupg.
        # Gerekce: okuma kimseye zarar vermez; yazma ayrica _yazma_izni
        # ile kilitlidir. Junction/symlink realpath ile cozulur.
        yol_str = str(yol).strip()
        if os.path.isabs(yol_str):
            mutlak = os.path.realpath(yol_str)
            # Kara liste: OKUMA bile yasak
            if _yasak_mi(mutlak):
                return False, "Bu yol kara listede — okuma yasak.", None
            for kok in IZINLI_KOKLER:
                if _altinda_mi(mutlak, os.path.realpath(kok)):
                    if _altinda_mi(mutlak, os.path.realpath(EV_KOK)):
                        return True, "ev", mutlak
                    iliski = os.path.relpath(
                        _gercek_norm(mutlak), _gercek_norm(
                            os.path.realpath(base_dir)))
                    birinci = iliski.split(os.sep)[0]
                    return True, birinci, mutlak
            # Bilinen koklerin disinda ama kara listede degil:
            # tum bilgisayar okumaya acik.
            return True, "bilgisayar", mutlak

        dis_ad = _dis_proje_adi(yol)
        if dis_ad:
            if not _canary_dis_izinli(dis_ad):
                return False, ("Canary modu: '%s' dış projesi "
                               "izinli_projeler listesinde yok."
                               % dis_ad), None
            rel = _dis_rel_yol(yol, dis_ad)
            dis_kok = DIS_PROJELER[dis_ad]
            if rel is None:
                return False, "Geçersiz dış proje yolu: %s" % yol, None
            mutlak = os.path.realpath(
                os.path.join(dis_kok, rel)) if rel else _gercek_norm_kok(dis_kok)
            if not _altinda_mi(mutlak, dis_kok):
                return False, "Yol dış proje dizininin dışında", None
            # 2026-09-09: dis projede bile sifre dosyasi okunmaz.
            if _yasak_mi(mutlak):
                return False, "Bu yol kara listede — okuma yasak.", None
            return True, "dis:%s" % dis_ad, mutlak

        # İç yol — realpath ile çöz (junction/symlink dahil)
        mutlak = os.path.realpath(os.path.join(base_dir, yol))
        kok = os.path.realpath(base_dir)

        if not _altinda_mi(mutlak, kok):
            return False, "Yol proje dizininin dışında", None

        # 2026-09-09: kara liste goreli yolda da gecerli (sifre dosyalari
        # knowledge/ icinde bile okunamaz/yazilamaz).
        if _yasak_mi(mutlak):
            return False, "Bu yol kara listede — okuma yasak.", None

        iliski = os.path.relpath(_gercek_norm(mutlak),
                                 _gercek_norm(kok))
        birinci_klasor = iliski.split(os.sep)[0]

        if birinci_klasor in IZINLI_KLASORLER:
            return True, birinci_klasor, mutlak

        return False, (f"'{birinci_klasor}' klasörüne izin yok. "
                       f"İzinli: {', '.join(IZINLI_KLASORLER)}"), None

    except (ValueError, OSError) as e:
        return False, f"Yol kontrolü hatası: {e}", None


def _gercek_norm_kok(kok):
    """Var olan kokun gercek halini dondurur (normcase'siz, gorunum icin)."""
    return os.path.realpath(kok)


def _dis_proje_adi(yol):
    """E-1: Yol dis projeye mi isaret ediyor? Oyleyse proje adi."""
    if not yol:
        return None
    yol_lower = yol.strip().lower()
    for ad in DIS_PROJELER:
        if yol_lower == ad or yol_lower.startswith(ad + "/") or \
           yol_lower.startswith(ad + "\\"):
            return ad
    return None


def _canary_dis_izinli(ad):
    """CANARY modunda dis projeler yalnizca ayarlardaki izinli_projeler
    listesindeysese acilir. Ayar okunamazsa kilitleme yapmaz (normal
    davranis) — canli test hatti karari icin bakiniz: CANLI-KAPISI.md"""
    try:
        from tools.permissions import _ayar_deger, calisma_modu
        if calisma_modu() != "canary":
            return True
        liste = _ayar_deger("izinli_projeler", []) or []
        return str(ad).lower() in [str(x).lower() for x in liste]
    except Exception:
        return True


# --- Geriye donuk uyumluluk sarmalayicilari -------------------------------

def _dis_proje_ayarla(yol, base_dir):
    """Eski imza: (proje_adi, kok)."""
    ad = _dis_proje_adi(yol)
    return (ad, DIS_PROJELER[ad]) if ad else (None, None)


def _klasor_kontrol(yol, base_dir):
    """Eski iki degerli donus (testler/araclar bozulmasin).

    NOT: cagiran bu sonuctan YOLU kendisi turetmemeli — _guvenli_yolu_coz
    kullanip ucuncu degerdeki cozulmus yolu acmak zorunda.
    """
    izinli, mesaj, _mutlak = _guvenli_yolu_coz(yol, base_dir)
    return izinli, mesaj


def read_file(yol: str, base_dir: str) -> dict:
    """Bir dosyanın içeriğini okur.

    Sadece izin verilen klasörlerdeki dosyaları okur.
    E-1: dış projelerden de okunabilir (salt okunur).
    Max 5000 karakter okunur.
    """
    if not yol or not yol.strip():
        return {"error": "Dosya yolu boş olamaz"}

    izinli, mesaj, mutlak_yol = _guvenli_yolu_coz(yol, base_dir)
    if not izinli:
        return {"error": mesaj}

    try:
        if not os.path.exists(mutlak_yol):
            return {"error": f"Dosya bulunamadı: {yol}"}

        if not os.path.isfile(mutlak_yol):
            return {"error": f"Bu bir dosya değil: {yol}"}

        with open(mutlak_yol, "r", encoding="utf-8", errors="replace") as f:
            icerik = f.read(5000)

        if len(icerik) == 5000:
            icerik += "\n... (ilk 5000 karakter)"

        return {"result": icerik}

    except OSError as e:
        return {"error": f"Dosya okunamadı: {e}"}


# 2026-08-25: Beyaz liste — yazma yalnizca knowledge/ ve research-engine/
# IZINLI_KOKLER'e yeni kok eklendiginde yazma kendiliginden acilmaz.
# 2026-09-09 (Casper karari): yazma ev + C:\Projects'e genisletildi.
# SARTLAR: kara liste disi (sistem/sifre dosyalari), dis projeler HARIC
# (vixrex/numeramatch/xses salt-okunur kalir), junction disari bakamaz.
# knowledge/ ve research-engine/ ONaysiz; DIGER yerlere yazma ONAYLIDIR
# (chat/tools.py onay sorar — Casper "ben nasilsam o da oyle" dedi:
# ben de sormadan dokunmam).
YAZMA_IZINLI_KOKLER = ("knowledge", "research-engine")

# Onaysiz yazilabilen kokler (proje ici not alanlari)
OTOMATIK_YAZMA_KOKLER = ("knowledge", "research-engine")

# Onayla yazilabilen kokler (kullanicinin kendi alanlari)
ONAYLI_YAZMA_KOKLER = (os.path.expanduser("~"), r"C:\Projects")


def _yazma_izni_var_mi(mutlak_yol, base_dir):
    """Yazma izni var mi? (evet/hayir — onay ayri katman)

    knowledge/research-engine: EVET. ev + C:\\Projects: EVET (kara liste
    ve dis projeler haric). Gerisi: HAYIR.
    """
    try:
        if _yasak_mi(mutlak_yol):
            return False
        mutlak_norm = os.path.normcase(os.path.realpath(mutlak_yol))
        # Dis projeler salt-okunur kalir
        for _ad, _kok in DIS_PROJELER.items():
            try:
                kok_norm = os.path.normcase(os.path.realpath(_kok))
                if mutlak_norm == kok_norm or mutlak_norm.startswith(
                        kok_norm + os.sep):
                    return False
            except (OSError, ValueError):
                continue
        base_norm = os.path.normcase(os.path.realpath(base_dir))
        for klasor_adi in YAZMA_IZINLI_KOKLER:
            kok = os.path.normcase(
                os.path.realpath(os.path.join(base_dir, klasor_adi)))
            if mutlak_norm.startswith(kok + os.sep) or mutlak_norm == kok:
                return True
        for kok_ham in ONAYLI_YAZMA_KOKLER:
            try:
                kok = os.path.normcase(os.path.realpath(kok_ham))
            except (OSError, ValueError):
                continue
            if mutlak_norm == kok or mutlak_norm.startswith(kok + os.sep):
                return True
        return False
    except (OSError, ValueError):
        return False


def _otomatik_yazma_mi(mutlak_yol, base_dir):
    """Onaysiz yazilabilir mi? Yalniz knowledge/ ve research-engine/."""
    try:
        mutlak_norm = os.path.normcase(os.path.realpath(mutlak_yol))
        for klasor_adi in OTOMATIK_YAZMA_KOKLER:
            kok = os.path.normcase(
                os.path.realpath(os.path.join(base_dir, klasor_adi)))
            if mutlak_norm.startswith(kok + os.sep) or mutlak_norm == kok:
                return True
        return False
    except (OSError, ValueError):
        return False

def write_file_ops(yol: str, icerik: str, base_dir: str) -> dict:
    """Bir dosyaya yazar.

    KURAL (2026-09-09): knowledge/ ve research-engine/ serbesttir.
    ev + C:\\Projects yazilabilir AMA onay ister (chat/tools.py sorar).
    Kara liste (sistem/sifre) ve dis projeler (vixrex/...) ASLA yazilmaz.
    Guvenlik: hedef realpath ile cozulmustur — izinli klasor icindeki
    disari bakan symlink/junction'a yazim BLOKLANIR.
    """
    if not yol or not yol.strip():
        return {"error": "Dosya yolu bos olamaz"}
    if not icerik:
        return {"error": "Icerik bos olamaz"}

    izinli, mesaj, mutlak_yol = _guvenli_yolu_coz(yol, base_dir)
    if not izinli:
        return {"error": mesaj}

    # BEYAZ LISTE KONTROLU
    if not _yazma_izni_var_mi(mutlak_yol, base_dir):
        return {"error": ("Güvenlik engeli: salt okunur, buraya yazma "
                          "izni yok. Yazılabilir: knowledge/, defter-notları, "
                          "ev klasörün ve C:\\Projects (onayla). "
                          "Sistem ve şifre dosyalarına asla yazılmaz.")}

    try:
        klasor = os.path.dirname(mutlak_yol)
        os.makedirs(klasor, exist_ok=True)

        with open(mutlak_yol, "w", encoding="utf-8") as f:
            f.write(icerik)

        return {"result": f"Dosya yazildi: {yol}"}

    except OSError as e:
        return {"error": f"Dosya yazilamadi: {e}"}


def list_files(klasor: str, base_dir: str) -> dict:
    """Bir klasördeki dosyaları listeler.

    Sadece izin verilen klasörleri listeler.
    E-1: dış projelerin kök klasörleri de listelenebilir.
    """
    if not klasor or not klasor.strip():
        klasor = "knowledge"

    izinli, mesaj, mutlak_yol = _guvenli_yolu_coz(klasor, base_dir)
    if not izinli:
        return {"error": mesaj}

    try:
        if not os.path.isdir(mutlak_yol):
            return {"error": f"Bu bir klasör değil: {klasor}"}

        dosyalar = []
        for ad in sorted(os.listdir(mutlak_yol)):
            tam_yol = os.path.join(mutlak_yol, ad)
            if os.path.isfile(tam_yol):
                boyut = os.path.getsize(tam_yol)
                dosyalar.append(f"  {ad} ({boyut} bayt)")
            elif os.path.isdir(tam_yol):
                dosyalar.append(f"  {ad}/ (klasör)")

        if not dosyalar:
            return {"result": f"{klasor}/ klasörü boş"}

        return {"result": f"{klasor}/ ({len(dosyalar)} öğe):\n" + "\n".join(dosyalar)}

    except OSError as e:
        return {"error": f"Klasör listelenemedi: {e}"}
