"""tests/test_kabul_matrisi_tetikleyici.py — ölü CI tetikleyicisi kapanışı.

2026-10-01 ölçümü: `provider-acceptance` işi koşu listesinde her zaman
`skipped` görünüyordu. Nedeni tek satırdı:

    if: github.event_name == 'pull_request' &&
        github.head_ref == 'preview/fatura-goz-cerrahi-20260927'

O dal 2026-09-28'de silinmişti; koşul **daima** yanlış olduğu için iş
hiç koşmuyordu. Bu, P0 kanıtını (gerçek sağlayıcı kabul matrisi)
üretiyor *gibi görünen* ölü bir iş — sessizce kanıt üretmediği için
en tehlikeli tür.

Sözleşme:
- İşin tetikleyicisi vardır ve tetikleyici **ölü bir dala bağlı
  değildir** (dallar silinir; koşul kalır).
- Tetikleyici bilinçlidir: `workflow_dispatch`, PR etiketi veya
  haftalık `schedule`. Push ile otomatik değil — iş gerçek sağlayıcı
  kotası harcar; schedule haftada 1 kezle sınırlıdır (2026-10-04).
- Sırlar kurulumdan ÖNCE denetlenir; hiç sır yoksa koşum israf olmaz.
- Sır listesi TEK kaynaktan gelir (Python) ve YAML'ın env bloğuyla
  kaymaz.

Ağ yok, sır yok: yalnız tetikleyici metni ve preflight mantığı ölçülür.
"""

import pathlib
import re

from tests.live import sir_preflight

AKIS = pathlib.Path(".github/workflows/test.yml")
KOK = pathlib.Path(__file__).resolve().parents[1]


def _akis():
    return AKIS.read_text(encoding="utf-8")


def _kod(metin):
    """Yorum satirlari atilmis metin.

    Düzeltmeyi anlatan yorumda eski dal adının yazması **normal**;
    ölü dal adı hâlâ KULLANILIYOR demek değildir. Yalnız yorum
    temizlenir, kod aynen denetlenir.
    """
    return "\n".join(
        satir for satir in metin.splitlines()
        if not satir.lstrip().startswith("#"))


def _provider_acceptance_kismi():
    """`provider-acceptance:` işinden sonraki metin.

    YAML'a harici bağımlılık eklememek için ayrım metinle yapılır;
    dosyada bu isten başka `if:` blokları var.
    """
    metin = _akis()
    bas = metin.index("  provider-acceptance:")
    return metin[bas:]


class TestOluTetikleyiciKapandi:
    def test_silinmis_dal_adi_artik_yok(self):
        """Koşul, silinmiş bir dala bagli olmaya devam edemez."""
        assert "preview/fatura-goz-cerrahi-20260927" not in _kod(_akis()), (
            "olu dal adi hala kosulda — isi tetiklemez")

    def test_head_ref_kosulu_kalmadi(self):
        """Dal adiyla eslesen kosulun kalinti bicimi de yok."""
        assert "head_ref ==" not in _kod(_provider_acceptance_kismi()), (
            "head_ref kosulu kaldi: is yine bir dala bagli")

    def test_elle_tetikleyici_var(self):
        kismi = _provider_acceptance_kismi()
        assert "github.event_name == 'workflow_dispatch'" in kismi, (
            "workflow_dispatch yolu yok — isi tetikleyecek kimse kalmadi")

    def test_etiket_yolu_var(self):
        kismi = _provider_acceptance_kismi()
        assert "kabul-matrisi" in kismi, "PR etiketi yolu yok"
        assert "contains(github.event.pull_request.labels" in kismi, (
            "etiket kosulu gercek bir etiket okumuyor")

    def test_schedule_tetikleyici_on_blokunda(self):
        """`on:` blogunda haftalik schedule tetikleyicisi kayitli.

        2026-10-04: kabul matrisi artik haftada 1 kez kaste kosar;
        kanit hiyarsi bilincli kabul edilmistir.
        """
        akis = _kod(_akis())
        assert "\n  schedule:" in akis, "on: blogunda schedule yok"
        assert "- cron: '0 4 * * 1'" in akis, (
            "haftalik Pzt 04:00 UTC cron'u yok — kota/dakika hesabı "
            "bozulur")

    def test_schedule_kosulu_if_blokunde(self):
        """`if:` kosuluna schedule dali eklenmis VE eskiler korunmus."""
        kismi = _provider_acceptance_kismi()
        kosul = kismi.split("needs:")[0]
        assert "github.event_name == 'schedule'" in kosul, (
            "schedule dali if: kosulunda yok — is yine kosmaz")
        # Mevcut yollar bozulmamali:
        assert "github.event_name == 'workflow_dispatch'" in kosul
        assert "contains(github.event.pull_request.labels" in kosul

    def test_schedule_push_kadar_otomatik_degil(self):
        """Schedule bilincli aralikladir; push gibi her olayda kosmaz.

        `if:` kosulunda yalnizca workflow_dispatch / schedule / etiket
        gecebilir; baska olay dali (push, pull_request without label)
        is otomatik kosturmaz.
        """
        kismi = _provider_acceptance_kismi()
        kosul = kismi.split("needs:")[0]
        olaylar = set(re.findall(r"github\.event_name == '(\w+)'", kosul))
        assert olaylar <= {"workflow_dispatch", "schedule",
                           "pull_request"}, olaylar

    def test_push_ile_otomatik_kosmaz(self):
        """Her merge'de otomatik kosmamali: kota + dakika israfi.

        P0 kaniti kaste uretilir. Otomatik tetikleme geri gelirse
        (ornegin `github.event_name == 'push'`) test kirmizi doner.
        """
        kismi = _provider_acceptance_kismi()
        kosul = kismi.split("needs:")[0]
        assert "github.event_name == 'push'" not in kosul, kosul

    def test_is_hala_pytest_kapisinin_arkasinda(self):
        """Kabul matrisi kotasiz kosudan sonra gelir."""
        assert "needs: pytest" in _provider_acceptance_kismi()


