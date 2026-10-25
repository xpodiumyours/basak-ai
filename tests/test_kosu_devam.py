"""Kosu defterinin ajana baglanmasi: adim kaydi, tekrar korumasi, devam.

Bu dosya "defter var" demiyor; defterin GERCEK ajan yolunda kullanildigini
olcuyor: arac dongusu her cagriyi yazar, kapanmis cagri yeniden calismaz,
devam paketi modele onceki arac sonuclarini gercekten geri verir.
"""

import pytest

from chat import kosu_deposu as kd


@pytest.fixture(autouse=True)
def _defter(tmp_path, monkeypatch):
    monkeypatch.setenv("BASAK_STATE_DIR", str(tmp_path))
    for ad in ("DATABASE_URL", "POSTGRES_URL", "NEON_DATABASE_URL",
               "VERCEL", "BASAK_URETIM", "BASAK_PREVIEW_DATABASE_URL"):
        monkeypatch.delenv(ad, raising=False)
    kd.sifirla()
    yield
    kd.sifirla()


def _tool(ad):
    return {
        "type": "function",
        "function": {
            "name": ad,
            "description": "test araci",
            "parameters": {"type": "object", "properties": {}},
        },
    }


def _cagri(cid, ad="list_tasks", args="{}"):
    return {
        "id": cid,
        "type": "function",
        "function": {"name": ad, "arguments": args},
    }


class _Js:
    def __init__(self):
        self.olaylar = []

    def __call__(self, kod):
        self.olaylar.append(("js", kod))

    def olay(self, tur, **veri):
        self.olaylar.append((tur, veri))


class _Beyin:
    """Tek tur arac cagrisi isteyen, sonra final cevap veren sahte beyin."""

    def __init__(self, cevap="bitti"):
        self.cevap = cevap
        self.gorulen = []

    def bulut_musait(self):
        return True

    def ajan_musait(self):
        return True

    def cevapla(self, mesajlar, model, tools=None, **kwargs):
        self.gorulen.append(list(mesajlar))
        if not any(m.get("role") == "tool" for m in mesajlar):
            return {"tool_calls": [_cagri("c1")]}, "groq"
        return {"content": self.cevap}, "groq"


def test_arac_dongusu_adimlari_deftere_yazar():
    from chat.tools import arac_dongusu

    kosu = kd.ac("casper", "gorevleri kontrol et")
    kosan = []

    def calistir(ad, args):
        kosan.append(ad)
        return {"result": "3 gorev var"}

    cevap, adet = arac_dongusu(
        [_cagri("c1")],
        [{"role": "user", "content": "gorevleri kontrol et"}],
        _Beyin(), None, _Js(), calistir,
        tools=[_tool("list_tasks")], tool_choice="auto", kosu=kosu,
    )

    assert cevap == "bitti"
    assert kosan == ["list_tasks"]
    ozet = kosu.ozet()
    assert ozet["adim"] == 1
    assert ozet["araclar"] == ["list_tasks"]
    assert "3 gorev var" in (kosu.adim_onceki("c1") or {}).get("sonuc", "")


def test_devamda_kapanmis_cagri_yeniden_calistirilmaz():
    from chat.tools import arac_dongusu

    kosu = kd.ac("casper", "sayfada tikla")
    kosu.adim_basla("list_tasks", "c1", {}, tur=1)
    kosu.adim_bitti("list_tasks", "c1", "ONCEKI SONUC", True)
    kosu.duraklat()

    kosan = []

    def calistir(ad, args):
        kosan.append(ad)
        return {"result": "YENI SONUC"}

    js = _Js()
    cevap, _ = arac_dongusu(
        [_cagri("c1")],
        [{"role": "user", "content": "devam"}],
        _Beyin(), None, js, calistir,
        tools=[_tool("list_tasks")], tool_choice="auto", kosu=kosu,
    )

    assert cevap == "bitti"
    assert kosan == [], "kapanmis cagri ikinci kez CALISTIRILMAMALI"
    assert any(tur == "toolReplay" for tur, _ in js.olaylar)


def test_devam_paketi_modele_onceki_sonuclari_geri_verir():
    from chat.flow import _yonlendirme_mesajlari

    kosu = kd.ac("casper", "fiyat karsilastir")
    kosu.adim_basla("web_search", "c1", {"q": "kahve"}, tur=1)
    kosu.adim_bitti("web_search", "c1", "KAHVE FIYATI 100 TL", True)
    kosu.duraklat()

    mesajlar = _yonlendirme_mesajlari(kosu.kayitli_devam(), [])
    assert mesajlar[0] == {"role": "user", "content": "fiyat karsilastir"}
    asistan = [m for m in mesajlar if m.get("role") == "assistant"]
    assert asistan and asistan[0]["tool_calls"][0]["id"] == "c1"
    araclar = [m for m in mesajlar if m.get("role") == "tool"]
    assert araclar and araclar[0]["content"] == "KAHVE FIYATI 100 TL"


def test_mesaj_isle_kosu_id_ile_defterden_devam_eder():
    from chat.flow import mesaj_isle

    kosu = kd.ac("casper", "fiyat karsilastir")
    kosu.adim_basla("web_search", "c1", {"q": "kahve"}, tur=1)
    kosu.adim_bitti("web_search", "c1", "KAHVE FIYATI 100 TL", True)
    kosu.duraklat()

    beyin = _Beyin(cevap="karsilastirdim")
    js = _Js()
    mesaj_isle(
        "devam", beyin, "SISTEM", js, [_tool("web_search")],
        kosu_id=kosu.id,
    )

    assert beyin.gorulen, "model cagrilmadi"
    tum = beyin.gorulen[-1]
    assert any(
        m.get("role") == "tool" and "KAHVE FIYATI 100 TL" in str(m.get("content"))
        for m in tum
    ), "defterdeki arac sonucu modele geri verilmedi"
    assert any(
        m.get("role") == "user" and m.get("content") == "fiyat karsilastir"
        for m in tum
    ), "onceki istek metni modele geri verilmedi"
    son = kd.yukle(kosu.id, "casper")
    assert son.durum == "completed"
    assert son.ozet()["cevap"] == "karsilastirdim"


def test_bilinmeyen_kosu_id_acik_hata_verir():
    from chat.flow import mesaj_isle

    js = _Js()
    mesaj_isle("devam", _Beyin(), "SISTEM", js, [_tool("web_search")],
               kosu_id="olmayan-kosu")
    assert any(
        "bulunamadi" in str(kod) for tur, kod in js.olaylar if tur == "js"
    )


def test_kosu_baska_kullaniciya_devam_etmez(monkeypatch):
    from chat import flow

    kosu = kd.ac("casper", "ozel")
    kosu.duraklat()
    monkeypatch.setattr(flow, "aktif_kullanici", lambda: "baska")
    js = _Js()
    flow.mesaj_isle("devam", _Beyin(), "SISTEM", js,
                    [_tool("web_search")], kosu_id=kosu.id)
    assert any(
        "bulunamadi" in str(kod) for tur, kod in js.olaylar if tur == "js"
    )
