from chat.flow import mesaj_isle


class _SahteBeyin:
    def __init__(self):
        self.mesajlar = None

    def bulut_musait(self):
        return True

    def ajan_musait(self):
        return True

    def cevapla(self, mesajlar, _model=None, tools=None, tool_choice=None, **_kwargs):
        self.mesajlar = list(mesajlar)
        return {"content": "tamam"}, "sahte"


def test_serverless_gecmis_ayni_cekirdek_akisina_girer():
    beyin = _SahteBeyin()
    olaylar = []
    mesaj_isle(
        "yeni soru",
        beyin,
        "sistem",
        olaylar.append,
        tools=[{"type": "function", "function": {"name": "x"}}],
        misafir=True,
        gecmis_override=[
            {"role": "user", "content": "onceki soru"},
            {"role": "assistant", "content": "onceki cevap"},
        ],
    )
    icerikler = [m.get("content") for m in beyin.mesajlar]
    assert "onceki soru" in icerikler
    assert "onceki cevap" in icerikler
    assert any(o.startswith("BasakUI.bitir(") for o in olaylar)


def test_vercel_koprusu_ikinci_beyin_degildir():
    metin = open("app.py", encoding="utf-8").read()
    assert "from chat.flow import mesaj_isle" in metin
    assert "from openai import" not in metin
    assert "chat.completions" not in metin


def test_vercel_yazma_alani_tmp_olur():
    metin = open("app.py", encoding="utf-8").read()
    assert "BASAK_STATE_DIR" in metin
    assert "tempfile.gettempdir()" in metin
