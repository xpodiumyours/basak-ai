"""tests/test_canary.py — CANARY modu testleri (2026-08-24).

CANLI-KAPISI.md Faz 1: "calisma_modu": "canary" iken yazma ve sistem
araçlarının TAMAMI kodla kapalıdır; salt-okunur ve internet akar.
Dış projeler yalnız izinli_projeler listesinden açılır.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools import executor
from tools import permissions as p


def _ayar(monkeypatch, tmp_path, sozluk):
    yol = tmp_path / "ayarlar.json"
    yol.write_text(json.dumps(sozluk), encoding="utf-8")
    monkeypatch.setattr(p, "SETTINGS_YOLU", str(yol))


@pytest.fixture()
def taban(tmp_path):
    bilgi = tmp_path / "knowledge"
    bilgi.mkdir()
    (tmp_path / "gorevler.json").write_text("[]", encoding="utf-8")
    return str(tmp_path)


YAZMA_ARACLARI = ("save_note", "add_task", "write_file_tool",
                  "deftere_kaydet", "complete_task")


class TestCanaryModu:
    def test_normal_modda_yazma_akar(self, monkeypatch, taban):
        yol = os.path.join(taban, "ayarlar.json")
        open(yol, "w", encoding="utf-8").write('{"calisma_modu": "normal"}')
        orig = p.SETTINGS_YOLU
        p.SETTINGS_YOLU = yol
        try:
            for ad in YAZMA_ARACLARI:
                assert p.calistirilabilir_mi(ad), ad
            r = executor.calistir(
                "save_note", {"title": "t", "content": "c"},
                knowledge_dir=os.path.join(taban, "knowledge"),
                gorevler_file=os.path.join(taban, "gorevler.json"))
            assert "error" not in r
        finally:
            p.SETTINGS_YOLU = orig

    def test_canary_yazmanin_tamamini_kapatir(self, monkeypatch, taban):
        yol = os.path.join(taban, "ayarlar.json")
        open(yol, "w", encoding="utf-8").write(
            '{"calisma_modu": "canary"}')
        orig = p.SETTINGS_YOLU
        p.SETTINGS_YOLU = yol
        try:
            for ad in YAZMA_ARACLARI:
                assert not p.calistirilabilir_mi(ad), ad
            # uçtan uca: save_note çağrısı güvenlik engeli döner
            r = executor.calistir(
                "save_note", {"title": "t", "content": "c"},
                knowledge_dir=os.path.join(taban, "knowledge"),
                gorevler_file=os.path.join(taban, "gorevler.json"))
            assert "CANARY" in r.get("error", "")
            # salt-okunur akar
            assert p.calistirilabilir_mi("list_tasks") is True
            assert p.calistirilabilir_mi("git_durum") is True
        finally:
            p.SETTINGS_YOLU = orig

    def test_canary_sistem_aracini_opt_in_ile_bile_acmaz(self,
                                                        monkeypatch,
                                                        taban):
        yol = os.path.join(taban, "ayarlar.json")
        open(yol, "w", encoding="utf-8").write(json.dumps({
            "calisma_modu": "canary",
            "sistem_araclari_acik": True}))
        orig = p.SETTINGS_YOLU
        p.SETTINGS_YOLU = yol
        try:
            assert p.calistirilabilir_mi("ac_uygulama") is False
            r = executor.calistir("ac_uygulama",
                                  {"uygulama": "notepad"},
                                  knowledge_dir=taban,
                                  gorevler_file="x")
            assert "CANARY" in r.get("error", "")
        finally:
            p.SETTINGS_YOLU = orig

    def test_gecersiz_mod_degeri_normale_duser(self, monkeypatch, taban):
        yol = os.path.join(taban, "ayarlar.json")
        open(yol, "w", encoding="utf-8").write(
            '{"calisma_modu": "yakinmod"}')
        orig = p.SETTINGS_YOLU
        p.SETTINGS_YOLU = yol
        try:
            assert p.calisma_modu() == "normal"
            assert p.calistirilabilir_mi("save_note") is True
        finally:
            p.SETTINGS_YOLU = orig


class TestCanaryDisProjeler:
    def test_beyaz_listedeki_dis_proje_acilir(self, monkeypatch, taban):
        yol = os.path.join(taban, "ayarlar.json")
        open(yol, "w", encoding="utf-8").write(json.dumps({
            "calisma_modu": "canary",
            "izinli_projeler": ["vixrex"]}))
        orig = p.SETTINGS_YOLU
        p.SETTINGS_YOLU = yol
        try:
            from tools.file_ops import read_file
            # Yol izni verilir (dosya gerçekte var olmayabilir —
            # önemli olan 'izin' katmanının geçmesidir)
            r = read_file("vixrex/README.md", taban)
            assert "dış proje" not in r.get("error", "")
            assert "Canary modu:" not in r.get("error", "")
        finally:
            p.SETTINGS_YOLU = orig

    def test_liste_disindaki_dis_proje_engellenir(self, monkeypatch,
                                                  taban):
        yol = os.path.join(taban, "ayarlar.json")
        open(yol, "w", encoding="utf-8").write(json.dumps({
            "calisma_modu": "canary",
            "izinli_projeler": ["vixrex"]}))
        orig = p.SETTINGS_YOLU
        p.SETTINGS_YOLU = yol
        try:
            from tools.file_ops import read_file
            r = read_file("xses/src/main.py", taban)
            assert "Canary modu:" in r.get("error", "")
        finally:
            p.SETTINGS_YOLU = orig