class TestSirlarKaymaz:
    def test_her_gereken_sir_env_blokunda_gecer(self):
        akis = _kod(_akis())
        eksik = [
            ad for ad in sir_preflight.GEREKEN_SIRLER
            if "%s: ${{ secrets.%s }}" % (ad, ad) not in akis
        ]
        assert not eksik, (
            "preflight bu sirlari ariyor ama YAML onlari geçmiyor: %s"
            % eksik)

    def test_gereken_sirler_bos_degil(self):
        """Liste bos kalirsa preflight her seyi 'gecer' sanir."""
        assert len(sir_preflight.GEREKEN_SIRLER) >= 7, (
            "kapsam 7 saglayici; %d" % len(sir_preflight.GEREKEN_SIRLER))

    def test_ondenetim_kurulumdan_once_kosuyor(self):
        """Sır denetimi `pip install` ONCESI olmali.

        Aksi halde sirlar yoksa kurulum da olur, denetim de olur —
        dakika israfi tam olarak bu yuzden engelleniyor.
        """
        kismi = _provider_acceptance_kismi()
        ondenetim = kismi.index("sir_preflight.py")
        kurulum = kismi.index("pip install -r requirements.txt")
        assert ondenetim < kurulum, (
            "on denetim kurulumdan sonra: %d > %d" % (ondenetim, kurulum))


class TestPreflightMantigi:
    def test_hic_sir_yoksa_durur(self):
        assert sir_preflight.preflight({}) == 1, (
            "anahtarsiz kosum 4+60 dakika israf eder — fail-closed degil")

    def test_bir_anahtar_yeterli_kismi_kosu(self):
        """Kismi kosum degerlidir; eksikler raporda NOT TESTED olur."""
        cevre = {"GROQ_API_KEY": "x"}
        assert sir_preflight.preflight(cevre) == 0

    def test_bos_dize_anahtar_sayilmaz(self):
        assert sir_preflight.preflight({"GROQ_API_KEY": "  "}) == 1
        assert sir_preflight.preflight({"GROQ_API_KEY": ""}) == 1

    def test_eksikler_adiyle_bildirilir(self, capsys):
        sir_preflight.preflight({"GROQ_API_KEY": "x"})
        cikti = capsys.readouterr().out
        assert "EKSIK" in cikti
        assert "MISTRAL_API_KEY" in cikti, cikti

    def test_sir_degeri_ekrana_yazilmaz(self, capsys):
        sir_preflight.preflight({"GROQ_API_KEY": "GIZLI-ANAHTAR-DEGERI"})
        cikti = capsys.readouterr().out
        assert "GIZLI-ANAHTAR-DEGERI" not in cikti, (
            "anahtar degeri konsola yazildi")

    def test_durumlar_ayirir(self):
        var, eksik = sir_preflight._durumlar(
            {"GROQ_API_KEY": "x", "ZAI_API_KEY": "y"})
        assert set(var) == {"GROQ_API_KEY", "ZAI_API_KEY"}
        assert "GROQ_API_KEY" not in eksik
        assert len(eksik) == len(sir_preflight.GEREKEN_SIRLER) - 2


class TestDosyaBagimsizligi:
    def test_preflight_proje_importu_yapmaz(self):
        """Kurulum oncesi kosacak dosya agirlik import edemez.

        `github_full_acceptance.py` ic ice import zinciriyle gelir;
        ondenetim onun yerine ayri ve bagimsiz bir dosyada durur.
        """
        kaynak = pathlib.Path(
            "tests/live/sir_preflight.py"
        ).read_text(encoding="utf-8")
        ic_i = re.findall(r"^(?:from|import)\s+(\S+)", kaynak, re.M)
        assert set(ic_i) <= {"os", "sys"}, ic_i


class TestKalanOluTetikleyiciler:
    """Ayni sinif hatasi diger akislarda da var mi? Taranir.

    `basak-full-acceptance.yml` ic checkout `ref:` degerinde silinmis
    bir dal adi geciyordu. Bu test ozel tetikleyicinin (issue #4
    yorumu) calistigini ve ref degerlerinin yasli dal icermedigini
    kilitlar.
    """

    def _full_acceptance(self):
        return pathlib.Path(
            ".github/workflows/basak-full-acceptance.yml"
        ).read_text(encoding="utf-8")

    def test_olu_dal_adi_kalmadi(self):
        assert "preview/p2-arac-ara-profesyonel" not in \
            _kod(self._full_acceptance()), (
            "FULL TEST P2, silinmis dali cekiyor — kosum hep basarisiz")

    def test_ozel_tetikleyici_duruyor(self):
        akis = self._full_acceptance()
        assert "issue_comment" in akis
        assert "github.event.issue.number == 4" in akis
