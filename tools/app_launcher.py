"""tools/app_launcher.py — Uygulama açma aracı.

Sadece beyaz listedeki uygulamaları açabilir.
Her işlem loglanır.
"""

import logging
import re
import subprocess
import sys
import webbrowser

logger = logging.getLogger(__name__)

# tarayiciya SADECE http/https adresi geçirilir
_URL_KALIP = re.compile(r"^https?://\S+$")

# Diğer uygulamalarda parametre: kabuk metakarakterleri ve kontrol
# karakterleri YASAK (ikinci savunma katmanı; asıl koruma shell=False)
_YASAK_KALIP = re.compile(r"""[&|<>^"`$;\r\n\t\x00-\x1f]""")

# Beyaz liste: sadece bu uygulamalar açılabilir
BEYAZ_LISTE = {
    "tarayici": {"desc": "Varsayılan tarayıcıyı açar"},
    "notepad": {"exe": ["notepad"], "desc": "Not Defteri'ni açar", "param": True},
    "calculator": {"exe": ["calc"], "desc": "Hesap Makinesi'ni açar", "param": False},
    "file_manager": {"exe": ["explorer"], "desc": "Dosya Yöneticisi'ni açar", "param": True},
    "vscode": {"exe": ["code"], "desc": "Visual Studio Code'u açar", "param": True},
}


def ac_uygulama(uygulama_adi: str, parametre: str = "") -> dict:
    """Beyaz listedeki bir uygulamayı açar.

    GÜVENLİK NOTU (2026-08-21):
    Eski sürüm shell=True ile komut birleştiriyordu; 'parametre' alanından
    keyfi komut çalıştırılabiliyordu (güvenlik sondası ile kanıtlandı).
    Artık:
    - shell=True hiç kullanılmaz (list-form Popen)
    - tarayiciya yalnızca http/https adresi geçirilir (webbrowser modülü)
    - diğer uygulamalarda parametredeki kabuk metakarakterleri reddedilir

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
    parametre = (parametre or "").strip()
    mesaj_ek = f" Parametre: {parametre}" if parametre else ""

    try:
        if uygulama_adi == "tarayici":
            if parametre:
                if not _URL_KALIP.match(parametre):
                    return {"error": "Tarayıcıya sadece http/https adresi geçer"}
                webbrowser.open(parametre)
            else:
                webbrowser.open("about:blank")
        else:
            komut = list(bilgi["exe"])
            if parametre:
                if not bilgi.get("param"):
                    return {"error": f"{uygulama_adi} parametre kabul etmez"}
                if _YASAK_KALIP.search(parametre):
                    return {"error": "Parametrede geçersiz karakterler var"}
                komut.append(parametre)
            if sys.platform == "win32":
                subprocess.Popen(
                    komut,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    creationflags=subprocess.CREATE_NO_WINDOW,
                )
            else:
                subprocess.Popen(
                    komut,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )

        mesaj = f"{bilgi['desc']} açıldı."
        mesaj += mesaj_ek
        return {"result": mesaj}

    except FileNotFoundError:
        return {"error": f"'{uygulama_adi}' bulunamadı — yüklü olmayabilir"}
    except OSError as e:
        return {"error": "Uygulama açılamadı: %s" % e}
