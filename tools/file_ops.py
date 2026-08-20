"""tools/file_ops.py — Dosya okuma/yazma araçları.

Sadece izin verilen klasörlerde çalışır (whitelist).
Varsayılan olarak sadece knowledge/ klasörüne izin verilir.
Her işlem loglanır.
"""

import logging
import os

logger = logging.getLogger(__name__)

# İzin verilen klasörler (whitelist)
IZINLI_KLASORLER = [
    "knowledge",
    "research-engine",
]


def _klasor_kontrol(yol, base_dir):
    """Verilen yolun izin verilen bir klasör içinde olup olmadığını kontrol eder."""
    try:
        mutlak_yol = os.path.abspath(os.path.join(base_dir, yol))
        base_mutlak = os.path.abspath(base_dir)

        # Yol base_dir altında mı?
        if not mutlak_yol.startswith(base_mutlak):
            return False, "Yol proje dizininin dışında"

        # Hangi alt klasörde?
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
    Max 5000 karakter okunur.

    Args:
        yol: Dosya yolu (base_dir'e göre).
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

    Args:
        klasor: Klasör yolu (base_dir'e göre). Boşsa knowledge/ listelenir.
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
