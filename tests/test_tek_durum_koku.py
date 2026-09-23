"""tests/test_tek_durum_koku.py — Tek durum kökü (P1a).

Ölçüm (2026-09-23): Başak'ın verisi iki dünyaya bölünmüştü. Bir grup
`BASAK_STATE_DIR` / `state_kok()` dinliyordu; şu sekiz yer ise doğrudan
depo klasörüne yazıyordu:

  tools/gorsel.py       -> BASE/data/uretilen
  tools/katalog.py      -> BASE/data/gelen, BASE/data/katalog,
                           BASE/data/yetki
  tools/matris.py       -> BASE/data/matris
  tools/saglik.py       -> BASE/data/audit/audit.log
  tools/__init__.py     -> BASE/gorevler.json
  brain/adapters/*      -> BASE/data/veri-kartlari/*.md

Vercel'de bu grup hiç çalışmıyordu: `vercel.json` `excludeFiles` ile
`data/**` pakete alınmıyor ve dağıtım klasörü yazılabilir değil.
Ayrıca `tools/saglik.py` denetim kaydını BASE/data'dan OKUYOR,
`brain/brain.py` durum kökü altına YAZIYORDU — sağlık raporu gerçek
kaydı hiç görmüyordu.

Bu dosya düzeltmeyi çiviler: (1) kök tanımsızken bugünkü yer,
(2) kök verilince sekizinin hepsi taşınır, (3) denetim kaydı tek yer,
(4) yollar modül yüklenirken sabitlenmez, (5) görev listesi çalışır.
"""

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import brain.brain as bb  # noqa: E402
import brain.adapters.deepseek_adapter as deepseek_ad  # noqa: E402
import brain.adapters.kimi_adapter as kimi_ad  # noqa: E402
import chat.kimlik as kimlik  # noqa: E402
import tools as tools_paket  # noqa: E402
from tools import gorsel, katalog, matris, saglik  # noqa: E402


def _sekiz_yol():
    """Sekiz yerin O ANKI yolu — hepsi gerçek fonksiyonlardan."""
    return {
        "uretilen": gorsel.uretilen_kok(),
        "gelen": katalog.gelen_kok(),
        "katalog": katalog.katalog_kok(),
        "yetki": katalog.yetki_kok(),
        "matris": matris.matris_kok(),
        "audit": saglik.audit_dosyasi(),
        "gorevler": tools_paket.gorevler_dosyasi(),
        "deepseek_kart": deepseek_ad.kart_yolu(),
        "kimi_kart": kimi_ad.kart_yolu(),
    }


# ── 1. Kök tanımsızken bugünkü davranış ───────────────────────────────

class TestVarsayilanKok:
    def test_kok_tanimsizken_yollar_base_data_altinda(self, monkeypatch,
                                                      tmp_path):
        """BASAK_STATE_DIR yoksa her yol <proje>/data/... (bugünkü yer)."""
        monkeypatch.delenv("BASAK_STATE_DIR", raising=False)
        proje = tmp_path / "proje"
        monkeypatch.setattr(kimlik, "BASE", str(proje))
        veri = str(proje / "data")

        assert kimlik.state_kok() == veri

        yollar = _sekiz_yol()
        assert yollar["uretilen"] == os.path.join(veri, "uretilen")
        assert yollar["gelen"] == os.path.join(veri, "gelen")
        assert yollar["katalog"] == os.path.join(veri, "katalog")
        assert yollar["yetki"] == os.path.join(veri, "yetki")
        assert yollar["matris"] == os.path.join(veri, "matris")
        assert yollar["audit"] == os.path.join(veri, "audit", "audit.log")
        assert yollar["gorevler"] == os.path.join(veri, "gorevler.json")
        assert yollar["deepseek_kart"] == os.path.join(
            veri, "veri-kartlari", "deepseek.md")
        assert yollar["kimi_kart"] == os.path.join(
            veri, "veri-kartlari", "kimi.md")

    def test_veri_karti_denetimi_klasor_acmaz(self, monkeypatch, tmp_path):
        """Salt-okuma denetimi (adapter) klasör açmaz — yan etki yok."""
        monkeypatch.delenv("BASAK_STATE_DIR", raising=False)
        proje = tmp_path / "proje"
        monkeypatch.setattr(kimlik, "BASE", str(proje))
        deepseek_ad.kart_yolu()
        kimi_ad.kart_yolu()
        assert not os.path.exists(proje / "data" / "veri-kartlari")


