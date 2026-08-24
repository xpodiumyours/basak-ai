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
