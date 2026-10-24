# -*- coding: utf-8 -*-
"""tests/test_kesilme_devam.py — baglanti kopunca is kaybolmaz (Yol B-1).

2026-10-22 OLCUMU: beklenmedik akis kesilmesinde web/app.js butun calisma
satirini siliyordu (`row.remove()`) ve "Bir sorun oluştu" balonu birakiyordu —
oysa o ana kadar gelen olaylar sunucu imzali handoff tokeninde duruyordu
(app.py `_handoff_tokeni`; her toolDone/source/runState olayi imzali tokenle
gider). Mola ayni kayitla "Devam et" sunabiliyorken kesilme sunamiyordu.
Bu dosya sozlesmeyi kilitler:

- kesilme hatasi `kesilme` isaretini tasir (test_web_akis_kesilme.py);
- `kesilmedeDevamVarMi(err, kayit)` yalniz kesilme + imzalı kayit + bitmemis
  calisma icin true doner — Node'da GERCEK fonksiyonla kosulur;
- kesilme + kayit varsa satir SILINMEZ, mola ile ayni "Devam et" sunulur;
- kayit yoksa bugunun davranisi aynen kalir (satir silinir, acik hata).

AGENTS.md §0: karar metne veya arac adina bakmaz; yalniz durum (isaret +
elde imzali kayit) bakar.
"""

import json
import pathlib
import re
import shutil
import subprocess
import tempfile

import pytest

KOK = pathlib.Path(__file__).resolve().parents[1]
JAVASCRIPT = (KOK / "web" / "app.js").read_text(encoding="utf-8")
HTML = (KOK / "web" / "index.html").read_text(encoding="utf-8")
NODE = shutil.which("node")

pytestmark = pytest.mark.skipif(NODE is None, reason="node yok")


def _fonksiyon(ad):
    m = re.search(r"(function " + ad + r"\([\s\S]*?\n\})", JAVASCRIPT)
    assert m is not None, ad + " app.js'te yok"
    return m.group(1)


def _node(betik):
    with tempfile.TemporaryDirectory() as klasor:
        dosya = pathlib.Path(klasor) / "kesilme_testi.js"
        dosya.write_text(betik, encoding="utf-8")
        cikti = subprocess.run(
            [NODE, str(dosya)], capture_output=True, encoding="utf-8",
            timeout=30)
    assert cikti.returncode == 0, cikti.stderr
    return json.loads(cikti.stdout.strip().splitlines()[-1])


class TestKesilmedeDevamKarari:
    """Karar saf fonksiyondur; metne/araç adina bakmaz, yalniz duruma bakar."""

    def _kos(self, err, kayit):
        return _node("""
%(kaynak)s
const sonuc = kesilmedeDevamVarMi(%(err)s, %(kayit)s);
console.log(JSON.stringify({ karar: sonuc }));
""" % {
            "kaynak": _fonksiyon("kesilmedeDevamVarMi"),
            "err": "null" if err is None else json.dumps(err),
            "kayit": "null" if kayit is None else json.dumps(kayit),
        })["karar"]

    def test_kesilme_ve_imzali_kayit_devam_sunar(self):
        assert self._kos(
            {"kesilme": True, "message": "baglanti kapandi"},
            {"bitti": False, "handoffToken": "govde.imza"},
        ) is True

    def test_token_yoksa_devam_sunulmez(self):
        assert self._kos(
            {"kesilme": True}, {"bitti": False, "handoffToken": ""},
        ) is False

    def test_bitmis_calisma_devam_sunmaz(self):
        assert self._kos(
            {"kesilme": True}, {"bitti": True, "handoffToken": "govde.imza"},
        ) is False

    def test_kesilme_olmayan_hata_devam_sunmaz(self):
        """Kota/sunucu reddi kesilme degildir; kurtarma yolu acilmaz."""
        assert self._kos(
            {"kesilme": False, "message": "Gunluk ucretsiz hakkin doldu."},
            {"bitti": False, "handoffToken": "govde.imza"},
        ) is False

    def test_hatasiz_durum_devam_sunmaz(self):
        assert self._kos(None, {"bitti": False, "handoffToken": "x"}) is False

    def test_kayitsiz_durum_cokmez(self):
        assert self._kos({"kesilme": True}, None) is False


class TestWebSozlesmesi:
    """Kesilme kurtarma akisi web kaynaginda tam ve tek yerdedir."""

    def test_kesilme_hatasi_isaretli_uretilir(self):
        # canliYanitiOku icindeki kesilme hatalari isaretlenir; digerleri degil.
        assert "hata.kesilme = true;" in JAVASCRIPT
        i = JAVASCRIPT.index("const kesilmeHatasi")
        govde = JAVASCRIPT[i:i + 600]
        assert "kesilme" in govde

    def test_catch_dalinda_kurtarma_var(self):
        assert "kesilmedeDevamVarMi(err, calisma)" in JAVASCRIPT
        assert 'calismaMolaVer(bekleyenBalon, "kesilme")' in JAVASCRIPT

    def test_kurtarma_satiri_silmez_silme_hata_yolunda_kalir(self):
        # Sira: send() catch'inde kurtarma dali SILME'den once gelir;
        # silme yalniz imzali kayit olmayan hata yolunda kalir.
        send_yeri = JAVASCRIPT.index("async function send")
        catch_yeri = JAVASCRIPT.index("} catch (err) {", send_yeri)
        kurtarma = JAVASCRIPT.index(
            'calismaMolaVer(bekleyenBalon, "kesilme")', catch_yeri)
        silme = JAVASCRIPT.index("if (row) row.remove();", kurtarma)
        assert kurtarma < silme
        assert 'bubble("assistant", err && err.kota' in JAVASCRIPT

    def test_mola_ve_kesilme_ayni_devam_akisini_paylasir(self):
        # "Devam et" tek yerden cikar; iki durum da imzali kaydi geri gonderir.
        assert 'devam.textContent = "Devam et"' in JAVASCRIPT
        assert "yonlendirmeBaglami: yonlendirmeBaglamiOlustur(b)" in JAVASCRIPT
        assert 'text: "Kaldığın yerden devam et."' in JAVASCRIPT

    def test_mola_ozel_metni_korunur(self):
        # Varsayilan mola davranisi degismez (calisma_ozeti kilidi).
        assert 'function calismaMolaVer(b, sebep = "mola")' in JAVASCRIPT
        assert "Mola · " in JAVASCRIPT

    def test_kesilme_metni_dürüsttür(self):
        # Baslik ve ozet gercegi soyler: mola degil, baglanti koptu.
        assert '"Bağlantı koptu · "' in JAVASCRIPT
        assert "Bağlantı beklenmedik kapandı;" in JAVASCRIPT

    def test_surum_kilidi_yukseltildi(self):
        assert "/app.js?v=30" in HTML
