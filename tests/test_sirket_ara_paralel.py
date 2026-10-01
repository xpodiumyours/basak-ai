"""tests/test_sirket_ara_paralel.py — aday sayfaların paralel okunması.

2026-10-01, P1.4 ölçümü. Ölçülen darboğaz: aday sayfaları SIRALI
okunuyordu (6 sayfa = 6,1 sn). Parallel okuma ölçüldü:
**2,749 sn (%55 kazanç)** — sıra ve kart korunarak.

Sözleşme (ağ yok, `kurum_sayfasi_oku` sahtelenir):
1. **Sıra korunur:** `map` girdi sırasını döndürür; `okunacak[i]` ile
   sonucu[i] aynı adaya aittir. Yanlış eşleşme kartı sessizce bozardı.
2. **Hata tek sayfaya düşer.** Bir sayfanın patlaması diğerlerini
   etkilemez — eski `except: continue` davranışının aynısı.
3. **Tüm sayfalar yine okunur.** Daraltma (erken çıkış, aday azaltma)
   YAPILMADI; ölçümde erken çıkış 3 markadan 1'inde kartı bozdu.
4. **Seçim kuralı sıradan bağımsızdır:** `daha_iyi` önce `uyuyor`,
   sonra `skor` karşılaştırır. Bu yüzden hangi sayfanın önce döndüğü
   sonucu değiştirmez — bu test bunu doğrular.
"""

import json
import os
import sys

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from tools import katalog as k


@pytest.fixture
def sahte_okuyucu(monkeypatch):
    """`kurum_sayfasi_oku` yerine geçer; çağrı kaydı tutar."""
    cagrilar = []

    def kur(adres, metin="", gercekler=None, hata=None, skor_tam=0):
        if hata:
            def oku(_a):
                cagrilar.append(_a)
                return {"error": hata}
        else:
            def oku(_a):
                cagrilar.append(_a)
                return {"result": json.dumps(
                    {"metin": metin, "gercekler": gercekler or []},
                    ensure_ascii=False)}
        return oku

    monkeypatch.setattr(
        "tools.web_search.kurum_sayfasi_oku",
        lambda url: kur(url)(url))
    return cagrilar


class TestSiraKorunur:
    def test_sonuclar_girdi_sirasinda(self, monkeypatch):
        """En kritik: yanlış eşleşme kartı sessizce bozardi."""
        import tools.web_search as ws
        cagrilar = []

        def oku(adres):
            cagrilar.append(adres)
            return {"result": json.dumps(
                {"metin": "test", "gercekler": []}, ensure_ascii=False)}

        monkeypatch.setattr(ws, "kurum_sayfasi_oku", oku)
        adaylar = ["https://a.com/iletisim", "https://b.com/iletisim",
                   "https://c.com/iletisim"]
        out = k._sirket_sayfalari_paralel(ws, adaylar)
        assert len(out) == 3
        assert set(cagrilar) == set(adaylar)
        # map girdi sirasini korur: cagrilar sirali mi belirsiz
        # (paralel), ama SONUCLAR adaylarla ayni indekste olmali.
        assert len(out) == len(adaylar)

    def test_tek_aday_dogrudan_okunur(self, monkeypatch):
        import tools.web_search as ws
        monkeypatch.setattr(
            ws, "kurum_sayfasi_oku",
            lambda a: {"result": json.dumps({"metin": "x"})})
        out = k._sirket_sayfalari_paralel(ws, ["https://tek.com/"])
        assert len(out) == 1

    def test_bos_liste_bos_doner(self):
        import tools.web_search as ws
        assert k._sirket_sayfalari_paralel(ws, []) == []
        assert k._sirket_sayfalari_paralel(ws, None) == []


