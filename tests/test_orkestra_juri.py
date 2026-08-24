"""tests/test_orkestra_juri.py — ORKESTRA-1 DIVERSIFY/CRITICIZE testleri.

Kabul ölçütleri (2026-08-24):
- Jüri bileşeni YOKSA v0 davranışı birebir korunur (izde FAY-1 atlaması)
- ek_adaylar varsa alternatifler PARALEL koşar; hata veren aday düşer,
  akış tek adayla devam eder
- aday_puanla kazananı belirler; eşitlikte BİRİNCİL kazanır
- boş/ölçemedim adayı otomatik elenir; kapıdan cümle yiyen aday cezalanır
- arac_var=True sinyali bileşene iletilir (jüri araç turlarında koşmaz)
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from brain.orkestra import Orkestra


def bilesenler(**fazlalar):
    b = {
        "observe": lambda s: (s.strip(), None),
        "model_baglami": lambda: "NOTLAR",
        "anilar": lambda s: [],
        "gecmis_pencere": lambda g: g,
        "siniflandir": lambda t: "genel",
        "dinamik_araclar": lambda t, tools: tools,
        "aday_uret": lambda mesajlar, araclar: (
            {"content": "birincil cevap"}, "groq"),
        "deney_kos": lambda tc, ms=None: None,
        "olcu_kapisi": lambda metin, o: (metin, []),
        "ham_olcum": lambda o: [],
        "ogren": lambda s, c, onem=1: None,
    }
    b.update(fazlalar)
    return b


def iz_ozeti(rapor):
    return {i["durum"]: i for i in rapor["iz"]}


class TestJuriYok:
    def test_bilesen_yoksa_v0_korunur(self):
        rapor = Orkestra(bilesenler()).kos("merhaba")
        d = iz_ozeti(rapor)
        assert d["DIVERSIFY"]["atlandi"] is True
        assert "FAY-1" in d["DIVERSIFY"]["sebep"]
        assert rapor["cevap"] == "birincil cevap"
        assert rapor["kaynak"] == "groq"

    def test_aday_puanla_tek_basina_davranisi_degistirmez(self):
        b = bilesenler(aday_puanla=lambda t, e: 0)
        rapor = Orkestra(b).kos("merhaba")
        assert rapor["cevap"] == "birincil cevap"
        assert "puan:" in iz_ozeti(rapor)["CRITICIZE"]["ozet"]


class TestDiversify:
    def test_iki_alternatif_paralel_donuyor(self):
        alinan_mesajlar = []

        def alt_a(ms):
            alinan_mesajlar.append(("alt-a", len(ms)))
            return {"content": "alternatif A cevabi"}

        def alt_b(ms):
            alinan_mesajlar.append(("alt-b", len(ms)))
            return {"content": "alternatif B cevabi"}

        def ek_adaylar(birincil, ms, arac_var=False):
            assert birincil == "groq"       # birincil kaynağı görüyor
            assert arac_var is False
            return [("alt-a", alt_a), ("alt-b", alt_b)]

        rapor = Orkestra(bilesenler(ek_adaylar=ek_adaylar)).kos("merhaba")
        d = iz_ozeti(rapor)
        assert d["DIVERSIFY"]["atlandi"] is False
        assert "2 ek aday" in d["DIVERSIFY"]["ozet"]
        # Eşitlik → birincil kazanır
        assert rapor["cevap"] == "birincil cevap"
        assert rapor["kaynak"] == "groq"
        assert len(alinan_mesajlar) == 2    # her ikisi de koştu

    def test_hata_veren_aday_duser_akis_devam_eder(self):
        def patlak(ms):
            raise RuntimeError("saglayici kacti")

        def saglam(ms):
            return {"content": "saglam alternatif"}

        b = bilesenler(
            ek_adaylar=lambda k, ms, arac_var=False:
                [("patlak", patlak), ("saglam", saglam)])
        rapor = Orkestra(b).kos("merhaba")
        d = iz_ozeti(rapor)
        assert d["DIVERSIFY"]["atlandi"] is False
        assert "1 ek aday" in d["DIVERSIFY"]["ozet"]
        assert rapor["cevap"] == "birincil cevap"

    def test_ek_adaylar_hatasi_tek_adaya_duser(self):
        """Kurulum hatası dürüstçe ATLANDI+sebep olarak kaydedilir;
        akış birincil adayla zarifçe devam eder."""
        def patlak(k, ms, arac_var=False):
            raise RuntimeError("juri kurulum hatasi")
        b = bilesenler(ek_adaylar=patlak)
        rapor = Orkestra(b).kos("merhaba")
        d = iz_ozeti(rapor)
        assert d["DIVERSIFY"]["atlandi"] is True
        assert "kurulum hatasi" in d["DIVERSIFY"]["sebep"]
        assert rapor["cevap"] == "birincil cevap"


class TestCriticizeSecim:
    def test_bos_birincil_yerine_saglam_alternatif_kazanir(self):
        def birincil(m, a):
            return {"content": ""}, "groq"

        def alt(ms):
            return {"content": "dolu alternatif cevap"}

        b = bilesenler(
            aday_uret=birincil,
            ek_adaylar=lambda k, ms, arac_var=False: [("glm", alt)])
        rapor = Orkestra(b).kos("merhaba")
        assert rapor["cevap"] == "dolu alternatif cevap"
        assert rapor["kaynak"] == "glm"

    def test_kapidan_cok_eyen_aday_puanla_cezalanir(self):
        def birincil(m, a):
            return {"content": "temiz birincil cevap"}, "groq"

        def alt(ms):
            return {"content": "uzun ama uyduruk alternatif cevap"}

        # Birincil temiz geçti; alternatif 3 cümle yedi
        def kapi(metin, o):
            if "uyduruk" in metin:
                return metin, ["e1", "e2", "e3"]
            return metin, []

        # Üretimdeki politikanın aynısı (chat.py aday_puanla)
        puanla = lambda tem, elenen: (
            -50 if not tem or tem.strip() == "Bunu ölçemedim."
            else -elenen * 5)

        b = bilesenler(
            aday_uret=birincil,
            ek_adaylar=lambda k, ms, arac_var=False: [("glm", alt)],
            olcu_kapisi=kapi,
            aday_puanla=puanla)
        rapor = Orkestra(b).kos("merhaba")
        ozet = iz_ozeti(rapor)["CRITICIZE"]["ozet"]
        assert "birincil=0" in ozet and "glm=-15" in ozet
        assert rapor["cevap"] == "temiz birincil cevap"

    def test_olcemedim_adayi_otomatik_elener(self):
        def birincil(m, a):
            return {"content": "Bunu ölçemedim."}, "groq"

        def alt(ms):
            return {"content": "el yordamiyla cevap"}

        b = bilesenler(
            aday_uret=birincil,
            ek_adaylar=lambda k, ms, arac_var=False: [("nvidia", alt)])
        rapor = Orkestra(b).kos("merhaba")
        assert rapor["cevap"] == "el yordamiyla cevap"
        assert rapor["kaynak"] == "nvidia"


class TestAracTuruSinyali:
    def test_arac_var_bilesene_bildirilir(self):
        gorulen = {}

        def birincil(m, a):
            return {"content": "", "tool_calls": [{"x": 1}]}, "groq"

        def ek_adaylar(k, ms, arac_var=False):
            gorulen["arac_var"] = arac_var
            return []

        b = bilesenler(aday_uret=birincil, ek_adaylar=ek_adaylar)
        Orkestra(b).kos("durum ne?")
        assert gorulen["arac_var"] is True


class TestLearnKazananla:
    def test_learn_kazanan_cevapla_calisir(self):
        ogrenilen = []

        def birincil(m, a):
            return {"content": ""}, "groq"

        def alt(ms):
            return {"content": "kazanan alternatif"}

        b = bilesenler(
            aday_uret=birincil,
            ek_adaylar=lambda k, ms, arac_var=False: [("glm", alt)],
            ogren=lambda s, c, onem=1: ogrenilen.append(c))
        Orkestra(b).kos("merhaba")
        assert ogrenilen == ["kazanan alternatif"]
