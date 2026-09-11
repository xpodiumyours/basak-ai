"""tests/test_hatirlatma_tarihi.py — Gün sayımı off-by-one düzeltmesi.

2026-08-24 canlı bulgu: 24 Ağustos 18:35'te 26 Ağustos için "1 gun kaldi"
deniyordu — saat bileşeni farka karışıyordu. Takvim günü farkı esastır.
"""

import os
import sys
from datetime import datetime, timedelta

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools.reminders import AY_MAP, bugunku_hatirlatmalar


def test_2_gun_sonra_1_gun_demez(tmp_path):
    hedef = datetime.now() + timedelta(days=2)
    ay_adi = next(a for a, m in AY_MAP.items() if m == hedef.month)
    (tmp_path / "d.md").write_text(
        "- **Doğum:** %d %s 1995 — Başak burcu\n" % (hedef.day, ay_adi),
        encoding="utf-8")

    sonuc = bugunku_hatirlatmalar(str(tmp_path), str(tmp_path / "yok.json"))
    metin = " ".join(sonuc.get("result", "").split())
    assert "2 gun sonra" in metin
    assert "1 gun kaldi" not in metin


def test_yarin_etiketi_takvimce_1_gunde(tmp_path):
    hedef = datetime.now() + timedelta(days=1)
    ay_adi = next(a for a, m in AY_MAP.items() if m == hedef.month)
    (tmp_path / "d.md").write_text(
        "- **Doğum:** %d %s 1995 — Başak burcu\n" % (hedef.day, ay_adi),
        encoding="utf-8")

    sonuc = bugunku_hatirlatmalar(str(tmp_path), str(tmp_path / "yok.json"))
    metin = " ".join(sonuc.get("result", "").split())
    assert "YARIN" in metin or "1 gun sonra" in metin


def test_gecmis_saatli_gorev_etiketlenir(tmp_path):
    from datetime import timedelta as td
    gecen = datetime.now() - td(hours=3)
    gorevler = [{"date": datetime.now().strftime("%Y-%m-%d"),
                 "text": "saat %02d:%02d'te discine yedek al"
                         % (gecen.hour, gecen.minute),
                 "done": False}]
    import json
    dosya = tmp_path / "gorevler.json"
    dosya.write_text(json.dumps(gorevler), encoding="utf-8")

    sonuc = bugunku_hatirlatmalar(str(tmp_path), str(dosya))
    assert "[SAATI GECTI]" in sonuc["result"]


def test_gelecek_saatli_gorev_etiketsiz(tmp_path):
    from datetime import timedelta as td
    gelecek = datetime.now() + td(hours=2)
    gorevler = [{"date": datetime.now().strftime("%Y-%m-%d"),
                 "text": "saat %02d:%02d'te discine yedek al"
                         % (gelecek.hour, gelecek.minute),
                 "done": False}]
    import json
    dosya = tmp_path / "gorevler.json"
    dosya.write_text(json.dumps(gorevler), encoding="utf-8")

    sonuc = bugunku_hatirlatmalar(str(tmp_path), str(dosya))
    assert "[SAATI GECTI]" not in sonuc["result"]