# ── 2. Kök verilince sekizinin hepsi taşınır ──────────────────────────

class TestKokDegisince:
    def test_sekiz_yol_da_yeni_kokun_altina_kayar(self, monkeypatch,
                                                 tmp_path):
        kok = tmp_path / "durum"
        monkeypatch.setenv("BASAK_STATE_DIR", str(kok))

        beklenen = {
            "uretilen": os.path.join(str(kok), "uretilen"),
            "gelen": os.path.join(str(kok), "gelen"),
            "katalog": os.path.join(str(kok), "katalog"),
            "yetki": os.path.join(str(kok), "yetki"),
            "matris": os.path.join(str(kok), "matris"),
            "audit": os.path.join(str(kok), "audit", "audit.log"),
            "gorevler": os.path.join(str(kok), "gorevler.json"),
            "deepseek_kart": os.path.join(str(kok), "veri-kartlari",
                                          "deepseek.md"),
            "kimi_kart": os.path.join(str(kok), "veri-kartlari",
                                      "kimi.md"),
        }
        assert _sekiz_yol() == beklenen

    def test_depo_klasorune_hicbir_sey_yazilmaz(self, monkeypatch, tmp_path):
        """Kök verildiğinde yollar depo klasörünü HİÇ göstermez.

        Vercel'de depo klasörü yazılabilir değil ve data/** pakete bile
        girmiyor; tek bir yol depoda kalırsa o araç canlıda patlar.
        """
        kok = tmp_path / "durum"
        monkeypatch.setenv("BASAK_STATE_DIR", str(kok))
        depo = os.path.abspath(kimlik.BASE)
        for ad, yol in _sekiz_yol().items():
            assert not os.path.abspath(yol).startswith(depo), ad

    def test_gorsel_uretilen_klasoru_yeni_kokte_acilir(self, monkeypatch,
                                                      tmp_path):
        kok = tmp_path / "durum"
        monkeypatch.setenv("BASAK_STATE_DIR", str(kok))
        assert os.path.isdir(gorsel.uretilen_kok())


# ── 3. Denetim kaydı: yazan ile okuyan aynı yer ────────────────────────

class TestDenetimKaydi:
    def test_yazan_ile_okuyan_ayni_dosya(self, monkeypatch):
        """brain/brain.py'nin yazdığı dosya = tools/saglik.py'nin okuduğu.

        brain.brain.AUDIT_DOSYASI'yı conftest geçici dosyaya yamıyor
        (gerçek ölçüm korunuyor), bu yüzden karşılaştırma yamanmayan
        kökten yapılır: bb.STATE_DIR + audit/audit.log.
        """
        monkeypatch.delenv("BASAK_STATE_DIR", raising=False)
        yazan = os.path.join(bb.STATE_DIR, "audit", "audit.log")
        okuyan = saglik.audit_dosyasi()
        assert os.path.abspath(okuyan) == os.path.abspath(yazan)

    def test_saglik_raporu_gercek_kaydi_gorur(self, monkeypatch, tmp_path):
        """Kök taşınınca sağlık raporu o köke yazılan hataları sayar."""
        kok = tmp_path / "durum"
        monkeypatch.setenv("BASAK_STATE_DIR", str(kok))
        yol = saglik.audit_dosyasi()
        os.makedirs(os.path.dirname(yol), exist_ok=True)
        with open(yol, "w", encoding="utf-8") as f:
            f.write("2026-09-23 HATA 429 rate limit\n")
            f.write("2026-09-23 HATA timed out\n")
        assert saglik._hata_ozeti(saglik.audit_dosyasi()) == {
            "kota-doldu": 1, "zaman-asimi": 1}