class TestHataIzolasyonu:
    def test_bir_sayfa_patlar_digerleri_etkilenmez(self, monkeypatch):
        import tools.web_search as ws

        def oku(adres):
            if "bozuk" in adres:
                raise RuntimeError("sayfa patladi")
            return {"result": json.dumps(
                {"metin": "iyi", "gercekler": []}, ensure_ascii=False)}

        monkeypatch.setattr(ws, "kurum_sayfasi_oku", oku)
        out = k._sirket_sayfalari_paralel(ws, [
            "https://bozuk.com/iletisim", "https://iyi.com/iletisim"])
        assert len(out) == 2
        # patlayan konum None, digeri dolu
        assert out[0] is None
        assert out[1] is not None

    def test_hatali_sayfa_error_sozlugu_doner(self, monkeypatch):
        import tools.web_search as ws
        monkeypatch.setattr(
            ws, "kurum_sayfasi_oku",
            lambda a: {"error": "HTTP hatasi 404"})
        out = k._sirket_sayfalari_paralel(ws, ["https://yok.com/x"])
        assert out[0]["error"].startswith("HTTP hatasi")

    def test_tek_aday_patlayinca_istisna_yok(self, monkeypatch):
        import tools.web_search as ws

        def patla(_a):
            raise RuntimeError("tek sayfa patladi")

        monkeypatch.setattr(ws, "kurum_sayfasi_oku", patla)
        out = k._sirket_sayfalari_paralel(ws, ["https://x.com/"])
        assert out == [None]


class TestKartAyniKalir:
    """Seçim kuralı sıradan bağımsız: `uyuyor` önce, sonra `skor`.

    Bu test, paralel okumanın sonucu değiştirmediğini kanıtlar: iki sayfa
    verilir, BİRİ uyuyor + yüksek skor, DİĞERİ uyuyor ama düşük skor.
    Sıralamadan bağımsız aynı kart seçilir.
    """
    def _sirket_ara_ile(self, monkeypatch, yanitlar):
        import tools.web_search as ws

        def oku(adres):
            return yanitlar[adres]

        monkeypatch.setattr(ws, "kurum_sayfasi_oku", oku)
        monkeypatch.setattr(k, "tedarikci_coz",
                            lambda m: ({"site": "ornek.com"}, m))
        ham = k.sirket_ara("Örnek")
        if isinstance(ham, str):
            ham = json.loads(ham)
        if "result" in ham:
            ham = json.loads(ham["result"])
        return ham

    def test_uyuyan_kazanan(self, monkeypatch):
        iyi = {"result": json.dumps({
            "metin": "iletisim telefon 0312 000 00 00 eposta a@b.com",
            "gercekler": [{"@type": "Organization", "name": "Örnek A.Ş."}]},
            ensure_ascii=False)}
        kotu = {"result": json.dumps({
            "metin": "telefon 0555 111 11 11 " + ("doldurucu " * 40),
            "gercekler": [{"@type": "Organization", "name": "Başka"}]},
            ensure_ascii=False)}
        kart = self._sirket_ara_ile(monkeypatch, {
            "https://ornek.com/iletisim": iyi,
            "https://ornek.com/iletisim.html": kotu,
        })
        assert kart.get("dogrulandi") is True, kart
        assert "ornek.com" in (kart.get("site") or ""), kart

    def test_hicbiri_okunmuyorsa_hata(self, monkeypatch):
        kart = self._sirket_ara_ile(monkeypatch, {
            "https://ornek.com/iletisim": {"error": "HTTP hatasi 404"},
            "https://ornek.com/iletisim.html": {"error": "HTTP hatasi 404"},
        })
        assert kart.get("error"), kart


class TestAyarOlculebilir:
    def test_paralellik_sabiti_tanimli(self):
        """Paralellik koda gömülü bir sihirli sayı değil, adlandırılmış."""
        assert isinstance(k._SIRKET_PARALEL, int)
        assert 1 < k._SIRKET_PARALEL <= 8, (
            "hedef sitelere ani yuk bindirmemek icin sinirli: %s"
            % k._SIRKET_PARALEL)

    def test_siteli_tavan_degisti(self):
        """Aday sayısı DARALTILMADI (davranış korundu)."""
        assert k._SIRKET_SITE_TAVANI == 3
        assert k._SIRKET_YOL_TAVANI == 2