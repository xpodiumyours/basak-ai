"""Faz 1: ana yol kişisel bağlamı ve küçük-model yükünü kaybetmemeli."""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def _schema(ad):
    return {
        "type": "function",
        "function": {
            "name": ad,
            "description": "",
            "parameters": {"type": "object", "properties": {}},
        },
    }


def test_kisisel_hazirlik_profili_ogrenir_ve_gecmisi_korur(tmp_path):
    from memory import HafizaMotoru
    from chat.personal import prepare_personal_turn

    motor = HafizaMotoru(
        db_yolu=str(tmp_path / "kisisel.db"), embed_fn=lambda _m: None)
    try:
        gecmis = [
            {"role": "user", "content": "Önceki sorum"},
            {"role": "assistant", "content": "Önceki cevabım"},
        ]
        hazir = prepare_personal_turn(
            "Ben çayı seviyorum", motor=motor, history=gecmis)

        assert "çayı seviyor" in hazir.profile_block
        assert hazir.recent_history == gecmis
        assert "profile yeni bilgi eklendi" in hazir.learning_note
    finally:
        motor.kapat()


def test_kisisel_bilgi_kapanip_acildiktan_sonra_modele_hazirlanir(tmp_path):
    from memory import HafizaMotoru
    from chat.personal import prepare_personal_turn

    db = str(tmp_path / "kalici.db")
    ilk = HafizaMotoru(db_yolu=db, embed_fn=lambda _m: None)
    prepare_personal_turn("Ben çayı seviyorum", motor=ilk, history=[])
    ilk.kapat()

    yeniden = HafizaMotoru(db_yolu=db, embed_fn=lambda _m: None)
    try:
        hazir = prepare_personal_turn(
            "Çay hakkında ne biliyorsun?", motor=yeniden, history=[])
        assert "çayı seviyor" in hazir.profile_block
        assert hazir.learning_note == ""
    finally:
        yeniden.kapat()


def test_orkestra_profili_ve_yakin_gecmisi_modele_tasir(
        monkeypatch, tmp_path):
    import _chat_legacy as legacy
    from chat.personal import PreparedPersonalTurn

    history_file = tmp_path / "gecmis.json"
    monkeypatch.setattr(legacy, "HISTORY_FILE", str(history_file))
    monkeypatch.setattr(legacy, "SETTINGS_FILE", str(tmp_path / "ayar.json"))
    monkeypatch.setattr(legacy, "_hafiza_al", lambda: None)
    monkeypatch.setattr(legacy, "juri_acik_mi", lambda: False)
    monkeypatch.setattr(legacy, "_juri_onayi", lambda: (lambda: False))

    yakalanan = {}

    class Brain:
        def yerel_modeller(self):
            return ["qwen2.5:3b"]

        def _bulut_zinciri(self):
            return []

        def cevapla(self, messages, yerel_model, tools=None, **_kw):
            yakalanan["messages"] = messages
            yakalanan["tools"] = tools
            return {"content": "Seni hatırlıyorum."}, "yerel"

    hazir = PreparedPersonalTurn(
        text="Devam edelim",
        speaker="",
        profile_block="Casper hakkında KALICI bilinenler:\n- Çayı şekersiz içer.",
        learning_note="",
        recent_history=[
            {"role": "user", "content": "Çayı şekersiz içerim."},
            {"role": "assistant", "content": "Bunu hatırlayacağım."},
        ],
    )

    cevaplar = []
    legacy.mesaj_isle_orkestra(
        "Devam edelim", Brain(), "KİMLİK", lambda c: cevaplar.append(c),
        [_schema("web_search"), _schema("list_files")],
        kaydet_acik=True, personal_turn=hazir)

    icerikler = [m.get("content", "") for m in yakalanan["messages"]]
    assert any("Çayı şekersiz" in m for m in icerikler)
    assert any(m == "Çayı şekersiz içerim." for m in icerikler)
    assert any(m == "Bunu hatırlayacağım." for m in icerikler)
    assert any(c.startswith("BasakUI.reply") for c in cevaplar)


def test_kucuk_model_selamlasmada_arac_gormez():
    from chat.tool_selection import select_tools

    tools = [_schema("web_search"), _schema("list_files"),
             _schema("read_file"), _schema("add_task")]
    assert select_tools("merhaba nasılsın", tools, small_model=True) == []


def test_kucuk_model_dosya_sorusunda_yalniz_liste_aracini_gorur():
    from chat.tool_selection import select_tools

    tools = [_schema("web_search"), _schema("list_files"),
             _schema("read_file"), _schema("add_task")]
    secilen = select_tools(
        "Masaüstümde hangi dosyalar var?", tools, small_model=True)
    assert [t["function"]["name"] for t in secilen] == ["list_files"]


def test_kimlik_tek_basak_olarak_tanimli():
    from chat.prompts import KIMLIK_BLOGU

    assert "Sen Başak'sın" in KIMLIK_BLOGU
    assert "Edercanım" not in KIMLIK_BLOGU


def test_sesli_cumle_normal_mesaj_gonderimine_hazirlanir(monkeypatch):
    import basak_app

    class SahteSTT:
        def dinle_and_id(self):
            return "Ben çayı seviyorum", None, 16000

    api = basak_app.Api.__new__(basak_app.Api)
    api.stt = SahteSTT()
    giden = []
    api._js = lambda kod: giden.append(kod)

    api._dinle()

    assert any(kod.startswith("BasakUI.sttResult(") and
               "Ben çayı seviyorum" in kod for kod in giden)


def test_sesli_sonuc_ekranda_normal_gonderme_kapisina_gider():
    kok = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    uygulama = open(os.path.join(kok, "ui", "app.js"),
                    encoding="utf-8").read()
    bas = uygulama.index("sttResult(text, speaker)")
    son = uygulama.index("ses(seviye)", bas)
    assert "send();" in uygulama[bas:son]


def test_kimlik_sorusu_modelden_bagimsiz_dogru_cevaplanir(
        monkeypatch, tmp_path):
    import chat
    import chat.flow as flow
    import _chat_legacy as legacy

    gecmis = tmp_path / "gecmis.json"
    monkeypatch.setattr(legacy, "HISTORY_FILE", str(gecmis))
    monkeypatch.setattr(legacy, "SETTINGS_FILE", str(tmp_path / "ayar.json"))
    monkeypatch.setattr(legacy, "_hafiza_al", lambda: None)
    monkeypatch.setattr(legacy, "orkestra_aktif_mi", lambda: True)
    import chat.oturum as oturum
    monkeypatch.setattr(oturum, "kaydet_cift", lambda *a, **k: None)

    class Cagrilmamali:
        def yerel_modeller(self):
            raise AssertionError("Kimlik sorusu modele gitmemeli")

    cevaplar = []
    flow.mesaj_isle_yeni(
        "Sen kimsin?", Cagrilmamali(), "KİMLİK",
        lambda kod: cevaplar.append(kod), [])

    yanitlar = [k for k in cevaplar if k.startswith("BasakUI.reply(")]
    assert len(yanitlar) == 1
    assert "Ben Başak'ım" in yanitlar[0]
    kayitlar = json.loads(gecmis.read_text(encoding="utf-8"))
    assert kayitlar[-1]["role"] == "assistant"
    assert "Ben Başak'ım" in kayitlar[-1]["content"]


def test_kimlik_korumasi_arastirma_sorusunu_yakalamaz():
    from chat.personal import deterministic_reply

    assert deterministic_reply("Başak kimdir?") == ""
    assert deterministic_reply("Sen kimsin?").startswith("Ben Başak'ım")