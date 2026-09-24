"""P2 runtime tool resolver — kotasiz birim testleri."""

from chat.tool_resolver import araclari_coz


def _tool(ad, aciklama="ornek arac", props=None):
    return {
        "type": "function",
        "function": {
            "name": ad,
            "description": aciklama,
            "parameters": {
                "type": "object",
                "properties": props or {},
            },
        },
    }


def test_resolver_farkli_turlerden_gercek_araclari_birlikte_secer():
    katalog = [
        _tool("web_search", "Internette arama yapar"),
        _tool("read_file", "Dosya okur"),
        _tool("github_durum", "GitHub durumunu okur"),
        _tool("hesapla", "Matematik hesabi yapar"),
    ]

    class Beyin:
        def cevapla(self, mesajlar, model, **kwargs):
            return {
                "content": (
                    '{"tools":["web_search","read_file","github_durum"]}'
                )
            }, "groq"

    secilen = araclari_coz(
        Beyin(), None,
        [{"role": "user",
          "content": "Internetten arastir, dosyayla karsilastir, GitHub'a bak"}],
        katalog,
    )
    assert [x["function"]["name"] for x in secilen] == [
        "web_search", "read_file", "github_durum"
    ]


def test_resolver_meta_arac_uretmez_ve_katalog_disi_adi_calistirmaz():
    katalog = [_tool("web_search"), _tool("read_file")]

    class Beyin:
        def cevapla(self, mesajlar, model, **kwargs):
            return {
                "content": '{"tools":["yetenek_ac","arac_ara","web_search"]}'
            }, "groq"

    secilen = araclari_coz(
        Beyin(), None,
        [{"role": "user", "content": "arastir"}],
        katalog,
    )
    assert [x["function"]["name"] for x in secilen] == ["web_search"]


def test_resolver_gecerli_bos_listeyle_normal_sohbette_arac_acmaz():
    katalog = [_tool("web_search")]

    class Beyin:
        def cevapla(self, mesajlar, model, **kwargs):
            return {"content": '{"tools":[]}'}, "groq"

    assert araclari_coz(
        Beyin(), None,
        [{"role": "user", "content": "merhaba"}],
        katalog,
    ) == []


def test_resolver_bozulursa_yetenek_kaybi_yaratmaz_tam_katalogu_korur():
    katalog = [_tool("web_search"), _tool("read_file")]

    class Beyin:
        def cevapla(self, mesajlar, model, **kwargs):
            return {"content": "json degil"}, "groq"

    secilen = araclari_coz(
        Beyin(), None,
        [{"role": "user", "content": "arastir"}],
        katalog,
    )
    assert [x["function"]["name"] for x in secilen] == [
        "web_search", "read_file"
    ]


def test_resolver_arac_sonucunu_sonraki_secimde_gorur():
    katalog = [_tool("web_search"), _tool("read_file")]
    gorulen = {}

    class Beyin:
        def cevapla(self, mesajlar, model, **kwargs):
            gorulen["prompt"] = mesajlar[-1]["content"]
            return {"content": '{"tools":["read_file"]}'}, "groq"

    secilen = araclari_coz(
        Beyin(), None,
        [
            {"role": "user", "content": "once webde ara sonra dosyayi kontrol et"},
            {"role": "tool", "name": "web_search",
             "content": "Bulgu: resmi sayfa bulundu"},
        ],
        katalog,
    )
    assert "tool=web_search" in gorulen["prompt"]
    assert "resmi sayfa bulundu" in gorulen["prompt"]
    assert [x["function"]["name"] for x in secilen] == ["read_file"]
