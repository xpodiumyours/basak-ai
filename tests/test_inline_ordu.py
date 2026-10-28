"""Aynı istek içinde paralel alt ajan (inline ordu) testleri.

Bu testler chat/inline_ordu modülünün davranışını sabitler:
- anonim/preview kimlikleri hesap kapısına takılmaz (inline=True),
- alt ajanlar salt-okunur katalogla, izole geçmişle koşar,
- paralel sınırı ve kota görünür hatayla döner,
- ana istek alt ajanları bekler, cevapları sonuç aracına düşer.
"""

import threading

import pytest


def _calistir(gorevler):
    """Bağlı inline zarf içinde alt ajan aracını çağırır."""
    from tools import calistir
    return [
        calistir("alt_ajan", {"isler": [{"gorev": g}]})
        for g in gorevler
    ]


# ── ExecutionContext inline kapısı ──────────────────────────────────

def test_inline_zarf_anonim_ve_preview_kimligini_kabul_eder():
    from chat.platform_context import ExecutionContext

    for kid in ("anon-x", "anonim-y", "p" + "a" * 16):
        ctx = ExecutionContext(kid, "inline", "run-1", inline=True)
        assert ctx.inline is True
        # Aynı kimlik kalıcı yolda hâlâ reddedilir.
        with pytest.raises(ValueError):
            ExecutionContext(kid, "ws", "run-2")
    # Anonim web kimliği her iki yolda da geçerli bir kimliktir.
    assert ExecutionContext("u1234567890123456", "ws", "run-3")


def test_inline_baglam_anonim_kimlikle_baglanir_ve_kaldirilir():
    from chat.inline_ordu import inline_baglam
    from chat.platform_context import current

    assert current() is None
    with inline_baglam("u1234567890123456", brain=object()) as ctx:
        assert current() is ctx
        assert ctx.control is not None
        assert ctx.control.inline is True
        assert ctx.control.store is ctx.control.depo
        assert ctx.user_id == "u1234567890123456"
    assert current() is None


def test_inline_kontrol_iptal_run_cancelled_dogurur():
    from chat.inline_ordu import inline_baglam
    from chat.platform_runtime import RunCancelled

    iptal = threading.Event()
    with inline_baglam("u1234567890123456", brain=object(),
                       iptal=iptal) as ctx:
        kontrol = ctx.control
        kontrol.check_cancelled()  # set edilmeden önce sorun yok
        iptal.set()
        with pytest.raises(RunCancelled):
            kontrol.check_cancelled()


# ── Yetenek sınırı ──────────────────────────────────────────────────

def test_alt_ajan_katalogu_salt_okunur_ve_alt_ajan_acamaz(monkeypatch):
    from chat.capabilities import PUBLIC_TOOLS
    from chat.inline_ordu import inline_baglam
    import chat.flow as flow

    seen = {}

    def _sahte(metin, beyin, sistem, ayikci, katalog, **kw):
        seen["adlar"] = {
            (t.get("function") or {}).get("name") for t in katalog}
        seen["gecmis"] = kw.get("gecmis_override", "YOK")
        return None  # cevap üretme: alt ajan failed sayılır, kayıp yok

    monkeypatch.setattr(flow, "mesaj_isle", _sahte)

    with inline_baglam("u1234567890123456", brain=object()) as ctx:
        kontrol = ctx.control
        sonuc = _calistir(["bir is"])[0]
        assert "error" not in sonuc  # kurulum başarılı
        kontrol.wait_for_children(list(kontrol.depo._kayitlar))

    assert seen["adlar"] <= PUBLIC_TOOLS
    assert "alt_ajan" not in seen["adlar"]
    assert "alt_ajan_sonuclari" not in seen["adlar"]
    assert seen["gecmis"] == [], "alt ajan izole geçmişle koşar"


# ── Paralel sınır + kota ────────────────────────────────────────────

def test_es_zamanli_dortten_fazla_alt_ajan_acilmaz(monkeypatch):
    from chat.inline_ordu import AZAMI_PARALEL, inline_baglam
    import chat.flow as flow

    monkeypatch.setattr(flow, "mesaj_isle", lambda *a, **kw: None)
    bit = threading.Event()

    def _yavas(*a, **kw):
        bit.wait(5)
        return None

    monkeypatch.setattr(flow, "mesaj_isle", _yavas)

    with inline_baglam("u1234567890123456", brain=object()) as ctx:
        kontrol = ctx.control
        sonuclar = _calistir(["is %d" % i for i in range(5)])
        hatalar = [s for s in sonuclar if isinstance(s, dict)
                   and s.get("error")]
        assert len(hatalar) == 1
        assert "siniri" in hatalar[0]["error"]
        assert len(kontrol.depo._kayitlar) == AZAMI_PARALEL
        bit.set()
        kontrol.wait_for_children(list(kontrol.depo._kayitlar))


def test_bitik_alt_ajanlarin_yerine_yenisi_acilir(monkeypatch):
    from chat.inline_ordu import inline_baglam
    import chat.flow as flow

    # Hemen cevap üreten (ama boş dönen) çocuk akışı.
    monkeypatch.setattr(flow, "mesaj_isle", lambda *a, **kw: None)

    with inline_baglam("u1234567890123456", brain=object()) as ctx:
        kontrol = ctx.control
        ilk = _calistir(["is %d" % i for i in range(4)])
        assert all("error" not in s for s in ilk)
        kontrol.wait_for_children(list(kontrol.depo._kayitlar))
        # Dört çocuk da bitti; aktif kalan yok → yenisi açılabilir.
        besinci = _calistir(["besinci is"])[0]
        assert "error" not in besinci
        kontrol.wait_for_children(list(kontrol.depo._kayitlar))
        assert len(kontrol.depo._kayitlar) == 5


