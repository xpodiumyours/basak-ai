"""tests/test_doktor.py — Ortam doktoru testleri.

Cevrimdisi: hicbir ag cagrisi, hicbir gercek kota yok. Kontroller tmp_path
uzerinde kosar; gercek ayarlar.json ve gercek hafiza DB'si ELLENMEZ.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import doktor


def _durumlar(satirlar):
    return {ad: durum for durum, ad, _ in satirlar}


class SahteBeyin:
    """Gercek Brain yerine: yalnizca zincir adlarini soyler."""

    def __init__(self, adlar=("groq", "gemini")):
        self._adlar = list(adlar)

    def _bulut_zinciri(self, *a, **k):
        return [(ad, object()) for ad in self._adlar]

    def cevapla(self, mesajlar, model=None, tools=None, tool_choice=None):
        return {"content": "merhaba"}, "sahte"


class TestPythonVePaketler:
    def test_python_durumu_gecerli(self):
        satirlar = doktor.kontrol_python()
        assert len(satirlar) == 1
        durum, ad, _ = satirlar[0]
        assert durum in (doktor.OK, doktor.UYARI, doktor.HATA)
        assert ad == "Python"

    def test_paketler_zorunlu_eksikse_hata(self, monkeypatch):
        monkeypatch.setattr(doktor, "_var_mi", lambda m: False)
        satirlar = doktor.kontrol_paketler()
        durumlar = _durumlar(satirlar)
        assert durumlar["Paketler (zorunlu)"] == doktor.HATA
        assert "pip install -r requirements.txt" in satirlar[0][2]

    def test_paketler_tamamsa_ok(self, monkeypatch):
        monkeypatch.setattr(doktor, "_var_mi", lambda m: True)
        satirlar = doktor.kontrol_paketler()
        assert _durumlar(satirlar)["Paketler (zorunlu)"] == doktor.OK
        assert "Paketler (opsiyonel)" not in _durumlar(satirlar)


class TestAyarlar:
    def test_dosya_yoksa_hata(self, tmp_path):
        satirlar = doktor.kontrol_ayarlar(str(tmp_path / "ayarlar.json"))
        assert satirlar[0][0] == doktor.HATA

    def test_bom_lu_json_okunur(self, tmp_path):
        yol = tmp_path / "ayarlar.json"
        yol.write_bytes(b"\xef\xbb\xbf" + json.dumps({"groq_key": "x"}).encode())
        assert doktor.ayar_yukle(str(yol))["groq_key"] == "x"

    def test_bozuk_json_bos_doner(self, tmp_path):
        yol = tmp_path / "ayarlar.json"
        yol.write_text("{bozuk", encoding="utf-8")
        assert doktor.ayar_yukle(str(yol)) == {}

    def test_ust_seviye_anahtar_ok_der(self, tmp_path):
        yol = tmp_path / "ayarlar.json"
        yol.write_text(json.dumps({"groq_key": "gsk_x"}), encoding="utf-8")
        durumlar = _durumlar(doktor.kontrol_ayarlar(str(yol)))
        assert durumlar["Anahtarlar"] == doktor.OK

    def test_anahtar_yoksa_uyari_verir(self, tmp_path):
        yol = tmp_path / "ayarlar.json"
        yol.write_text(json.dumps({"tts_on": True}), encoding="utf-8")
        durumlar = _durumlar(doktor.kontrol_ayarlar(str(yol)))
        assert durumlar["Anahtarlar"] == doktor.UYARI

    def test_ic_ice_gruba_yazilan_anahtar_hata_verir(self, tmp_path):
        """2026-09-22 tuzagi: kod ust seviyeden okur, sablon ic ice koyuyordu."""
        yol = tmp_path / "ayarlar.json"
        yol.write_text(json.dumps({
            "_yeni_platformlar": {"mistral_key": "sk-x"},
        }), encoding="utf-8")
        satirlar = doktor.kontrol_ayarlar(str(yol))
        durumlar = _durumlar(satirlar)
        assert durumlar["ayarlar.json (ic ice)"] == doktor.HATA
        detay = [d for _, ad, d in satirlar if ad == "ayarlar.json (ic ice)"][0]
        assert "mistral_key" in detay

    def test_ic_ice_alanlar_derinlikte_de_bulur(self):
        veri = {"_a": {"_b": {"cohere_key": "x"}}}
        assert ("_b", "cohere_key") in doktor.ic_ice_alanlar(veri)

    def test_sablon_gercek_dosyada_ic_ice_anahtar_yok(self):
        """ayarlar.ornek.json ile kod ayni yeri okumali — bu bekci kilitler."""
        yoll = [
            os.path.join(doktor.BASE, "ayarlar.ornek.json"),
            os.path.join(os.path.dirname(doktor.BASE), "ayarlar.ornek.json"),
        ]
        yol = next((y for y in yoll if os.path.exists(y)), None)
        assert yol, "ayarlar.ornek.json bulunamadi"
        veri = doktor.ayar_yukle(yol)
        assert doktor.ic_ice_alanlar(veri) == []
        # Sablon kodun okudugu adlari da tasimali (bos dahi olsa).
        eksik = [ad for ad in doktor.ANAHTAR_ALANLARI if ad not in veri]
        assert eksik == [], "sablonda eksik alan: %s" % eksik


class TestSesVeVeri:
    def test_ses_modeli_yoksa_uyari(self, tmp_path):
        satirlar = doktor.kontrol_ses_modeli(str(tmp_path))
        assert satirlar[0][0] == doktor.UYARI
        assert doktor.SES_MODELI_ADI in satirlar[0][2]

    def test_ses_modeli_varsa_ok(self, tmp_path):
        (tmp_path / doktor.SES_MODELI_ADI).write_bytes(b"0")
        (tmp_path / (doktor.SES_MODELI_ADI + ".json")).write_text("{}")
        assert doktor.kontrol_ses_modeli(str(tmp_path))[0][0] == doktor.OK

    def test_veri_klasoru_olusturulur(self, tmp_path):
        satirlar = doktor.kontrol_veri_klasoru(str(tmp_path))
        assert satirlar[0][0] == doktor.OK
        assert (tmp_path / "data" / "memory").is_dir()

    def test_hafiza_db_acilir(self, tmp_path):
        satirlar = doktor.kontrol_hafiza(str(tmp_path))
        assert satirlar[0][0] == doktor.OK


class TestBeyinVeButun:
    def test_zincir_bos_ise_hata(self):
        satirlar = doktor.kontrol_beyin(SahteBeyin([]))
        assert satirlar[0][0] == doktor.HATA

    def test_zincir_dolu_ise_ok(self):
        satirlar = doktor.kontrol_beyin(SahteBeyin(["groq", "gemini"]))
        durum, _, detay = satirlar[0]
        assert durum == doktor.OK
        assert "groq" in detay and "gemini" in detay

    def test_beyin_kurulamazsa_hata(self):
        class Patlayan:
            def _bulut_zinciri(self, *a, **k):
                raise RuntimeError("patladi")

        assert doktor.kontrol_beyin(Patlayan())[0][0] == doktor.HATA

    def test_canli_cagri_basarili(self):
        assert doktor.kontrol_canli(SahteBeyin())[0][0] == doktor.OK

    def test_canli_cagri_hatali(self):
        class Patlayan(SahteBeyin):
            def cevapla(self, *a, **k):
                raise RuntimeError("kota bitti")

        assert doktor.kontrol_canli(Patlayan())[0][0] == doktor.HATA

    def test_calistir_tum_kontrolleri_dondurur(self, tmp_path):
        satirlar = doktor.calistir(kok=str(tmp_path), brain=SahteBeyin())
        assert all(d in (doktor.OK, doktor.UYARI, doktor.HATA)
                   for d, _, _ in satirlar)
        adlar = {ad for _, ad, _ in satirlar}
        assert {"Python", "ayarlar.json", "Ses modeli",
                "Beyin zinciri"} <= adlar

    def test_cikis_kodu_hata_varsa_1(self, monkeypatch):
        monkeypatch.setattr(doktor, "calistir",
                            lambda **k: [(doktor.HATA, "X", "y")])
        assert doktor.main([]) == 1

    def test_cikis_kodu_temizse_0(self, monkeypatch):
        monkeypatch.setattr(doktor, "calistir",
                            lambda **k: [(doktor.OK, "X", "y")])
        assert doktor.main([]) == 0
