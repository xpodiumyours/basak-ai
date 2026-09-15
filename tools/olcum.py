"""tools/olcum.py — OLCU zemininin ölçüm araçları (Ö-1, salt-okunur).

OLCU.md §3 izin listesinin kod karşılığı. Güvenlik kodda sabittir,
model değiştiremez:

- Projeler beyaz listededir: basak, vixrex, numeramatch, xses
  (gelişimsüreci.md E-1 tablosu; yollar 22 Ağustos 2026'da doğrulandı)
- git yalnız OKUMA komutlarıyla ve sabit argv listesiyle çalışır; shell
  asla kullanılmaz. Yazan komutlar (commit/push/pull/fetch/checkout/reset)
  bu modülde imkânsızdır (gorev-pota-tur1.md kural 2 ile aynı sınır).
- belge_ara yalnız proje kökündeki .md dosyalarında düz metin arar.
- Çıktılar kırpılır; hata yolunda anlamlı mesaj döner.
"""

import os
import re
import subprocess

from tools.file_ops import YASAK_DOSYA_KALIPLARI, _yasak_mi

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Beyaz liste — model yol veremez, yalnız bu anahtarlardan seçer
PROJELER = {
    "basak": BASE,
    "vixrex": r"C:\Projects\vixrex",
    "numeramatch": r"C:\Users\Casper\source\NumeraMatch",
    "xses": r"C:\Projects\xses",
}

_MAX_CIKTI = 200000
_MAX_ESLESME = 200

# Is 4 (icerik_ara) sinirlari — ARAC-PLANI Is 4 tablosu
_ATLANACAK_KLASORLER = frozenset((
    ".git", "node_modules", "__pycache__", "build", "dist", ".next",
    "venv", ".codex-worktrees",
))
_MAX_DOSYA_BOYUT = 1_000_000      # dosya basi 1 MB
_MAX_ICERIK_ESLESME = 8           # en fazla 8 eslesme
_ICERIK_CIKTI_TAVAN = 8000        # cikti 8000 karakter (8 eslesme sigar)


def _kirmala(metin):
    """Bilinen sifre/anahtar desenlerini maskeleyip dondurur.

    Kaynak: 27b03a9:tools/tool_logger.py::_kirmala (aynen alindi) +
    eyJ (JWT) deseni — ARAC-PLANI Is 4 listesi bunu sart kosar.
    Kara liste dosya ADINA bakar; normal adli dosyadaki gomulu
    anahtar ikinci savunma hattidir.
    """
    metin = re.sub(r"(?i)(bearer\s+)\S+", r"\1***", metin)
    metin = re.sub(r"\beyJ[A-Za-z0-9_-]{10,}", "eyJ***", metin)
    metin = re.sub(r"\bsk-[A-Za-z0-9_-]{8,}", "sk-***", metin)
    metin = re.sub(r"\bsk-or-v1-[A-Za-z0-9]{8,}", "sk-or-***", metin)
    metin = re.sub(r"\bgsk_[A-Za-z0-9]{10,}", "gsk-***", metin)
    metin = re.sub(r"\bhf_[A-Za-z0-9]{10,}", "hf-***", metin)
    metin = re.sub(r"\bnvapi-[A-Za-z0-9_-]{10,}", "nvapi-***", metin)
    metin = re.sub(
        r"(?i)\b(api[_-]?key|token|parola|password|sifre|secret|anahtar)"
        r"(\s*[=:]\s*)(?:\"[^\"]*\"|'[^']*'|\S+)",
        r"\1\2***", metin)
    return metin

_FOLD = str.maketrans({
    "ı": "i", "I": "i", "İ": "i", "ş": "s", "Ş": "s", "ğ": "g", "Ğ": "g",
    "ü": "u", "Ü": "u", "ö": "o", "Ö": "o", "ç": "c", "Ç": "c",
})


def _norm(metin):
    return re.sub(r"\s+", " ", (metin or "").translate(_FOLD).lower()).strip()


def _kok(proje):
    """Beyaz liste anahtarından proje kökünü döndürür; yoksa None."""
    return PROJELER.get((proje or "").strip().lower())


def _hata_beyaz_liste(proje):
    adlar = ", ".join(sorted(PROJELER))
    return {"error": "Bilinmeyen proje: '%s'. Beyaz liste: %s"
                     % ((proje or ""), adlar)}