def test_tek_cagrida_bes_is_verilirse_alan_siniri_doner():
    from chat.inline_ordu import inline_baglam
    from tools import calistir
    import chat.flow as flow

    original = flow.mesaj_isle
    flow.mesaj_isle = lambda *a, **kw: None
    try:
        with inline_baglam("u1234567890123456", brain=object()) as ctx:
            sonuc = calistir("alt_ajan", {
                "isler": [{"gorev": "is %d" % i} for i in range(5)]})
            assert "error" in sonuc
            assert "siniri" in sonuc["error"]
            assert ctx.control.depo._kayitlar == {}
    finally:
        flow.mesaj_isle = original


def test_kota_dolunca_alt_ajan_acilmaz_ve_hata_gorunur(monkeypatch):
    from chat.inline_ordu import inline_baglam
    import chat.flow as flow

    monkeypatch.setattr(flow, "mesaj_isle", lambda *a, **kw: None)

    def _kota_dolu():
        return False

    with inline_baglam("u1234567890123456", brain=object(),
                       kota_harcakci=_kota_dolu) as ctx:
        sonuc = _calistir(["ilk is"])[0]
        assert isinstance(sonuc, dict) and "error" in sonuc
        assert "kota" in sonuc["error"]
        for kayit in ctx.control.depo._kayitlar.values():
            assert kayit["durum"] in ("blocked", "queued", "failed")


def test_baska_istegin_alt_ajanini_bekleyemez():
    from chat.inline_ordu import inline_baglam

    with inline_baglam("u1234567890123456", brain=object()) as ctx:
        kontrol = ctx.control
        with pytest.raises(ValueError):
            kontrol.wait_for_children([])
        with pytest.raises(PermissionError):
            kontrol.wait_for_children(["orda-bilinmeyen"])


# ── Ana istek alt ajanları bekler, cevap döner ──────────────────────

def test_alt_ajan_cevabi_sonuc_araci_sonucu_olur(monkeypatch):
    from chat.inline_ordu import inline_baglam
    from tools import calistir
    import chat.flow as flow

    def _cevap_uret(metin, beyin, sistem, ayikci, katalog, **kw):
        # flow'daki gibi cevabı ekrana basar
        ayikci('BasakUI.bitir("Merhaba, is bitti", "groq")')
        return None

    monkeypatch.setattr(flow, "mesaj_isle", _cevap_uret)

    with inline_baglam("u1234567890123456", brain=object()) as ctx:
        kontrol = ctx.control
        kurulum = calistir("alt_ajan", {"isler": [{"gorev": "selamla"}]})
        assert "error" not in kurulum
        kid = list(kontrol.depo._kayitlar)[0]
        kontrol.wait_for_children([kid])
        assert kontrol.depo._kayitlar[kid]["durum"] == "completed"
        sonuc = calistir("alt_ajan_sonuclari", {"bekle": True})

    metin = str(sonuc)
    assert "Merhaba" in metin
    assert "bitti" in metin


def test_alt_ajan_adimlari_ana_olay_toplayicisina_tasinir(monkeypatch):
    from chat.inline_ordu import inline_baglam
    from tools import calistir
    import chat.flow as flow

    olaylar = []

    def _cevap_uret(metin, beyin, sistem, ayikci, katalog, **kw):
        ayikci._web_olay = None
        # Zengin olay + nihai cevap
        yay = getattr(ayikci, "olay", None)
        if callable(yay):
            yay("toolDone", arac="web_search", ok=True)
        ayikci('BasakUI.bitir("tamam", "groq")')
        return None

    monkeypatch.setattr(flow, "mesaj_isle", _cevap_uret)

    def _topla(tur, alt_ajan, veri):
        olaylar.append((tur, alt_ajan, veri))

    with inline_baglam("u1234567890123456", brain=object(),
                       olay_verici=_topla) as ctx:
        kontrol = ctx.control
        assert "error" not in calistir(
            "alt_ajan", {"isler": [{"gorev": "bir is"}]})
        kontrol.wait_for_children(list(kontrol.depo._kayitlar))

    assert olaylar, "alt ajan adımı ana ekrana taşınmalı"
    tur, alt_ajan, veri = olaylar[0]
    assert tur == "toolDone"
    assert alt_ajan.startswith("orda-")


def test_olay_verici_yokken_alt_ajan_kesintisiz_kosar(monkeypatch):
    from chat.inline_ordu import inline_baglam
    import chat.flow as flow

    def _cevap_uret(metin, beyin, sistem, ayikci, katalog, **kw):
        ayikci('BasakUI.bitir("sorunsuz", "groq")')
        return None

    monkeypatch.setattr(flow, "mesaj_isle", _cevap_uret)

    with inline_baglam("u1234567890123456", brain=object()) as ctx:
        kontrol = ctx.control
        from tools import calistir
        assert "error" not in calistir(
            "alt_ajan", {"isler": [{"gorev": "tek"}]})
        kontrol.wait_for_children(list(kontrol.depo._kayitlar))
        kayit = next(iter(kontrol.depo._kayitlar.values()))
        assert kayit["durum"] == "completed"
        assert kayit["cevap"] == "sorunsuz"
