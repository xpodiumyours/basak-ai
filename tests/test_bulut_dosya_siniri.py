r"""tests/test_bulut_dosya_siniri.py — bulutta dosya okuma siniri.

Olculdu 2026-09-23: tools/file_ops.py "kara listede degilse her mutlak
yolu oku" kuralini uyguluyordu. Kara listenin tamami Windows yolu
(C:\Windows, C:\Program Files, ~/.ssh) oldugu icin Linux sunucuda liste
fiilen bos kaliyor -> sunucunun her yeri okunabilir hale geliyordu.
Bulutta beyaz liste uygulanir: yalniz uygulama koku ve durum klasoru.
"""

import os

import tools.file_ops as fo

PROJE_KOK = os.path.dirname(os.path.dirname(os.path.abspath(fo.__file__)))


def test_yerelde_kural_degismedi(monkeypatch, tmp_path):
    """Casper'in kendi bilgisayarinda okuma daralmadi."""
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("BASAK_URETIM", raising=False)
    hedef = tmp_path / "not.txt"
    hedef.write_text("merhaba", encoding="utf-8")
    izinli, _mesaj, mutlak = fo._guvenli_yolu_coz(str(hedef), PROJE_KOK)
    assert izinli is True
    assert mutlak is not None


def test_bulutta_disarisi_okunamaz(monkeypatch, tmp_path):
    """Bulutta uygulama/durum kokü disindaki mutlak yol reddedilir."""
    monkeypatch.setenv("BASAK_URETIM", "1")
    monkeypatch.delenv("BASAK_STATE_DIR", raising=False)
    hedef = tmp_path / "disarida.txt"
    hedef.write_text("gizli", encoding="utf-8")
    izinli, mesaj, mutlak = fo._guvenli_yolu_coz(str(hedef), PROJE_KOK)
    assert izinli is False
    assert mutlak is None
    assert "disarida" in mesaj or "yalniz" in mesaj


def test_bulutta_linux_sistem_yollari_okunamaz(monkeypatch):
    """Kara liste Windows'a gore yazilmisti; Linux yollari da kapali."""
    monkeypatch.setenv("BASAK_URETIM", "1")
    monkeypatch.delenv("BASAK_STATE_DIR", raising=False)
    for yol in ("/etc/passwd", "/proc/self/environ", "/var/task/app.py"):
        izinli, _mesaj, mutlak = fo._guvenli_yolu_coz(yol, PROJE_KOK)
        assert izinli is False, yol
        assert mutlak is None, yol


def test_bulutta_uygulama_koku_okunur(monkeypatch):
    """Basak kendi kodunu/knowledge'ini bulutta da okuyabilmeli."""
    monkeypatch.setenv("BASAK_URETIM", "1")
    hedef = os.path.join(PROJE_KOK, "AGENTS.md")
    izinli, _mesaj, mutlak = fo._guvenli_yolu_coz(hedef, PROJE_KOK)
    assert izinli is True
    assert mutlak is not None


def test_bulutta_durum_klasoru_okunur(monkeypatch, tmp_path):
    """BASAK_STATE_DIR beyaz listede — hafiza/sohbet dosyalari okunur."""
    monkeypatch.setenv("BASAK_URETIM", "1")
    durum = tmp_path / "state"
    durum.mkdir()
    monkeypatch.setenv("BASAK_STATE_DIR", str(durum))
    hedef = durum / "kayit.json"
    hedef.write_text("{}", encoding="utf-8")
    izinli, _mesaj, mutlak = fo._guvenli_yolu_coz(str(hedef), PROJE_KOK)
    assert izinli is True
    assert mutlak is not None