def _git(proje, argv, limit=_MAX_CIKTI):
    """Sabit okuma komutunu çalıştırır; başarısızlıkta None döner."""
    kok = _kok(proje)
    if kok is None:
        return None
    try:
        r = subprocess.run(
            ["git", "-C", kok] + list(argv),
            capture_output=True, text=True, timeout=10, shell=False,
            encoding="utf-8", errors="replace")
    except Exception:
        return None
    if r.returncode != 0:
        return None
    cikti = (r.stdout or "").strip()
    if len(cikti) > limit:
        cikti = cikti[:limit] + "\n...(kisaltildi)"
    return cikti


def git_durum(proje):
    """Projenin dal + son commit + commit edilmemiş dosyalarını ölçer."""
    if _kok(proje) is None:
        return _hata_beyaz_liste(proje)

    dal = _git(proje, ["rev-parse", "--abbrev-ref", "HEAD"])
    son = _git(proje, ["log", "-1", "--format=%h | %ad | %s",
                       "--date=format:%Y-%m-%d %H:%M"])
    durum = _git(proje, ["status", "--porcelain"])

    if dal is None and son is None:
        return {"error": ("git olcumu basarisiz: '%s' bir git deposu degil "
                          "veya git erisilemiyor." % _kok(proje))}

    satirlar = ["Proje: %s" % (proje or "").strip().lower()]
    if dal:
        satirlar.append("Dal: %s" % dal)
    if son:
        satirlar.append("Son commit: %s" % son)
    else:
        satirlar.append("Son commit: (bos depo)")
    if durum is not None:
        kirliler = [s for s in durum.splitlines() if s.strip()]
        if not kirliler:
            satirlar.append("Commit edilmemis dosya: 0 (temiz)")
        else:
            satirlar.append("Commit edilmemis dosya: %d" % len(kirliler))
            satirlar.extend(kirliler[:10])
            if len(kirliler) > 10:
                satirlar.append("...(+%d gizli)" % (len(kirliler) - 10))
    return {"result": "\n".join(satirlar)}


def belge_ara(proje, sorgu):
    """Proje kökündeki .md belgelerde birebir satır araması yapar."""
    kok = _kok(proje)
    if kok is None:
        return _hata_beyaz_liste(proje)
    q = _norm(sorgu)
    if not q:
        return {"error": "Arama sorgusu bos."}

    bulgular = []
    try:
        adlar = sorted(os.listdir(kok))
    except OSError as e:
        return {"error": "Proje klasoru okunamadi: %s" % e}

    for ad in adlar:
        if not ad.lower().endswith(".md"):
            continue
        tam = os.path.join(kok, ad)
        try:
            if os.path.getsize(tam) > 300_000:
                continue
            with open(tam, "r", encoding="utf-8-sig",
                      errors="replace") as f:
                for i, satir in enumerate(f, 1):
                    if q in _norm(satir):
                        bulgular.append("%s:%d: %s"
                                        % (ad, i, satir.strip()))
                        if len(bulgular) >= _MAX_ESLESME:
                            break
        except OSError:
            continue
        if len(bulgular) >= _MAX_ESLESME:
            break

    if not bulgular:
        return {"error": "Belgelerde bulunamadi: '%s'"
                         % (sorgu or "")}
    return {"result": "\n".join(bulgular)}


def dosya_bilgi(proje, yol):
    """Proje içindeki tek dosyanın varlık/değişim/boyut bilgisini ölçer."""
    kok = _kok(proje)
    if kok is None:
        return _hata_beyaz_liste(proje)
    rel = (yol or "").strip()
    if not rel:
        return {"error": "Dosya yolu bos."}
    tam = os.path.realpath(os.path.join(kok, rel))
    kok_gercek = os.path.realpath(kok)
    if not (tam == kok_gercek or tam.startswith(kok_gercek + os.sep)):
        return {"error": "Yol proje disina tasiyor: %s" % rel}
    if os.path.isdir(tam):
        try:
            n = len(os.listdir(tam))
        except OSError:
            n = -1
        return {"result": "%s: klasor (%d ogeler)" % (rel, n)}
    if not os.path.isfile(tam):
        return {"error": "Dosya yok: %s" % rel}
    try:
        st = os.stat(tam)
    except OSError as e:
        return {"error": "Dosya okunamadi: %s" % e}
    import time as _time
    degisti = _time.strftime("%Y-%m-%d %H:%M",
                             _time.localtime(st.st_mtime))
    return {"result": "%s: var | %d bayt | son degisim %s"
                      % (rel, st.st_size, degisti)}


