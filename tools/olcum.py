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

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# Beyaz liste — model yol veremez, yalnız bu anahtarlardan seçer
PROJELER = {
    "basak": BASE,
    "vixrex": r"C:\Projects\vixrex",
    "numeramatch": r"C:\Users\Casper\source\NumeraMatch",
    "xses": r"C:\Projects\xses",
}

_MAX_CIKTI = 1500
_MAX_ESLESME = 8

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
                     % ((proje or "")[:40], adlar)}


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
                satirlar.append("(10 / %d dosya gosteriliyor)" % len(kirliler))
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
                                        % (ad, i, satir.strip()[:160]))
                        if len(bulgular) >= _MAX_ESLESME:
                            break
        except OSError:
            continue
        if len(bulgular) >= _MAX_ESLESME:
            break

    if not bulgular:
        return {"error": "Belgelerde bulunamadi: '%s'"
                         % (sorgu or "")[:60]}
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
        return {"error": "Yol proje disina tasiyor: %s" % rel[:60]}
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
