"""tests/test_isci_calistirici.py — kuyruktan iş alıp uygulama döngüsü.

Gerçek Chromium burada yok; tarayıcı sınıfının sözleşmesini uygulayan bir
dublör var. Amaç işçinin KARAR VERMEDİĞİNİ ve hata sınıflamasını ölçmek:

- Geçerli belge + eylem → iş `bitti`, sonuç defterde.
- Belge başka koşuya/adıma aitse ya da süresi dolduysa → eylem ÇALIŞMAZ,
  iş `hata`.
- Aynı nonce ikinci kez → eylem çalışmaz, iş `hata` (kalıcı defter).
- Tarayıcı hatası → `hata` (kanıt metniyle), otomatik tekrar yok.
- Beklenmeyen hata → `supheli` (kör tekrar yok).
"""

import asyncio
import json
import time

import pytest

from worker import kuyruk as kq
from worker.calistirici import Calistirici
from worker.guvenlik import TokenHatasi, token_dogrula, token_uret
from worker.hatalar import TarayiciHatasi

ANAHTAR = "test-iscisi-anahtari-32-bayt"
KOSU = "kosu-1"
ADIM = "adim-1"
URL = "https://ornek.test/sayfa"


class SahteTarayici:
    """Gerçek sınıfın sözleşmesi: belgeyi doğrula, nonce'u harca, uygula."""

    def __init__(self, kuyruk=None, sonuc=None, hata=None):
        self.kuyruk = kuyruk
        self.sonuc = sonuc if sonuc is not None else {
            "ok": True, "tur": "oku", "metin": "Merhaba"}
        self.hata = hata
        self.cagrilar = []
        self.calistirildi = False

    async def adim(self, kosu_id, eylem, token, *, adim_id):
        self.cagrilar.append({
            "kosu_id": kosu_id, "adim_id": adim_id, "eylem": dict(eylem),
        })
        url = str(eylem.get("url") or URL)
        payload = token_dogrula(
            ANAHTAR, token, tur=eylem.get("tur"), url=url,
            argumanlar=eylem, kosu_id=kosu_id, adim_id=adim_id)
        if self.kuyruk is not None:
            if not self.kuyruk.nonce_al(payload["nonce"], payload["exp"]):
                raise TokenHatasi("onay belgesi daha önce kullanıldı")
        if self.hata is not None:
            self.calistirildi = True
            raise self.hata
        self.calistirildi = True
        return dict(self.sonuc)


@pytest.fixture
def kurulum(tmp_path):
    kuyruk = kq.Kuyruk(sqlite_yolu=str(tmp_path / "isci.db"))
    tarayici = SahteTarayici(kuyruk)
    calistirici = Calistirici(
        kuyruk, tarayici, isci="isci-1", surum="test",
        aralik=0.1, kalp_aralik=5.0, esik=90.0)
    return kuyruk, tarayici, calistirici


def _birak(kuyruk, adim=ADIM, kosu=KOSU, eylem=None, token_kosu=None,
           nonce=None, simdi=None, ttl=300):
    eylem = eylem or {"tur": "oku", "secici": "#icerik"}
    token, payload = token_uret(
        ANAHTAR, kosu_id=token_kosu or kosu, adim_id=adim,
        tur=eylem["tur"], url=URL, argumanlar=eylem, ttl=ttl,
        nonce=nonce, simdi=simdi)
    satir = kuyruk.birak(kosu, adim, eylem, token, URL)
    return satir, token, payload


def _satir(kuyruk, satir):
    return kuyruk.oku(str(satir["id"]))


def test_gecerli_is_uygulanir_ve_sonuc_yazilir(kurulum):
    kuyruk, tarayici, calistirici = kurulum
    birakilan, _, _ = _birak(kuyruk)

    sonuc = asyncio.run(calistirici.tek_tur())

    assert sonuc["durum"] == "bitti"
    assert json.loads(sonuc["sonuc"])["metin"] == "Merhaba"
    assert tarayici.cagrilar[0]["kosu_id"] == KOSU
    assert tarayici.cagrilar[0]["adim_id"] == ADIM
    assert tarayici.cagrilar[0]["eylem"]["tur"] == "oku"
    assert tarayici.calistirildi is True
    assert _satir(kuyruk, birakilan)["bitis"] is not None


