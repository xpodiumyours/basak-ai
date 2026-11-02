"""Kullaniciya ve gunluge yazilacak hata metni.

anyio/asyncio gorev gruplari gercek hatayi `ExceptionGroup` icinde saklar.
Sarmalayi cozmeden yazmak, "unhandled errors in a TaskGroup (1 sub-exception)"
gibi teshis edilemez bir metin uretir; asil neden kaybolur.
"""
import builtins

GRUP = getattr(builtins, "BaseExceptionGroup", ())


def hata_metni(exc, limit=3):
    """Yaprak hata mesajlarini tek satirda birlestirir; grup yoksa str(exc)."""
    if not isinstance(exc, GRUP):
        return str(exc or "").strip() or type(exc).__name__
    yapraklar, kuyruk = [], [exc]
    while kuyruk and len(yapraklar) < limit:
        oge = kuyruk.pop(0)
        if isinstance(oge, GRUP):
            kuyruk[0:0] = list(oge.exceptions)
            continue
        metin = str(oge or "").strip() or type(oge).__name__
        if metin not in yapraklar:
            yapraklar.append(metin)
    return " | ".join(yapraklar) or type(exc).__name__
