"""tests/test_juri_onay.py — Jüri onay kutusu sözleşme testleri.

2026-09-10 (Casper kararı): bayrak kapalıyken jüri her soruda kota
yakmasın; ekranda onay kutusuyla sorulsun. Sözleşme:
- juri_acik_mi() True → ek_adaylar sorusuz koşar (onay thunk'u çağrılmaz)
- bayrak kapalı + thunk yok → [] (kota yenmez, zincire dokunulmaz)
- bayrak kapalı + thunk EVET → adaylar kurulur
- bayrak kapalı + thunk HAYIR/hata → [] (kota yenmez)
- dırdır engeli: ikinci soru 30 dk içinde sorulmadan [] döner
- ek_adaylar onay beklerken engellenmez: onay thunk'u DIVERSIFY
  adımında çağrılır (orkestra thread'i bloklar, UI onay_ver ile açar)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chat  # önce tam paket (dairesel import önlemi)
import _chat_legacy as L


class Sahte:
    zincir_dokunma = 0

    def _bulut_zinciri(self):
        type(self).zincir_dokunma += 1
        return [("groq", "ist1"), ("glm", "ist2"), ("nvidia", "ist3")]


def _temizle(monkeypatch):
    monkeypatch.setattr(L, "_JURI_SON_SORU", 0.0)
    Sahte.zincir_dokunma = 0


class TestJuriOnay:
    def test_bayrak_aciksa_sorusuz_kosar(self, monkeypatch):
        _temizle(monkeypatch)
        monkeypatch.setattr(L, "juri_acik_mi", lambda: True)
        bilesenler = L.orkestra_bilesenleri(Sahte())
        cagrildi = []
        sonuc = bilesenler["ek_adaylar"](
            "groq", [], arac_var=False)
        assert len(sonuc) == 2  # _JURI_MAX
        assert {ad for ad, _ in sonuc} == {"glm", "nvidia"}

    def test_bayrak_kapali_thunk_yoksa_kota_yemez(self, monkeypatch):
        _temizle(monkeypatch)
        monkeypatch.setattr(L, "juri_acik_mi", lambda: False)
        bilesenler = L.orkestra_bilesenleri(Sahte())
        assert bilesenler["ek_adaylar"]("groq", [], arac_var=False) == []
        assert Sahte.zincir_dokunma == 0

    def test_bayrak_kapali_onay_evetse_kosar(self, monkeypatch):
        _temizle(monkeypatch)
        monkeypatch.setattr(L, "juri_acik_mi", lambda: False)
        bilesenler = L.orkestra_bilesenleri(
            Sahte(), juri_onay=lambda: True)
        sonuc = bilesenler["ek_adaylar"]("groq", [], arac_var=False)
        assert len(sonuc) == 2
        assert Sahte.zincir_dokunma == 1

    def test_bayrak_kapali_rette_kota_yemez(self, monkeypatch):
        _temizle(monkeypatch)
        monkeypatch.setattr(L, "juri_acik_mi", lambda: False)
        bilesenler = L.orkestra_bilesenleri(
            Sahte(), juri_onay=lambda: False)
        assert bilesenler["ek_adaylar"]("groq", [], arac_var=False) == []
        assert Sahte.zincir_dokunma == 0

    def test_onay_hatasi_kota_yemez(self, monkeypatch):
        def patlak():
            raise RuntimeError("UI kapali")

        _temizle(monkeypatch)
        monkeypatch.setattr(L, "juri_acik_mi", lambda: False)
        bilesenler = L.orkestra_bilesenleri(Sahte(), juri_onay=patlak)
        assert bilesenler["ek_adaylar"]("groq", [], arac_var=False) == []
        assert Sahte.zincir_dokunma == 0

    def test_dirdir_engeli_ikinci_soruyu_atlar(self, monkeypatch):
        _temizle(monkeypatch)
        monkeypatch.setattr(L, "juri_acik_mi", lambda: False)
        soru_sayisi = []
        bilesenler = L.orkestra_bilesenleri(
            Sahte(), juri_onay=lambda: soru_sayisi.append(1) or True)
        assert len(bilesenler["ek_adaylar"]("groq", [],
                                             arac_var=False)) == 2
        # 30 dk dolmadan ikinci soru sorulmaz → []
        assert bilesenler["ek_adaylar"]("groq", [],
                                        arac_var=False) == []
        assert len(soru_sayisi) == 1

    def test_arac_turu_onaylansa_bile_kosmaz(self, monkeypatch):
        _temizle(monkeypatch)
        monkeypatch.setattr(L, "juri_acik_mi", lambda: False)
        bilesenler = L.orkestra_bilesenleri(
            Sahte(), juri_onay=lambda: True)
        assert bilesenler["ek_adaylar"]("groq", [], arac_var=True) == []

    def test_juri_onayi_thunku_onay_bekler(self, monkeypatch):
        yakalanan = {}

        def sahte_bekle(call_id, tool, args, timeout=60):
            yakalanan["call_id"] = call_id
            yakalanan["tool"] = tool
            yakalanan["timeout"] = timeout
            return True

        monkeypatch.setattr(L, "onay_bekle", sahte_bekle)
        sor = L._juri_onayi(timeout=60)
        assert sor() is True
        assert yakalanan["tool"] == "juri"
        assert yakalanan["call_id"].startswith("juri-")
        assert yakalanan["timeout"] == 60

    def test_juri_onayi_zamanasimi_false(self, monkeypatch):
        monkeypatch.setattr(L, "onay_bekle", lambda *a, **k: False)
        assert L._juri_onayi()() is False
