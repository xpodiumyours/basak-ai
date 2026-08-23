"""tests/test_kapanis_db.py — Kapanista hafiza DB kapanisi testleri.

2026-08-24'te Casper'in buldugu hata: Api.quit() DB'yi kapatirken
self._hafiza'ya bakiyordu; gercek nesne chat.py modul-globaliydi ve Api'de
boyle bir alan hic olusturulmiyordu. Blok oluyordu, os._exit(0) DB'yi
acik birakiyordu (WAL buyur).

Not: quit()'in TAMAMINI test etmek sureci oldururdugunden yalniz cikarilan
_hafizayi_kapat() metni denetlenir.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import basak_app
import chat as c


class SahteMotor:
    def __init__(self):
        self.kapatildi = False

    def kapat(self):
        self.kapatildi = True


def _api():
    return basak_app.Api()


def test_gercek_motor_kapatilir(monkeypatch):
    motor = SahteMotor()
    monkeypatch.setattr(c, "_hafiza", motor)
    _api()._hafizayi_kapat()
    assert motor.kapatildi is True


def test_motor_yoksa_cokmeden_gecer(monkeypatch):
    monkeypatch.setattr(c, "_hafiza", None)
    _api()._hafizayi_kapat()          # istisna firlatmamali
    monkeypatch.setattr(c, "_hafiza", False)
    _api()._hafizayi_kapat()


def test_api_nesnesinde_artik_hafiza_alani_aranmaz(monkeypatch):
    """Eski hatanin regresyon testi: self._hafiza YOKken bile gercek
    motor kapatilmali."""
    motor = SahteMotor()
    monkeypatch.setattr(c, "_hafiza", motor)
    api = _api()
    assert not hasattr(api, "_hafiza")
    api._hafizayi_kapat()
    assert motor.kapatildi is True