# ── 4. Yollar modül yüklenirken sabitlenmez ───────────────────────────

class TestSabitlenmez:
    def test_kok_degisince_yollar_da_degisir(self, monkeypatch, tmp_path):
        """Modül zaten yüklü; kök değişince yol ANINDA yeni köke uyar."""
        bir = tmp_path / "bir"
        iki = tmp_path / "iki"

        monkeypatch.setenv("BASAK_STATE_DIR", str(bir))
        birinci = _sekiz_yol()

        monkeypatch.setenv("BASAK_STATE_DIR", str(iki))
        ikinci = _sekiz_yol()

        for ad in birinci:
            assert birinci[ad] != ikinci[ad], ad
            assert os.path.abspath(birinci[ad]).startswith(
                os.path.abspath(str(bir))), ad
            assert os.path.abspath(ikinci[ad]).startswith(
                os.path.abspath(str(iki))), ad


# ── 5. Görev listesi yeni kökte çalışır ───────────────────────────────

class TestGorevListesi:
    def test_ekle_listele_tamamla_yeni_kokte_kosar(self, monkeypatch,
                                                  tmp_path):
        kok = tmp_path / "durum"
        monkeypatch.setenv("BASAK_STATE_DIR", str(kok))

        eklendi = tools_paket.calistir("add_task", {"text": "sut al"})
        assert "error" not in eklendi, eklendi

        dosya = tools_paket.gorevler_dosyasi()
        assert os.path.isfile(dosya)
        assert os.path.abspath(dosya) == os.path.abspath(
            str(kok / "gorevler.json"))

        with open(dosya, "r", encoding="utf-8-sig") as f:
            kayit = json.load(f)
        assert kayit[0]["text"] == "sut al"
        gorev_no = kayit[0]["id"]

        listelendi = tools_paket.calistir("list_tasks", {})
        assert "error" not in listelendi, listelendi
        assert "sut al" in json.dumps(listelendi, ensure_ascii=False)

        bitti = tools_paket.calistir("complete_task",
                                     {"task_id": gorev_no})
        assert "error" not in bitti, bitti
        with open(dosya, "r", encoding="utf-8-sig") as f:
            kayit = json.load(f)
        assert kayit[0].get("done") or kayit[0].get("completed")

    def test_gorev_dosyasi_depo_kokune_yazilmaz(self, monkeypatch, tmp_path):
        """Eski yer BASE/gorevler.json idi; dağıtımda yazılamıyordu."""
        kok = tmp_path / "durum"
        monkeypatch.setenv("BASAK_STATE_DIR", str(kok))
        # Gercek depo dosyasina BAKILMAZ: testin kumu disindaki bir
        # dosyanin varligi/yoklugu uzerinden hukum vermek, test paketini
        # gercek veriye bagimli kilar (2026-09-23'te tam bu yuzden gercek
        # gorev dosyasi tasinip kayboldu). Olculen sey: cagri depo kokunde
        # yeni bir dosya YARATMIYOR / var olani DEGISTIRMIYOR.
        kok_dosya = os.path.join(kimlik.BASE, "gorevler.json")
        onceki = (os.path.exists(kok_dosya),
                  os.path.getmtime(kok_dosya)
                  if os.path.exists(kok_dosya) else None)

        tools_paket.calistir("add_task", {"text": "deneme"})

        sonraki = (os.path.exists(kok_dosya),
                   os.path.getmtime(kok_dosya)
                   if os.path.exists(kok_dosya) else None)
        assert onceki == sonraki, "depo kokundeki dosya degisti"
        assert (kok / "gorevler.json").exists(), "gorev yeni koke yazilmadi"
