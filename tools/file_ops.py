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


def _guvenli_yolu_coz(yol, base_dir):
    """Yolu tek merkezi kuralla cozer.

    Donus: (izinli, etiket|mesaj, mutlak_yol)
      - izinli=True : etiket 'dis:<ad>' veya izinli klasor adi,
        mutlak_yol = realpath uygulanmis acilacak yol
      - izinli=False: mesaj hata aciklamasi, mutlak_yol None
    """
    try:
        if not yol or not str(yol).strip():
            return False, "Dosya yolu boş olamaz", None

        dis_ad = _dis_proje_adi(yol)
        if dis_ad:
            rel = _dis_rel_yol(yol, dis_ad)
            dis_kok = DIS_PROJELER[dis_ad]
            if rel is None:
                return False, "Geçersiz dış proje yolu: %s" % yol, None
            mutlak = os.path.realpath(
                os.path.join(dis_kok, rel)) if rel else _gercek_norm_kok(dis_kok)
            if not _altinda_mi(mutlak, dis_kok):
                return False, "Yol dış proje dizininin dışında", None
            return True, "dis:%s" % dis_ad, mutlak

        # İç yol — realpath ile çöz (junction/symlink dahil)
        mutlak = os.path.realpath(os.path.join(base_dir, yol))
        kok = os.path.realpath(base_dir)

        if not _altinda_mi(mutlak, kok):
            return False, "Yol proje dizininin dışında", None

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


def write_file_ops(yol: str, icerik: str, base_dir: str) -> dict:
    """Bir dosyaya yazar.

    Sadece izin verilen klasörlere yazar. Dosya yoksa oluşturur.
    Guvenlik: hedef realpath ile cozulmustur — izinli klasor icindeki
    disari bakan symlink/junction'a yazim BLOKLANIR.
    """
    if not yol or not yol.strip():
        return {"error": "Dosya yolu boş olamaz"}
    if not icerik:
        return {"error": "İçerik boş olamaz"}

    izinli, mesaj, mutlak_yol = _guvenli_yolu_coz(yol, base_dir)
    if not izinli:
        return {"error": mesaj}

    # E-1: Dış projelere yazma yasak (salt okunur)
    if mesaj.startswith("dis:"):
        return {"error": ("Güvenlik engeli: '%s' dış projesine yazma izni yok. "
                          "Dış projeler salt okunur.") % mesaj.split(":")[1]}

    try:
        klasor = os.path.dirname(mutlak_yol)
        os.makedirs(klasor, exist_ok=True)

        with open(mutlak_yol, "w", encoding="utf-8") as f:
            f.write(icerik)

        return {"result": f"Dosya yazıldı: {yol}"}

    except OSError as e:
        return {"error": f"Dosya yazılamadı: {e}"}


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
