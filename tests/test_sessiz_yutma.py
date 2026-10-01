"""Sessiz yutma kabul kapısı — `except …: pass` = 0.

Ölçüm (2026-10-01, AST): üretim kodunda 59 sessiz yutma vardı. Bugün
59 → 0. Kural şudur:

    Bir `except` bloğu yalnız `pass` içeremez.

Neden `pass` yasak: `except: pass` hatayı yok sayar ve izi kalmaz.
Bir hata ya gerçekten umursamaz olmalıdır (o zaman `logger.debug` izi
bırakılır) ya da yutulmamalıdır (o zaman `return`/düzeltme yazılır).
Aralarında "niye yuttum" yorumu tek başına yetmez — ölçülebilir kural
sadece bir tanesini kabul eder: iz veya akış.

Bu test, kuralı koda bağlar: yeni bir `except: pass` yazılırsa koşu
kırmızıya döner. Taban: 0 (değiştirmek için kasıtlı gerekçe + commit).
"""

import ast
import pathlib

KOK = pathlib.Path(__file__).resolve().parents[1]

# Taranmayan dizinler: arsiv, testler, arac dosyalar, ölçüm probeleri.
# - tests/ : testlerin kendi hata yutmalari kasitlidir
# - _arsiv/: eski kod, calismiyor
# - _*  : kokteki tek seferlik olcum/kanit probelri (izlenen _olcum_*)
HARIC = {
    ".git", "_arsiv", "tests", "__pycache__", ".agents", ".claude",
    "node_modules", ".pytest_cache", ".ruff_cache", ".venv", "venv",
}


def _uretim_dosyalari():
    for yol in sorted(KOK.rglob("*.py")):
        if set(yol.relative_to(KOK).parts) & HARIC:
            continue
        yield yol


def _sessiz_yutmalar(yol):
    """(satir_no, kaynak_kodu) listesi: govdesi yalniz `pass` olan except."""
    agac = ast.parse(yol.read_text(encoding="utf-8"))
    bulunan = []
    for dugum in ast.walk(agac):
        if not isinstance(dugum, ast.ExceptHandler):
            continue
        if len(dugum.body) == 1 and isinstance(dugum.body[0], ast.Pass):
            bulunan.append(dugum.lineno)
    return bulunan


def _goreli_yollar():
    """Kokten goreli yol, **platformdan bagimsiz** bicimde.

    2026-10-01: burada `str(relative_to())` vardi ve CI **Windows**
    (win32) uzerinde kirmiziya dustu: `brain\\brain.py` != `brain/brain.py`.
    Uretim kodu degil, **testin** yoluydu. `as_posix()` her platformda
    `/` uretir; kural bu dosyada da kilitli.
    """
    return {yol.relative_to(KOK).as_posix() for yol in _uretim_dosyalari()}


def test_uretim_kodu_listeleniyor():
    """Taranan dosya sayısı makul: filtre yanlislikla her seyi elemiyor."""
    goreli = _goreli_yollar()
    assert "app.py" in goreli, "app.py taranmiyor — filtre bozuk"
    assert "brain/brain.py" in goreli, "brain/brain.py taranmiyor"
    assert "tools/web_search.py" in goreli, "tools/web_search.py taranmiyor"
    assert not any(y.startswith("tests/") for y in goreli), (
        "testler taranmamali")
    assert len(goreli) > 20, "taranan dosya sayisi anormal: %d" % len(goreli)


def test_yol_bicimi_platformdan_bagimsiz():
    """Aynı kural, Windows yazımıyla da doğrulanır.

    Linux'ta `str()` ve `as_posix()` aynı sonucu verir; bu yüzden
    hata ancak CI'da (win32) görünür. Kuralın kendisi her yerde
    kilitli kalsın diye Windows yazımı ayrıca sınanır.
    """
    ornek = pathlib.PureWindowsPath("brain") / "brain.py"
    assert str(ornek) == r"brain\brain.py", "beklenmeyen Windows yazimi"
    assert ornek.as_posix() == "brain/brain.py", ornek.as_posix()
    goreli = _goreli_yollar()
    assert "brain/brain.py" in goreli, sorted(goreli)[:5]
    assert not any(y.startswith("tests/") for y in goreli), (
        "testler taranmamali")


def test_sessiz_yutma_sifir():
    """KABUL ÖLÇÜTÜ: `except: pass` sayısı 0."""
    supheli = {}
    for yol in _uretim_dosyalari():
        satirlar = _sessiz_yutmalar(yol)
        if satirlar:
            supheli[yol.relative_to(KOK).as_posix()] = satirlar
    assert not supheli, (
        "Sessiz yutma bulundu (her `except` govdesi `pass` olamaz — "
        "logger.debug izi birak veya akisi duzelt): %s" % supheli)


def test_kural_testleri_kendi_dosyasinda_gecerli():
    """Bu dosya kurala uymak zorunda (kendini denetleme)."""
    satirlar = _sessiz_yutmalar(pathlib.Path(__file__).resolve())
    assert not satirlar, "test dosyasi kendi kuralini ihlal ediyor: %s" % (
        satirlar,)


def test_uretilmis_ornek_sessiz_yutma_olculuyor():
    """Sayacin gercekten calistigini gosteren kucuk alet sinamasi.

    Yanlislikla her seyi sifir sayan bir test, kurali "kilitlemez".
    """
    ornek = (
        "try:\n"
        "    x = 1\n"
        "except Exception:\n"
        "    pass\n"
    )
    yol = KOK / "tests" / "_gecici_sessiz_yutma_ornegi.py"
    yol.write_text(ornek, encoding="utf-8")
    try:
        assert _sessiz_yutmalar(yol) == [3], "ornek algilanmadi"
    finally:
        yol.unlink()


def test_yorumlu_pass_yalnizca_gecmez():
    """`# gerekce` yorumu tek basina kuralı saglamaz."""
    ornek = (
        "try:\n"
        "    x = 1\n"
        "except Exception:\n"
        "    pass  # bilerek yutuluyor\n"
    )
    yol = KOK / "tests" / "_gecici_yorumlu_ornegi.py"
    yol.write_text(ornek, encoding="utf-8")
    try:
        assert _sessiz_yutmalar(yol) == [3], (
            "yorumlu pass kuraldan muaf tutulmali")
    finally:
        yol.unlink()