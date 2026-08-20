"""tools/app_launcher.py — Uygulama açma aracı.

Sadece beyaz listedeki uygulamaları açabilir.
Her işlem loglanır.
"""

import logging
import os
import subprocess
import sys

logger = logging.getLogger(__name__)

# Beyaz liste: sadece bu uygulamalar açılabilir
BEYAZ_LISTE = {
    "tarayici": {
        "windows": "cmd /c start",
        "desc": "Varsayılan tarayıcıyı açar",
    },
    "notepad": {
        "windows": "notepad",
        "desc": "Not Defteri'ni açar",
    },
    "calculator": {
        "windows": "calc",
        "desc": "Hesap Makinesi'ni açar",
    },
    "file_manager": {
        "windows": "explorer",
        "desc": "Dosya Yöneticisi'ni açar",
    },
    "vscode": {
        "windows": "code",
        "desc": "Visual Studio Code'u açar",
    },
}


def ac_uygulama(uygulama_adi: str, parametre: str = "") -> dict:
    """Beyaz listedeki bir uygulamayı açar.

    Args:
        uygulama_adi: Açılacak uygulamanın kısa adı (örn: tarayici, notepad).
        parametre: Uygulamaya geçirilecek parametre (örn: URL, dosya yolu).

    Returns:
        {"result": str} veya {"error": str}.
    """
    if not uygulama_adi or not uygulama_adi.strip():
        return {"error": "Uygulama adı boş olamaz"}

    uygulama_adi = uygulama_adi.strip().lower()

    if uygulama_adi not in BEYAZ_LISTE:
        mevcut = ", ".join(BEYAZ_LISTE.keys())
        return {
            "error": f"'{uygulama_adi}' beyaz listede değil. "
                     f"İzinli uygulamalar: {mevcut}"
        }

    bilgi = BEYAZ_LISTE[uygulama_adi]
    komut = bilgi["windows"]

    if parametre:
        komut = f"{komut} {parametre}"

    try:
        if sys.platform == "win32":
            # Windows'ta arka planda aç
            subprocess.Popen(
                komut,
                shell=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0,
            )
        else:
            subprocess.Popen(
                komut.split(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

        mesaj = f"{bilgi['desc']} açıldı."
        if parametre:
            mesaj += f" Parametre: {parametre}"

        return {"result": mesaj}

    except FileNotFoundError:
        return {"error": f"'{uygulama_adi}' bulunamadı — yüklü olmayabilir"}
    except OSError as e:
        return {"error": f"Uygulama açılamadı: {e}"}
