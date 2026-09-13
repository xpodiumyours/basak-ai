"""tools/hesap.py — Deterministik zaman + guvenli aritmetik.

Kucuk modeller tarihte/dort islemde sasirir; bu ikisi olcer, tahmin
etmez. Ag yok, dosya yok, yan etki yok. eval() ASLA kullanilmaz —
ifade AST ile cozumlur (sayi + dort islem + parantez).
"""

import ast
import operator
from datetime import datetime

_GUNLER = ("Pazartesi", "Sali", "Carsamba", "Persembe", "Cuma",
           "Cumartesi", "Pazar")
_AYLAR = ("", "Ocak", "Subat", "Mart", "Nisan", "Mayis", "Haziran",
          "Temmuz", "Agustos", "Eylul", "Ekim", "Kasim", "Aralik")

_isLEMLER = {ast.Add: operator.add, ast.Sub: operator.sub,
             ast.Mult: operator.mul, ast.Div: operator.truediv,
             ast.Mod: operator.mod, ast.Pow: operator.pow,
             ast.FloorDiv: operator.floordiv}
_isARETLER = {ast.UAdd: operator.pos, ast.USub: operator.neg}


def simdi():
    """Su an: gun ay yil, haftanin gunu, saat."""
    s = datetime.now()
    return {"result": "%d %s %d %s, %02d:%02d"
                       % (s.day, _AYLAR[s.month], s.year,
                          _GUNLER[s.weekday()], s.hour, s.minute)}


def _coz(dugum):
    if isinstance(dugum, ast.Expression):
        return _coz(dugum.body)
    if isinstance(dugum, ast.Constant) and isinstance(
            dugum.value, (int, float)):
        return dugum.value
    if isinstance(dugum, ast.BinOp) and type(dugum.op) in _isLEMLER:
        return _isLEMLER[type(dugum.op)](_coz(dugum.left),
                                         _coz(dugum.right))
    if isinstance(dugum, ast.UnaryOp) and type(dugum.op) in _isARETLER:
        return _isARETLER[type(dugum.op)](_coz(dugum.operand))
    raise ValueError("desteklenmeyen ifade")


def hesapla(ifade):
    """Dort islem + parantez + us/yuzde kalani. Ornek: (120*18)/100."""
    ifade = (ifade or "").strip()
    if not ifade:
        return {"error": "Ifade bos olamaz"}
    if len(ifade) > 200:
        return {"error": "Ifade cok uzun (en fazla 200 karakter)"}
    try:
        sonuc = _coz(ast.parse(ifade, mode="eval"))
    except ZeroDivisionError:
        return {"error": "Sifira bolunemez"}
    except (SyntaxError, ValueError):
        return {"error": ("Sadece sayi ve + - * / yuzde, ** ( ) "
                          "kullanilabilir: '" + ifade[:60] + "'")}
    except Exception as e:
        return {"error": "Hesaplanamadi: %s" % e}
    if isinstance(sonuc, float) and sonuc.is_integer():
        sonuc = int(sonuc)
    return {"result": str(sonuc)}
