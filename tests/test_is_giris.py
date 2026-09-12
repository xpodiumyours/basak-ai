"""tests/test_is_giris.py - Is girisi + is_notu + uzun tur testleri (P-A).

A2: ac/kapat kapisi, akisa blok yukleme, is_notu araci.
A3: aktif is turunda tur tavani esner (8), varsayilan yol aynidir (3/12).
"""

import os
import sys
from types import SimpleNamespace

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import chat  # once tam paket (dairesel import onlemi)
import chat.flow as flow
from tools import isdosya as D


def _yeni_kok(monkeypatch, tmp_path):
    kok = str(tmp_path / "isler")
    monkeypatch.setattr(D, "KOK", kok)
    return kok


class TestTurGirisi:
    def test_bos_turda_sifir(self, monkeypatch, tmp_path):
        kok = _yeni_kok(monkeypatch, tmp_path)
        olay, blok, uzun = D.tur_girisi("masaüstünde ne var", kok=kok)
        assert (olay, blok, uzun) == (None, "", False)
        assert D.aktif_id(kok=kok) is None

    def test_ac_komutu_dosya_acar(self, monkeypatch, tmp_path):
        kok = _yeni_kok(monkeypatch, tmp_path)
        olay, blok, uzun = D.tur_girisi(
            "Vixrex için müşteri bul, bunu takip et", kok=kok)
        assert uzun is True
        assert "İş dosyası açıldı" in (olay or "")
        assert "## HEDEF" in blok
        assert D.aktif_id(kok=kok) is not None

    def test_ikinci_turda_blok_var_not_yok(self, monkeypatch, tmp_path):
        kok = _yeni_kok(monkeypatch, tmp_path)
        D.tur_girisi("müşteri bul, bunu takip et", kok=kok)
        olay, blok, uzun = D.tur_girisi("nerede kalmıştık", kok=kok)
        assert olay is None
        assert uzun is True
        assert "## HEDEF" in blok

    def test_kapat_komutu(self, monkeypatch, tmp_path):
        kok = _yeni_kok(monkeypatch, tmp_path)
        D.tur_girisi("müşteri bul, bunu takip et", kok=kok)
        olay, blok, uzun = D.tur_girisi("işi kapat", kok=kok)
        assert "kapatıldı" in (olay or "")
        assert (blok, uzun) == ("", False)
        assert D.aktif_id(kok=kok) is None

    def test_kapatilmis_ise_yazilmaz(self, monkeypatch, tmp_path):
        kok = _yeni_kok(monkeypatch, tmp_path)
        D.tur_girisi("müşteri bul, bunu takip et", kok=kok)
        sid = D.aktif_id(kok=kok)
        D.is_kapat(sid, kok=kok)
        assert "error" in D.is_notu_yaz(sid, "plan", "x", kok=kok)


class TestIsNotuAraci:
    def test_tanim_izin_taninmis(self):
        from tools.definitions import TOOLS, EXTENDED_TETIKLERI
        from tools.permissions import ETIKETLER, calistirilabilir_mi
        from chat.tools import TANINMIS_TOOLLAR
        adlar = {t["function"]["name"] for t in TOOLS}
        assert "is_notu" in adlar
        assert "is_notu" in ETIKETLER
        assert "is_notu" in TANINMIS_TOOLLAR
        assert "is_notu" in EXTENDED_TETIKLERI
        assert calistirilabilir_mi("is_notu") is True

    def test_calistir_yazar(self, monkeypatch, tmp_path):
        kok = _yeni_kok(monkeypatch, tmp_path)
        sid = D.is_ac_dosya("T", "H", kok=kok)["is_id"]
        from tools.executor import calistir
        r = calistir("is_notu",
                     {"is_id": sid, "bolum": "plan", "metin": "1. ara"},
                     knowledge_dir="kd", gorevler_file="gf")
        assert "result" in r, r
        assert "1. ara" in D.is_oku(sid, kok=kok)

    def test_hedef_yazilamaz(self, monkeypatch, tmp_path):
        kok = _yeni_kok(monkeypatch, tmp_path)
        sid = D.is_ac_dosya("T", "H", kok=kok)["is_id"]
        from tools.executor import calistir
        r = calistir("is_notu",
                     {"is_id": sid, "bolum": "hedef", "metin": "x"},
                     knowledge_dir="kd", gorevler_file="gf")
        assert "error" in r


