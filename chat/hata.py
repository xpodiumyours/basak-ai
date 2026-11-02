"""Kullaniciya ve gunluge yazilacak hata metni.

anyio/asyncio gorev gruplari gercek hatayi bir grup nesnesinde saklar.
Python 3.11+ bunu `BaseExceptionGroup` olarak verir; daha eski surumlerde ayni
is `exceptiongroup` geri-uyum paketinin kendi sinifiyla yapilir. Iki bicim de
cozulmezse mesaj "unhandled errors in a TaskGroup (1 sub-exception)" olarak
kalir ve asil neden kaybolur.
"""
import builtins

GRUP = getattr(builtins, "BaseExceptionGroup", ())


def grup_mu(exc):
    """Yerlesik ya da geri-uyum (exceptiongroup) grubunu tanir."""
    if isinstance(exc, GRUP):
        return True
    icerik = getattr(exc, "exceptions", None)
    return isinstance(icerik, (list, tuple)) and len(icerik) > 0 and all(
        isinstance(oge, BaseException) for oge in icerik)


def hata_metni(exc, limit=3):
    """Yaprak hata mesajlarini tek satirda birlestirir; grup yoksa str(exc)."""
    if not grup_mu(exc):
        return str(exc or "").strip() or type(exc).__name__
    yapraklar, kuyruk = [], [exc]
    while kuyruk and len(yapraklar) < limit:
        oge = kuyruk.pop(0)
        if grup_mu(oge):
            kuyruk[0:0] = list(getattr(oge, "exceptions") or ())
            continue
        metin = str(oge or "").strip() or type(oge).__name__
        if metin not in yapraklar:
            yapraklar.append(metin)
    return " | ".join(yapraklar) or type(exc).__name__
