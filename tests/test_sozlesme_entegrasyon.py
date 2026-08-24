"""tests/test_sozlesme_entegrasyon.py — FAZ 1.3 sözleşme kapısı entegrasyonu.

Sözleşme kapısının CANLI zincire bağlanması (chat.mesaj_isle):
- çift yol kapı (_kapidan_gecir): geçerli JSON → yapısal kapı,
  düz metin → eski işaret kapısı
- yapi sozlesmesinin her iki brain.cevapla çağrısına taşınması
- prompt bloğu seçimi (SOZLESME_PROMPTU <-> PROMPT_BLOGU)
- orkestra bileşenlerinin yeni parçaları sunması

test_gerceklik_kapisi.py / test_yetki_tavani.py gibi GERÇEK mesaj_isle
sahte beyinle koşturulur; ağ/model yok.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

import chat as c
from olcu import (PROMPT_BLOGU, SOZLESME_PROMPTU, YEDEK_CUMLE,
                  sozlesme_coz, sozlesme_kapisi)

# brain.cevapla'ya yapi kwarg'i GELMEDIGINDE yakalanacak muhafız
GELMEDI = "__yapi_kwarg_gelmedi__"

GIT_CIKTISI = "Proje: vixrex Dal: main Son commit: 20da1a7"


def _schema(ad):
    return {"type": "function",
            "function": {"name": ad, "description": "",
                         "parameters": {"type": "object", "properties": {}}}}


def soz_json(yanit, iddialar):
    """Geçerli şemalı sözleşme JSON'u (model çıktısı taklidi)."""
    return json.dumps({"yanit": yanit, "iddialar": iddialar},
                      ensure_ascii=False)


def olcum_iddia(metin, arac="git_durum"):
    return {"metin": metin, "tur": "olcum", "dayanak": {"arac": arac}}


def arac_cagrisi(ad="git_durum"):
    return {"content": "", "tool_calls": [
        {"id": "1", "type": "function",
         "function": {"name": ad,
                      "arguments": "{\"proje\": \"vixrex\"}"}}]}


class SahteBrain:
    """Script'li beyin: mesajları/tools/yapi'yi yakalar."""

    def __init__(self, yanitlar):
        self._yanitlar = [
            y if isinstance(y, dict) else {"content": y}
            for y in yanitlar]
        self.cagrilar = []

    def yerel_modeller(self):
        return ["sahte-model"]

    def bulut_musait(self):
        return True

    def cevapla(self, mesajlar, model, tools=None, override_model=None,
                yapi=GELMEDI):
        self.cagrilar.append({"mesajlar": mesajlar, "tools": tools,
                              "override_model": override_model, "yapi": yapi})
        return self._yanitlar.pop(0), "sahte"


class EskiImzaBrain:
    """FAZ 1.1 öncesi imza: yapi parametresi YOK — patlamamalı."""

    def __init__(self):
        self.cagrildi = 0

    def yerel_modeller(self):
        return ["sahte-model"]

    def bulut_musait(self):
        return True

    def cevapla(self, mesajlar, model, tools=None, override_model=None):
        self.cagrildi += 1
        return ({"content": "Bugun hava cok guzel, aksam cay iceriz."},
                "sahte")


@pytest.fixture(autouse=True)
def yalit(monkeypatch, tmp_path):
    """Gercek dosyalara dokunmayan mesaj_isle ortami; mod ACIK baslar."""
    monkeypatch.setattr(c, "HISTORY_FILE", str(tmp_path / "gecmis.json"))
    monkeypatch.setattr(c, "SETTINGS_FILE", str(tmp_path / "ayarlar.json"))
    monkeypatch.setattr(c, "_hafiza", False)
    monkeypatch.setattr(c, "_SOZLESME_MODU", "acik")
    monkeypatch.setattr("tools.calistir",
                        lambda ad, args, kdir="", gdosya="":
                        {"result": GIT_CIKTISI})


def _kos(text, brain, tools=None):
    """mesaj_isle koşturur; reply/error değerlerini yakalar."""
    kutu = {"reply": [], "error": []}

    def cb(code):
        if code.startswith(("BasakUI.reply", "BasakUI.error")):
            ic = code[code.index("(") + 1:code.rindex(")")]
            anahtar = "reply" if code.startswith("BasakUI.reply") else "error"
            kutu[anahtar].append(json.loads("[" + ic + "]")[0])

    c.mesaj_isle(text, brain, "SYS", cb, tools)
    return kutu


