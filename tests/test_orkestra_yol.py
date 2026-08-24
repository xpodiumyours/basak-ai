"""tests/test_orkestra_yol.py — Üretim bağlantısı: ayar anahtarı + akış.

Gölge mod ilkesi: "orkestra_ana_yol": true olana kadar mesaj_isle ESKİ
yolu kullanır. Anahtar açılınca aynı sözleşmeli mesaj_isle_orkestra
devreye girer; davranış farkı yalnız iz kaydıdır.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chat as c


def test_ayar_kapaliyken_eski_yol_secilir(monkeypatch, tmp_path):
    ayarlar = tmp_path / "ayarlar.json"
    ayarlar.write_text(json.dumps({"orkestra_ana_yol": False}),
                       encoding="utf-8")
    monkeypatch.setattr(c, "SETTINGS_FILE", str(ayarlar))
    assert c.orkestra_aktif_mi() is False

    ayarlar.write_text(json.dumps({"orkestra_ana_yol": True}),
                       encoding="utf-8")
    assert c.orkestra_aktif_mi() is True

    # dosya yoksa da güvenli False
    monkeypatch.setattr(c, "SETTINGS_FILE", str(tmp_path / "yok.json"))
    assert c.orkestra_aktif_mi() is False


def _ana_yol_acik(monkeypatch, tmp_path, deger=True):
    ayarlar = tmp_path / "ayarlar.json"
    ayarlar.write_text(json.dumps({"orkestra_ana_yol": deger}),
                       encoding="utf-8")
    monkeypatch.setattr(c, "SETTINGS_FILE", str(ayarlar))


class SahteBrain:
    def yerel_modeller(self):
        return ["qwen2.5:3b"]

    def bulut_musait(self):
        return True


def test_ana_yol_acikken_mesaj_isle_orkestraya_yonlenir(monkeypatch,
                                                        tmp_path):
    """ORKESTRA-1 üretim bağlantısı: anahtar açıkken mesaj_isle akışı
    durum makinesine devreder; eski yol koşmaz."""
    _ana_yol_acik(monkeypatch, tmp_path, True)

    gidenler = []

    def sahte_orkestra(text, brain, sprompt, cb, tools, kaydet_acik):
        gidenler.append((text, sprompt, kaydet_acik))
        cb("BasakUI.reply('orkestra cevabi', 'groq')")

    monkeypatch.setattr(c, "mesaj_isle_orkestra", sahte_orkestra)
    c.mesaj_isle("merhaba", SahteBrain(), "KISILIK-METNI",
                 lambda code: None, None)
    assert len(gidenler) == 1
    assert gidenler[0][0] == "merhaba"
    assert gidenler[0][1] == "KISILIK-METNI"   # kişilik promptu taşınır
    assert gidenler[0][2] is True              # kalıcı yolda yazma AÇIK


def test_ana_yol_kapaliyken_eski_akis_devam_eder(monkeypatch, tmp_path):
    _ana_yol_acik(monkeypatch, tmp_path, False)

    def patlak(*a, **k):
        raise AssertionError("kapalıyken orkestra yolu çağrılmamalı")

    monkeypatch.setattr(c, "mesaj_isle_orkestra", patlak)
    try:
        c.mesaj_isle("merhaba", SahteBrain(), "SP",
                     lambda code: None, None)
    except AssertionError:
        raise
    except Exception:
        pass   # eski yol SahteBrain ile çeşitli yerlerde takılabilir;
               # önemli olan orkestra yolunun ÇAĞRILMAMIŞ olması


def test_golge_modu_ana_yolda_sessizce_atlanir(monkeypatch, tmp_path):
    """Ana yol aktifken gölge koşumu kendini ölçmek olur — çağrılmaz."""
    ayarlar = tmp_path / "ayarlar.json"
    ayarlar.write_text(json.dumps({"orkestra_ana_yol": True,
                                   "golge_mod": True}),
                       encoding="utf-8")
    monkeypatch.setattr(c, "SETTINGS_FILE", str(ayarlar))

    def patlak(*a, **k):
        raise AssertionError("ana yolda golge_kos koşmamalı")

    monkeypatch.setattr(c, "mesaj_isle_orkestra", patlak)
    c.golge_kos("selam", SahteBrain(), "eski")   # exception fırlatmamalı
