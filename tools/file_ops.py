"""tools/file_ops.py — Dosya okuma/yazma araçları.

Sadece izin verilen klasörlerde çalışır (whitelist).
Varsayılan olarak sadece knowledge/ klasörüne izin verilir.
E-1: dış projeler (vixrex, numeramatch, xses) salt-okunur olarak eklendi.
Her işlem loglanır.
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


def _dis_proje_ayarla(yol, base_dir):
    """E-1: Yol dış projeden mi? Öyleyse (proje_adi, mutlak_kok) döner."""
    if not yol:
        return None, None
    yol_lower = yol.strip().lower()
    for ad, kok in DIS_PROJELER.items():
        # "vixrex/AGENTS.md" → "vixrex" eşleşir
        if yol_lower == ad or yol_lower.startswith(ad + "/") or \
           yol_lower.startswith(ad + "\\"):
            return ad, kok
    return None, None


def _klasor_kontrol(yol, base_dir):
    """Verilen yolun izin verilen bir klasör içinde olup olmadığını kontrol eder.

    E-1: Dış projeler de kontrol edilir (salt okunur).
    """
    try:
        # E-1: Dış proje kontrolü — yol "vixrex/..." şeklinde gelir
        dis_proje, dis_kok = _dis_proje_ayarla(yol, base_dir)
        if dis_proje:
            # Dış projede relative yol
            rel_yol = yol.strip()
            if rel_yol.lower().startswith(dis_proje + "/"):
                rel_yol = rel_yol[len(dis_proje) + 1:]
            elif rel_yol.lower().startswith(dis_proje + "\\"):
                rel_yol = rel_yol[len(dis_proje) + 1:]
            mutlak_yol = os.path.abspath(os.path.join(dis_kok, rel_yol))
            if not mutlak_yol.startswith(os.path.realpath(dis_kok)):
                return False, "Yol dış proje dizininin dışında"
            return True, "dis:%s" % dis_proje

        # İç proje kontrolü (mevcut mantık)
        mutlak_yol = os.path.abspath(os.path.join(base_dir, yol))
        base_mutlak = os.path.abspath(base_dir)

        if not mutlak_yol.startswith(base_mutlak):
            return False, "Yol proje dizininin dışında"

        iliski = os.path.relpath(mutlak_yol, base_mutlak)
        birinci_klasor = iliski.split(os.sep)[0]

        if birinci_klasor in IZINLI_KLASORLER:
            return True, birinci_klasor

        return False, f"'{birinci_klasor}' klasörüne izin yok. İzinli: {', '.join(IZINLI_KLASORLER)}"

    except (ValueError, OSError) as e:
        return False, f"Yol kontrolü hatası: {e}"


def read_file(yol: str, base_dir: str) -> dict:
    """Bir dosyanın içeriğini okur.

    Sadece izin verilen klasörlerdeki dosyaları okur.
    E-1: dış projelerden de okunabilir (salt okunur).
    Max 5000 karakter okunur.

    Args:
        yol: Dosya yolu. Dış proje için "vixrex/AGENTS.md" gibi.
        base_dir: Proje kök dizini.

    Returns:
        {"result": str} veya {"error": str}.
    """
    if not yol or not yol.strip():
        return {"error": "Dosya yolu boş olamaz"}

    izinli, mesaj = _klasor_kontrol(yol, base_dir)
    if not izinli:
        return {"error": mesaj}

    try:
        # E-1: Dış proje ise onun kökünden çöz
        if mesaj.startswith("dis:"):
            dis_proje = mesaj.split(":")[1]
            dis_kok = DIS_PROJELER[dis_proje]
            rel_yol = yol.strip()
            if rel_yol.lower().startswith(dis_proje + "/"):
                rel_yol = rel_yol[len(dis_proje) + 1:]
            mutlak_yol = os.path.abspath(os.path.join(dis_kok, rel_yol))
        else:
            mutlak_yol = os.path.abspath(os.path.join(base_dir, yol))

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

    Sadece izin verilen klasörlere yazar.
    Dosya yoksa oluşturur.

    Args:
        yol: Dosya yolu (base_dir'e göre).
        icerik: Yazılacak içerik.
        base_dir: Proje kök dizini.

    Returns:
        {"result": str} veya {"error": str}.
    """
    if not yol or not yol.strip():
        return {"error": "Dosya yolu boş olamaz"}
    if not icerik:
        return {"error": "İçerik boş olamaz"}

    izinli, mesaj = _klasor_kontrol(yol, base_dir)
    if not izinli:
        return {"error": mesaj}

    # E-1: Dış projelere yazma yasak (salt okunur)
    if mesaj.startswith("dis:"):
        return {"error": ("Güvenlik engeli: '%s' dış projesine yazma izni yok. "
                          "Dış projeler salt okunur.") % mesaj.split(":")[1]}

    try:
        mutlak_yol = os.path.abspath(os.path.join(base_dir, yol))

        # Klasörü oluştur
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

    Args:
        klasor: Klasör yolu. Dış proje için "vixrex" gibi. Boşsa knowledge/ listelenir.
        base_dir: Proje kök dizini.

    Returns:
        {"result": str} veya {"error": str}.
    """
    if not klasor or not klasor.strip():
        klasor = "knowledge"

    izinli, mesaj = _klasor_kontrol(klasor, base_dir)
    if not izinli:
        return {"error": mesaj}

    try:
        # E-1: Dış proje ise onun kökünden listele
        if mesaj.startswith("dis:"):
            dis_proje = mesaj.split(":")[1]
            dis_kok = DIS_PROJELER[dis_proje]
            rel_yol = klasor.strip()
            if rel_yol.lower().startswith(dis_proje + "/"):
                rel_yol = rel_yol[len(dis_proje) + 1:]
            elif rel_yol.lower() == dis_proje:
                rel_yol = ""
            mutlak_yol = os.path.abspath(
                os.path.join(dis_kok, rel_yol)) if rel_yol else dis_kok
        else:
            mutlak_yol = os.path.abspath(os.path.join(base_dir, klasor))

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