def _ikili_mi(tam):
    """Ikili dosya mi? (ilk 8 KB'ta NUL bayt varsa okuma)."""
    try:
        with open(tam, "rb") as f:
            return b"\x00" in f.read(8192)
    except OSError:
        return True


def icerik_ara(proje, sorgu, uzanti=None):
    """Proje genelinde ozyinelemeli icerik aramasi (Is 4, yeni kod).

    belge_ara yalniz kok .md'lere bakiyordu; bu alt klasorlere de iner.
    Donus: `dosya:satir: icerik` satirlari (en fazla 8 eslesme).

    GUVENLIK (ARAC-PLANI Is 4, olculmus .env sizintisi):
    1. Kara listedeki dosya HIC acilmaz (file_ops._yasak_mi — ayni
       koruma; yeni kara liste YAZILMADI).
    2. Cikti maskelenir (_kirmala): gomulu anahtar ikinci hatta durur.
    """
    kok = _kok(proje)
    if kok is None:
        return _hata_beyaz_liste(proje)
    q = _norm(sorgu)
    if not q:
        return {"error": "Arama sorgusu bos."}
    uz = (uzanti or "").strip().lower()
    if uz and not uz.startswith("."):
        uz = "." + uz

    bulgular = []
    kok_gercek = os.path.realpath(kok)
    for gezdik, klasorler, dosyalar in os.walk(kok_gercek):
        klasorler[:] = [k for k in klasorler
                        if k not in _ATLANACAK_KLASORLER
                        and not k.startswith(".codex")]
        for ad in sorted(dosyalar):
            if uz and not ad.lower().endswith(uz):
                continue
            tam = os.path.join(gezdik, ad)
            try:
                if _yasak_mi(tam):
                    continue
                if os.path.getsize(tam) > _MAX_DOSYA_BOYUT:
                    continue
                if _ikili_mi(tam):
                    continue
                with open(tam, "r", encoding="utf-8-sig",
                          errors="replace") as f:
                    for i, satir in enumerate(f, 1):
                        if q in _norm(satir):
                            rel = os.path.relpath(tam, kok_gercek)
                            bulgular.append("%s:%d: %s"
                                            % (rel, i, satir.strip()))
                            if len(bulgular) >= _MAX_ICERIK_ESLESME:
                                break
            except OSError:
                continue
            if len(bulgular) >= _MAX_ICERIK_ESLESME:
                break
        if len(bulgular) >= _MAX_ICERIK_ESLESME:
            break

    if not bulgular:
        return {"error": "Icerikte bulunamadi: '%s'" % (sorgu or "")}
    cikti = _kirmala("\n".join(bulgular))
    if len(cikti) > _ICERIK_CIKTI_TAVAN:
        cikti = cikti[:_ICERIK_CIKTI_TAVAN] + "\n...(kisaltildi)"
    return {"result": cikti}


_TABAN_KALIP = re.compile(r"^[A-Za-z0-9][A-Za-z0-9/_.\-]*$")


def git_gecmis(proje, dosya=None, adet=10):
    """Son commit listesi (Is 6, salt-okunur, mevcut _git yardimcisi).

    adet tavani 30; dosya proje koku disina cikamaz.
    """
    kok = _kok(proje)
    if kok is None:
        return _hata_beyaz_liste(proje)
    try:
        adet = max(1, min(30, int(adet)))
    except (TypeError, ValueError):
        adet = 10
    argv = ["log", "--oneline", "-n", str(adet)]
    if dosya:
        rel = str(dosya).strip()
        tam = os.path.realpath(os.path.join(kok, rel))
        kok_gercek = os.path.realpath(kok)
        if not (tam == kok_gercek or tam.startswith(kok_gercek + os.sep)):
            return {"error": "Yol proje disina tasiyor: %s" % rel}
        argv += ["--", rel]
    cikti = _git(proje, argv)
    if cikti is None:
        return {"error": "git gecmisi okunamadi."}
    return {"result": cikti or "(bos depo)"}


def git_degisenler(proje, taban="origin/master"):
    """Taban ile HEAD arasi degisen dosya ozeti (Is 6, salt-okunur)."""
    kok = _kok(proje)
    if kok is None:
        return _hata_beyaz_liste(proje)
    taban = (taban or "origin/master").strip()
    if not _TABAN_KALIP.match(taban):
        return {"error": "Gecersiz taban: '%s'." % taban}
    cikti = _git(proje, ["diff", "--stat", "%s...HEAD" % taban])
    if cikti is None:
        return {"error": "git degisenler okunamadi."}
    return {"result": cikti or "(degisen yok)"}