def test_bos_kuyrukta_none_doner_ve_kalp_yazar(kurulum):
    kuyruk, _, calistirici = kurulum
    assert asyncio.run(calistirici.tek_tur()) is None
    canli = kuyruk.canli_isciler()
    assert len(canli) == 1
    assert canli[0]["isci"] == "isci-1"
    assert canli[0]["durum"] == "hazir"


def test_baska_kosunun_belgesi_eylemi_calistirmaz(kurulum):
    kuyruk, tarayici, calistirici = kurulum
    birakilan, _, _ = _birak(kuyruk, token_kosu="baska-kosu")

    sonuc = asyncio.run(calistirici.tek_tur())

    assert sonuc["durum"] == "hata"
    assert "başka koşu" in sonuc["hata"]
    assert tarayici.calistirildi is False
    assert _satir(kuyruk, birakilan)["durum"] == "hata"


def test_suresi_dolmus_belge_eylemi_calistirmaz(kurulum):
    kuyruk, tarayici, calistirici = kurulum
    _birak(kuyruk, simdi=time.time() - 1_000, ttl=10)

    sonuc = asyncio.run(calistirici.tek_tur())

    assert sonuc["durum"] == "hata"
    assert "süresi doldu" in sonuc["hata"]
    assert tarayici.calistirildi is False


def test_ayni_nonce_ikinci_kez_calismaz(kurulum):
    kuyruk, tarayici, calistirici = kurulum
    birakilan, _, payload = _birak(kuyruk, nonce="n-tek")
    assert kuyruk.nonce_al("n-tek", payload["exp"]) is True

    sonuc = asyncio.run(calistirici.tek_tur())

    assert sonuc["durum"] == "hata"
    assert "daha önce kullanıldı" in sonuc["hata"]
    assert tarayici.calistirildi is False
    assert _satir(kuyruk, birakilan)["durum"] == "hata"


def test_tarayici_hatasi_hata_olarak_yazilir_ve_tekrarlanmaz(kurulum):
    kuyruk, tarayici, calistirici = kurulum
    tarayici.hata = TarayiciHatasi("tıklama zaman aşımı")
    _birak(kuyruk, eylem={"tur": "tikla", "secici": "#dugme"})

    sonuc = asyncio.run(calistirici.tek_tur())

    assert sonuc["durum"] == "hata"
    assert "zaman aşımı" in sonuc["hata"]
    assert json.loads(sonuc["sonuc"])["ok"] is False
    assert tarayici.calistirildi is True
    # Otomatik tekrar YOK: aynı eylem ikinci kez kuyruğa dönmez.
    assert kuyruk.al("isci-2") is None


def test_beklenmeyen_hata_supheli_olur(kurulum):
    kuyruk, tarayici, calistirici = kurulum
    tarayici.hata = RuntimeError("tarayıcı süreci çöktü")
    _birak(kuyruk)

    sonuc = asyncio.run(calistirici.tek_tur())

    assert sonuc["durum"] == "supheli"
    assert "beklenmeyen hata" in sonuc["hata"]
    assert tarayici.calistirildi is True


def test_calisirken_durdurma_isi_supheli_birakir(kurulum):
    kuyruk, tarayici, calistirici = kurulum
    birakilan, _, _ = _birak(kuyruk)

    async def senaryo():
        tarayici.hata = asyncio.CancelledError()
        with pytest.raises(asyncio.CancelledError):
            await calistirici.tek_tur()

    asyncio.run(senaryo())
    satir = kuyruk.oku(birakilan["id"])
    assert satir["durum"] == "supheli"
    assert "durduruldu" in satir["hata"]


def test_durdurulan_dongu_kalp_atisini_duruyor_yazar(kurulum):
    kuyruk, _, calistirici = kurulum
    calistirici.durdur()
    asyncio.run(calistirici.kos())
    canli = kuyruk.canli_isciler()
    assert len(canli) == 1
    assert canli[0]["durum"] == "duruyor"


def test_saglik_ozeti_kuyrugu_ve_iscini_gosterir(kurulum):
    kuyruk, _, calistirici = kurulum
    _birak(kuyruk)
    veri = calistirici.saglik()
    assert veri["ok"] is True
    assert veri["isci"] == "isci-1"
    assert veri["surum"] == "test"
    assert veri["kuyruk"]["bekliyor"] == 1
    assert veri["kuyruk"]["canli"] == 0