class TestKapiV2:
    def test_json_yapisal_kapidan_gecer(self):
        """Geçerli sözleşme JSON'u → yapısal kapı (rapor dict)."""
        ham = soz_json("Selam!", [])
        temiz, rapor = c._kapidan_gecir(ham, [])
        assert isinstance(rapor, dict) and rapor["gecerli"] is True
        assert temiz == "Selam!"

    def test_duz_metin_eski_kapidan_gecirir(self):
        """JSON'suz metin → eski işaret kapısı (rapor liste)."""
        temiz, rapor = c._kapidan_gecir("VixRex main dalinda.", [])
        assert isinstance(rapor, list)
        assert temiz == YEDEK_CUMLE

    def test_kapali_modda_json_eski_kapidan_gecer(self, monkeypatch):
        """Mod kapaliysa GEÇERLI JSON bile eski kapıya gider."""
        monkeypatch.setattr(c, "_SOZLESME_MODU", "kapali")
        temiz, rapor = c._kapidan_gecir(soz_json("Selam!", []), [])
        assert isinstance(rapor, list)
        assert "Selam!" in temiz


class TestSozlesmeZinciri:
    def test_a_gecerli_sozlesme_kanitli_cumle_isaretsiz_yasar(self):
        """(a) Beyan edilen iddia koşan araçla kanıtlanır; [Ö]/[A]
        işareti OLMADAN yaşar."""
        brain = SahteBrain([
            arac_cagrisi(),
            soz_json("VixRex su an main dalinda, son commit 20da1a7.",
                     [olcum_iddia("main dalinda")]),
        ])
        kutu = _kos("VixRex durum ne?", brain, [_schema("git_durum")])
        assert kutu["error"] == []
        cevap = kutu["reply"][0]
        assert "main dalinda" in cevap and "20da1a7" in cevap
        assert "[Ö" not in cevap and "[A]" not in cevap

    def test_b_beyansiz_eylem_oldurulur(self):
        """(b) Araçsız turda beyan edilmemiş eylem iddiası ölür."""
        brain = SahteBrain([
            soz_json("Bilgileri deftere kaydettim.", []),
        ])
        kutu = _kos("merhaba nasilsin?", brain, None)
        assert YEDEK_CUMLE in kutu["reply"][0]

    def test_c_jsonsiz_duz_metin_eski_kapida_oldurulur(self):
        """(c) Sözleşme modu açıkken düz metin eski kapıdan geçer;
        işaretsiz ölçü-alanı cümlesi bugünkü gibi elenir."""
        brain = SahteBrain(["VixRex su anda main dalinda, yolunda."])
        kutu = _kos("merhaba nasilsin?", brain, None)
        assert YEDEK_CUMLE in kutu["reply"][0]

    def test_c_jsonsiz_duz_sohbet_acik_modda_yasar(self):
        """(c) Eski kapının yaşatma davranışı aynen korunur."""
        metin = "Selam! Bugun cok yogun gecti, sen nasilsin?"
        brain = SahteBrain([metin])
        kutu = _kos("merhaba nasilsin?", brain, None)
        for parca in ("Selam!", "yogun gecti", "nasilsin?"):
            assert parca in kutu["reply"][0]

    def test_acik_modda_sozlesme_jsonu_temiz_prose_donuser(self):
        """Açık modda JSON yapısı sökülür; kullanıcı ham JSON görmez."""
        brain = SahteBrain([soz_json("Selam! Bugun nasilsin?", [])])
        kutu = _kos("merhaba nasilsin?", brain, None)
        cevap = kutu["reply"][0]
        assert "{" not in cevap and "iddialar" not in cevap
        for parca in ("Selam!", "Bugun nasilsin?"):
            assert parca in cevap

    def test_d_kapali_modda_json_braces_ile_gecer(self, monkeypatch):
        """(d) Kapalı modda aynı JSON DÜZ METİN sayılır: eski kapı
        sözleşme kurallarını uygulamaz, süslü parantezler ayakta kalır."""
        monkeypatch.setattr(c, "_SOZLESME_MODU", "kapali")
        brain = SahteBrain([soz_json("Selam! Bugun nasilsin?", [])])
        kutu = _kos("merhaba nasilsin?", brain, None)
        cevap = kutu["reply"][0]
        assert '"yanit"' in cevap and "Selam!" in cevap

    def test_d_kapali_modda_olcu_jsonu_eski_kuralla_oldurulur(
            self, monkeypatch):
        """(d) Kapalı modda ölçü-alanı cümlesi taşıyan JSON, eski kapının
        işaretsiz-ölçü kuralına takılır (sözleşme kuralı DEĞİL)."""
        monkeypatch.setattr(c, "_SOZLESME_MODU", "kapali")
        brain = SahteBrain([
            soz_json("VixRex su an main dalinda.",
                     [olcum_iddia("main dalinda")]),
        ])
        kutu = _kos("merhaba nasilsin?", brain, None)
        assert YEDEK_CUMLE in kutu["reply"][0]


