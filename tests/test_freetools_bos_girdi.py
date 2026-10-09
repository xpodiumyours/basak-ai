"""tests/test_freetools_bos_girdi.py — bos/eksik girisle basari UYDURULAMAZ.

Canli kusur (2026-10-10): "freetools.org'da SHA-256 uret: merhaba"
sorusuna karsilik arac BOS METNIN hash'ini (e3b0c442...) uretti ve model
kullaniciya "uretildi" dedi. Kusurun zinciri:
  - freetools_calistir'de form hic dogrulanmiyordu,
  - yerel.hesapla([]) bos listeyle hesapciyi calistiriyordu,
  - _sha([]) bos metnin hash'ini "sonuc" olarak donuyordu (sessiz basari).

Kural: girdi yoksa arac HATA doner, is yapmis gibi sonuc uydurmaz.
Not: "bos metnin hash'i" gibi egzotik istekler bu sinirla artik mumkun
degildir — bilincli takas: sessiz yanlis sonuc > kenar durum kolayligi.
"""

import hashlib
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import calistir
from tools import freetools_kopru as kopru
from tools import freetools_yerel as yerel
from tools.definitions import FREETOOLS_CALISTIR

SHA = "https://www.freetools.org/security-tools/sha-hash-generator"
BOS_HASH = hashlib.sha256(b"").hexdigest()


def _yerel_yol(monkeypatch):
    """Vercel yolu: tarayici yok, yerel standart algoritma devreye girer."""
    monkeypatch.setattr(
        kopru, "_tarayici_kos",
        lambda *a, **k: (_ for _ in ()).throw(ModuleNotFoundError("playwright")))


class TestBosGirdi:
    def test_form_yoksa_basari_uydurmaz(self, monkeypatch):
        """Kullanici semptomu: form yoksa arac bos-hash'i 'sonuc' diye veremez."""
        kopru.sifirla()
        _yerel_yol(monkeypatch)
        r = calistir("freetools_calistir", {"adres": SHA})
        assert "error" in r, "bos girdiyle basari uyduruldu: %r" % (r,)
        assert "girdi" in r["error"].lower()
        assert r.get("sonuc") != BOS_HASH

    def test_bos_stringler_de_girdi_sayilmaz(self, monkeypatch):
        kopru.sifirla()
        _yerel_yol(monkeypatch)
        for form in ([""], ["", ""], [None], ["", "sha256"]):
            r = calistir("freetools_calistir", {"adres": SHA, "form": form})
            assert "error" in r, "form=%r basari uydurdu: %r" % (form, r)
            assert r.get("sonuc") != BOS_HASH

    def test_bos_form_tarayiciya_uzamaz(self, monkeypatch):
        """Girdi eksikse tarayici/kota/onbellek hic isle ugrasmaz."""
        kopru.sifirla()
        kostu = {"n": 0}

        def sahte(adres, form):
            kostu["n"] += 1
            return {"sonuc": "yanlis-sonuc"}

        monkeypatch.setattr(kopru, "_sarmalayici", sahte)
        r = calistir("freetools_calistir", {"adres": SHA, "form": []})
        assert "error" in r
        assert kostu["n"] == 0, "bos girdi tarayiciya gonderildi"

    def test_dogruluk_korunur(self, monkeypatch):
        """Duzeltme gercek girise dokunmaz: merhaba'nin hash'i birebir doner."""
        kopru.sifirla()
        _yerel_yol(monkeypatch)
        r = calistir("freetools_calistir",
                     {"adres": SHA, "form": ["merhaba"]})
        assert r.get("sonuc") == hashlib.sha256(b"merhaba").hexdigest()
        assert "yerel-hesaplama" in r.get("kaynak", "")


class TestYerelDikis:
    def test_hesapla_bos_form_hata_don(self):
        """En kucuk repro: hesapla([], ...) bos-hash uretmez."""
        for form in (None, [], [""], [None]):
            r = yerel.hesapla(SHA, form)
            assert isinstance(r, dict) and "error" in r, \
                "form=%r ile basari dondu: %r" % (form, r)
            assert r.get("sonuc") != BOS_HASH

    def test_hesapla_gercek_girdi_calisir(self):
        r = yerel.hesapla(SHA, ["merhaba"])
        assert r["sonuc"] == hashlib.sha256(b"merhaba").hexdigest()


class TestSema:
    def test_form_alani_zorunlu(self):
        """Model form'u atlarsa hata orani artar; sema bunu onlemeli."""
        zorunlu = FREETOOLS_CALISTIR["function"]["parameters"]["required"]
        assert "form" in zorunlu, "form semada zorunlu degil: %r" % (zorunlu,)