class SahteBeyin:
    def __init__(self):
        self.mesajlar = None
        self.verilen_araclar = None

    def yerel_modeller(self):
        return ["m"]

    def bulut_musait(self):
        return True

    def _bulut_zinciri(self):
        return []

    def cevapla(self, messages, yerel_model, tools=None, **kw):
        self.mesajlar = messages
        self.verilen_araclar = [t["function"]["name"] for t in (tools or [])]
        return {"content": "ok"}, "sahte"


def _akis_hazirla(monkeypatch):
    import _chat_legacy as legacy
    import chat.context as _ctx
    import memory.profil as _profil
    monkeypatch.setattr(legacy, "yukle", lambda *a, **k: {})
    monkeypatch.setattr(legacy, "kaydet", lambda *a, **k: None)
    monkeypatch.setattr(legacy, "_save_and_reply", lambda *a, **k: None)
    monkeypatch.setattr(legacy, "_hafiza_al", lambda: None)
    monkeypatch.setattr(legacy, "_ilgili_anilar", lambda *a, **k: [])
    monkeypatch.setattr(_ctx, "hafiza_al", lambda: None)
    monkeypatch.setattr(_profil, "unut", lambda *a, **k: 0)
    monkeypatch.setattr(_profil, "ogren", lambda *a, **k: [])
    monkeypatch.setattr(_profil, "blok", lambda m: "")


def _sistem(beyin):
    return "\n".join(m.get("content", "") for m in beyin.mesajlar
                     if m.get("role") == "system")


class TestAkisYukleme:
    def test_issiz_turda_isblogu_yok(self, monkeypatch, tmp_path):
        _yeni_kok(monkeypatch, tmp_path)
        _akis_hazirla(monkeypatch)
        from tools import TOOLS
        beyin = SahteBeyin()
        flow.mesaj_isle_yeni("masaüstünde ne var", beyin, "SYS",
                             lambda c: None, TOOLS)
        assert "Aktif iş dosyası" not in _sistem(beyin)

    def test_ac_komutunda_blok_ve_not(self, monkeypatch, tmp_path):
        _yeni_kok(monkeypatch, tmp_path)
        _akis_hazirla(monkeypatch)
        from tools import TOOLS
        beyin = SahteBeyin()
        flow.mesaj_isle_yeni("müşteri bul, bunu takip et", beyin, "SYS",
                             lambda c: None, TOOLS)
        metin = _sistem(beyin)
        assert "Aktif iş dosyası" in metin
        assert "is_notu" in metin
        assert "is_notu" in beyin.verilen_araclar

    def test_devam_turunda_blok_var(self, monkeypatch, tmp_path):
        kok = _yeni_kok(monkeypatch, tmp_path)
        _akis_hazirla(monkeypatch)
        from tools import TOOLS
        D.tur_girisi("müşteri bul, bunu takip et", kok=kok)
        beyin = SahteBeyin()
        flow.mesaj_isle_yeni("nerede kalmıştık", beyin, "SYS",
                             lambda c: None, TOOLS)
        assert "Aktif iş dosyası" in _sistem(beyin)
        assert "is_notu" in beyin.verilen_araclar


CAGRI = [{"id": "c1", "type": "function",
          "function": {"name": "web_search", "arguments": "{}"}}]


class SayacBeyin:
    def __init__(self):
        self.cagri = 0

    def _bulut_zinciri(self):
        return []

    def cevapla(self, messages, model, tools=None, **kw):
        self.cagri += 1
        return {"content": "", "tool_calls": CAGRI}, "sahte"


class TestUzunTur:
    def _kos(self, monkeypatch, uzun_is):
        import brain.kapasite as _kap
        monkeypatch.setattr(
            _kap, "mod_kapasite",
            lambda *a, **k: SimpleNamespace(kucuk=True, guclu=False))
        from chat.tools import tool_calling_multi
        beyin = SayacBeyin()
        tools = [{"type": "function",
                  "function": {"name": "web_search"}}]
        tool_calling_multi(
            CAGRI, [{"role": "user", "content": "araştır"}], beyin, "m",
            lambda c: None,
            lambda *a, **k: {"result": "ok"},
            tools, uzun_is=uzun_is)
        return beyin.cagri

    def test_kisa_tur_uc_turda_durur(self, monkeypatch):
        assert self._kos(monkeypatch, False) == 3

    def test_uzun_is_sekiz_tura_cikar(self, monkeypatch):
        assert self._kos(monkeypatch, True) == 8