class TestYapiThread:
    def test_e_acik_modda_yapi_json_object_gider(self):
        """(e) Mod açıkken brain.cevapla yapi={"type": "json_object"} alır."""
        brain = SahteBrain(["Selam! Bugun cok yogun gecti."])
        _kos("merhaba nasilsin?", brain, None)
        assert brain.cagrilar[0]["yapi"] == {"type": "json_object"}

    def test_e_kapali_modda_yapi_none_kwarg_ile_gider(self, monkeypatch):
        """(e) Mod kapalıyken kwarg GİDER ama değeri None'dır."""
        monkeypatch.setattr(c, "_SOZLESME_MODU", "kapali")
        brain = SahteBrain(["Selam! Bugun cok yogun gecti."])
        _kos("merhaba nasilsin?", brain, None)
        assert brain.cagrilar[0]["yapi"] is None

    def test_eski_imzali_beyin_yapi_siz_calisir(self):
        """FAZ 1.1 öncesi imzalı beyin TypeError almaz; akış tamamlanır."""
        brain = EskiImzaBrain()
        kutu = _kos("merhaba nasilsin?", brain, None)
        assert brain.cagrildi == 1
        assert kutu["error"] == []
        assert "cay iceriz" in kutu["reply"][0]


class TestPromptSecimi:
    def test_f_acik_modda_sozlesme_promptu_gider(self):
        """(f) Açık mod: SOZLESME_PROMPTU var, PROMPT_BLOGU yok;
        OLCU_YONLENDIRME her iki modda kalır."""
        brain = SahteBrain(["Selam!"])
        _kos("merhaba nasilsin?", brain, None)
        tp = brain.cagrilar[0]["mesajlar"][0]["content"]
        assert "CEVAP SOZLESMESI" in tp
        assert "CEVAP BİÇİMİ" not in tp
        assert "ÖLÇÜM ÖNCE GELİR" in tp

    def test_f_kapali_modda_eski_blogu_gider(self, monkeypatch):
        """(f) Kapalı mod: PROMPT_BLOGU geri gelir, sözleşme bloğu yok."""
        monkeypatch.setattr(c, "_SOZLESME_MODU", "kapali")
        brain = SahteBrain(["Selam!"])
        _kos("merhaba nasilsin?", brain, None)
        tp = brain.cagrilar[0]["mesajlar"][0]["content"]
        assert "CEVAP BİÇİMİ" in tp
        assert "CEVAP SOZLESMESI" not in tp
        assert "ÖLÇÜM ÖNCE GELİR" in tp


class TestAracDongusu:
    def test_g_dongu_sonunda_yapisal_kapi_kanitla_calisir(self):
        """(g) Tool-loop dönüşü sözleşme JSON'u döndürünce kapı #2 yapısal
        yoldan denetler; kanıt koşan araca karşı doğrulanır."""
        brain = SahteBrain([
            arac_cagrisi(),
            soz_json("VixRex su an main dalinda, son commit 20da1a7.",
                     [olcum_iddia("main dalinda")]),
        ])
        kutu = _kos("VixRex durum ne?", brain,
                    [_schema("git_durum"), _schema("save_note")])
        # Yetki tavani: yalnız ölçü ailesi sunuldu; dongu seti buyumez
        assert [t["function"]["name"]
                for t in brain.cagrilar[0]["tools"]] == ["git_durum"]
        assert [t["function"]["name"]
                for t in brain.cagrilar[1]["tools"]] == ["git_durum"]
        # Her iki çağrı da yapı sözleşmesi taşıdı
        assert brain.cagrilar[0]["yapi"] == {"type": "json_object"}
        assert brain.cagrilar[1]["yapi"] == {"type": "json_object"}
        cevap = kutu["reply"][0]
        assert "main dalinda" in cevap
        assert "[Ö" not in cevap


class TestOrkestraBilesenleri:
    def test_h_bilesenler_yeni_parcalari_sunar(self):
        """(h) Bileşen sözlüğü kapi_v2/sozlesme_coz/sozlesme_kapisi verir;
        kapi_v2 gerçekten çift yolu koşturuyor."""
        bilesenler = c.orkestra_bilesenleri(SahteBrain([]))
        assert bilesenler["kapi_v2"] is c._kapidan_gecir
        assert bilesenler["sozlesme_coz"] is sozlesme_coz
        assert bilesenler["sozlesme_kapisi"] is sozlesme_kapisi
        temiz, rapor = bilesenler["kapi_v2"](soz_json("Merhaba!", []), [])
        assert isinstance(rapor, dict) and temiz == "Merhaba!"
