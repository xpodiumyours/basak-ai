# -*- coding: utf-8 -*-
"""test_calisma_sayaclari.py — Yol A-1 canlı sayaçlar (2026-10-04).

Manus tarzi "kac komut calistirildi / kac sayfa gezildi" sayaclari iki
gercek veriye dayanir, kod tahmin yurutmez:

- `toolDone` olayindaki `arac` alani -> komut sayaci (chat/tools.py);
  `yetenek_ac` toolDone yayinlamadigi icin sayaci sismez.
- `source` olayi -> gezilen sayfa sayaci (web/app.js `kaynakEkle`).

Sure sayaci zaten vardi (`work-time` + `zamanlayici`); bu dosya sayac ve
`arac` alaninin yolda oldugunu kilitler.
"""

import pathlib

KOK = pathlib.Path(__file__).resolve().parents[1]
JAVASCRIPT = (KOK / "web" / "app.js").read_text(encoding="utf-8")
CSS = (KOK / "web" / "chat.css").read_text(encoding="utf-8")


class _Toplayici:
    """Gerçek akıştaki web taşıyıcısı: olayları toplar."""

    def __init__(self):
        self.olaylar = []
        self.kodlar = []

    def __call__(self, kod):
        self.kodlar.append(kod)

    def olay(self, tur, **veri):
        self.olaylar.append(dict(veri, tur=tur))

    def turleri(self):
        return [o["tur"] for o in self.olaylar]


LIST_TASKS = {
    "type": "function",
    "function": {"name": "list_tasks", "parameters": {"type": "object"}},
}


def _call(ad, args="{}", cid="c1"):
    return {"id": cid, "type": "function",
            "function": {"name": ad, "arguments": args}}


def _dongu(cagri, calistir_stub, katalog=None, tools=None):
    from chat.tools import arac_dongusu

    class Beyin:
        def cevapla_yayin(self, *a, **k):
            from brain.yayin import SonHata
            raise SonHata("testte stream yok")
            yield

        def cevapla(self, mesajlar, model, tools=None, tool_choice=None,
                    tercih=None):
            return ({"content": "Tamamdır."}, "nvidia")

    toplayici = _Toplayici()
    arac_dongusu(
        [cagri],
        [{"role": "user", "content": "görevleri listele"}],
        Beyin(), None, toplayici,
        calistir_stub,
        tools=[LIST_TASKS] if tools is None else tools,
        tool_choice="auto", tercih=["nvidia"],
        katalog=katalog,
    )
    return toplayici


class TestToolDoneAracAlani:
    """toolDone olayı hangi gerçek aracın çalıştığını taşır."""

    def test_tool_done_arac_alani_tasiyor(self):
        t = _dongu(_call("list_tasks"), lambda ad, args: {"result": "[]"})
        done = [o for o in t.olaylar if o["tur"] == "toolDone"]
        assert done, t.turleri()
        assert done[0]["arac"] == "list_tasks"
        assert done[0]["ok"] is True

    def test_basarisiz_aracta_da_arac_alani_var(self):
        t = _dongu(_call("list_tasks"),
                   lambda ad, args: {"error": "görev dosyası yok"})
        done = [o for o in t.olaylar if o["tur"] == "toolDone"]
        assert done and done[0]["arac"] == "list_tasks"
        assert done[0]["ok"] is False

    def test_yetenek_ac_tool_done_yayinlamaz(self):
        """Alan açmak komut sayılmaz; sayaç yalnız gerçek araçları sayar."""
        from chat.agent_protocol import baslangic_araclari
        t = _dongu(_call("yetenek_ac", '{"alanlar": ["gorevler"]}'),
                   lambda ad, args: {"result": "x"},
                   katalog=[LIST_TASKS], tools=baslangic_araclari())
        assert "toolDone" not in t.turleri(), t.turleri()
        assert any(o["tur"] == "toolStatus" for o in t.olaylar) or \
            any("toolStatus" in k for k in t.kodlar)


class TestWebSayaclari:
    """Web yüzeyi sayaçları gerçek olaylardan besler."""

    def test_sayac_yardimcisi_var(self):
        assert "function sayaclariYaz(kayit)" in JAVASCRIPT
        assert 'sayac.className = "work-counts";' in JAVASCRIPT

    def test_komut_sayaci_tool_done_artirir(self):
        assert "aktifAdimiTamamla(kayit, olay?.ok !== false, olay?.arac);" \
            in JAVASCRIPT
        assert "kayit.komutSayisi += 1;" in JAVASCRIPT
        assert "komutSayisi: 0, sayfaSayisi: 0," in JAVASCRIPT

    def test_sayfa_sayaci_kaynak_eklemede_artar(self):
        # source olayı = gerçekten gezilen/okunan sayfa; URL dedup sonrası.
        assert "kayit.sayfaSayisi += 1;" in JAVASCRIPT
        i = JAVASCRIPT.index("function kaynakEkle")
        govde = JAVASCRIPT[i:i + 1200]
        assert govde.index("kaynaklar.push") < govde.index("sayfaSayisi += 1")

    def test_adim_detayinda_arac_adi_gorunur(self):
        assert "adim.arac" in JAVASCRIPT
        assert "function aktifAdimiTamamla(kayit, ok = true, arac = \"\")" \
            in JAVASCRIPT

    def test_sayac_css_kilitleri(self):
        assert ".work-counts{" in CSS
        assert ".work-counts:not([hidden]){display:inline}" in CSS
        # Gizliyken ayraç noktası da görünmez.
        assert ".work-counts::before" in CSS

    def test_sayac_basliga_yerlestirildi(self):
        assert "ust.append(nokta, baslik, sayac, sure);" in JAVASCRIPT
