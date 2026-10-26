"""tests/test_isci_kuyrugu.py — kalıcı işçi kuyruğu sözleşmesi.

Ölçülen şey yalnız söz değil, gerçek SQLite (ve CI'da Postgres) üzerinde
çalışan davranıştır:

- Aynı koşu + adım iki satır yaratmaz; farklı eylem aynı kimliğe sığmaz.
- İşi yalnız bir işçi alır; kapanmış iş EZİLMEZ.
- Tekrar hakkı sınırlıdır; sınır aşılınca `hata`.
- Çöken işçinin işi kör tekrar edilmez, `supheli` işaretlenir.
- Nonce kalıcıdır: süreç yeniden başlasa da belge ikinci kez çalışmaz.
"""

import json
import threading
import time

import pytest

from worker import kuyruk as kq
from worker.guvenlik import token_uret

ANAHTAR = "test-iscisi-anahtari-32-bayt"
KOSU = "kosu-1"
URL = "https://ornek.test/sayfa"


@pytest.fixture
def kuyruk(tmp_path):
    return kq.Kuyruk(sqlite_yolu=str(tmp_path / "isci.db"))


def _eylem(tur="oku"):
    if tur == "ac":
        return {"tur": "ac", "url": URL}
    if tur == "yaz":
        return {"tur": "yaz", "secici": "#kutu", "metin": "merhaba"}
    return {"tur": tur, "secici": "#icerik"}


def _birak(kuyruk, adim="adim-1", kosu=KOSU, tur="oku", eylem=None,
           url=URL, simdi=None, nonce=None):
    eylem = eylem or _eylem(tur)
    token, payload = token_uret(
        ANAHTAR, kosu_id=kosu, adim_id=adim, tur=eylem["tur"], url=url,
        argumanlar=eylem, ttl=300, nonce=nonce, simdi=simdi)
    satir = kuyruk.birak(kosu, adim, eylem, token, url, simdi=simdi)
    return satir, token, payload


def test_ayni_kosu_adim_ikinci_satir_yaratmaz(kuyruk):
    ilk, _, _ = _birak(kuyruk)
    ikinci, _, _ = _birak(kuyruk)
    assert ilk["id"] == ikinci["id"]
    assert ikinci["durum"] == "bekliyor"
    assert kuyruk.ozet()["bekliyor"] == 1


def test_ayni_kimlige_farkli_eylem_sigismaz(kuyruk):
    _birak(kuyruk)
    with pytest.raises(kq.KuyrukHatasi, match="farklı eylem"):
        _birak(kuyruk, eylem={"tur": "tikla", "secici": "#baska"})


def test_bekleyen_ise_yeni_belge_yazilabilir(kuyruk):
    _, eski, _ = _birak(kuyruk, nonce="n-eski")
    _, yeni, _ = _birak(kuyruk, nonce="n-yeni")
    assert eski != yeni
    satir = kuyruk.adim_oku(KOSU, "adim-1")
    assert satir["token"] == yeni
    assert satir["durum"] == "bekliyor"


def test_calisan_ise_yeni_belge_yazilmaz(kuyruk):
    _, eski, _ = _birak(kuyruk)
    alinan = kuyruk.al("isci-1")
    assert alinan is not None
    _birak(kuyruk, nonce="n-sonra")
    satir = kuyruk.adim_oku(KOSU, "adim-1")
    assert satir["token"] == eski
    assert satir["durum"] == "calisiyor"


def test_isi_yalniz_bir_isci_alir(kuyruk):
    birakilan, _, _ = _birak(kuyruk)
    alinan = kuyruk.al("isci-1")
    assert alinan["id"] == birakilan["id"]
    assert alinan["durum"] == "calisiyor"
    assert alinan["isci"] == "isci-1"
    assert alinan["deneme"] == 1
    assert kuyruk.al("isci-2") is None


def test_kapanmis_is_ezilmez(kuyruk):
    _birak(kuyruk)
    alinan = kuyruk.al("isci-1")
    assert alinan is not None
    assert kuyruk.bitir(
        alinan["id"], "baska-isci", {"ok": True}) is None
    bitti = kuyruk.bitir(
        alinan["id"], "isci-1", {"ok": True, "metin": "sonuç"})
    assert bitti["durum"] == "bitti"
    assert json.loads(bitti["sonuc"])["metin"] == "sonuç"

    tekrar = kuyruk.bitir(
        alinan["id"], "isci-1", {"ok": False, "metin": "ezildi"})
    assert tekrar is None
    assert json.loads(kuyruk.oku(alinan["id"])["sonuc"])["metin"] == "sonuç"


def test_hata_durumu_kanitla_yazilir(kuyruk):
    _birak(kuyruk)
    alinan = kuyruk.al("isci-1")
    satir = kuyruk.bitir(
        alinan["id"], "isci-1", {"ok": False}, hata="tıklama zaman aşımı")
    assert satir["durum"] == "hata"
    assert "zaman aşımı" in satir["hata"]
    assert satir["bitis"] is not None


def test_tekrar_hakki_sinirlidir(kuyruk):
    _birak(kuyruk)
    ilk = kuyruk.al("isci-1")
    tekrar = kuyruk.birak_tekrar(
        ilk["id"], "isci-1", "geçici hata", azami=2)
    assert tekrar["durum"] == "bekliyor"
    assert tekrar["isci"] is None
    assert tekrar["bitis"] is None

    ikinci = kuyruk.al("isci-2")
    assert ikinci["deneme"] == 2
    son = kuyruk.birak_tekrar(
        ikinci["id"], "isci-2", "yine hata", azami=2)
    assert son["durum"] == "hata"
    assert son["bitis"] is not None
    assert kuyruk.al("isci-3") is None


def test_calisan_isi_baska_isci_tekrara_birakamaz(kuyruk):
    _birak(kuyruk)
    ilk = kuyruk.al("isci-1")
    assert kuyruk.birak_tekrar(
        ilk["id"], "isci-2", "sahte", azami=2) is None
    assert kuyruk.oku(ilk["id"])["isci"] == "isci-1"


def test_coken_iscinin_isi_supheli_olur(kuyruk):
    simdi = 1_000.0
    _birak(kuyruk, simdi=simdi)
    alinan = kuyruk.al("isci-1", simdi=simdi)
    assert alinan is not None
    kuyruk.kalp("isci-1", simdi=simdi)

    assert kuyruk.temizle(esik=90, simdi=simdi + 10) == 0
    assert kuyruk.oku(alinan["id"])["durum"] == "calisiyor"

    # Kalp 200 sn önce durdu: iş belirsizdir, kör tekrar edilmez.
    assert kuyruk.temizle(esik=90, simdi=simdi + 200) == 1
    satir = kuyruk.oku(alinan["id"])
    assert satir["durum"] == "supheli"
    assert "işçi kayboldu" in satir["hata"]


def test_canli_iscinin_isi_supheli_olmaz(kuyruk):
    simdi = 1_000.0
    _birak(kuyruk, simdi=simdi)
    alinan = kuyruk.al("isci-1", simdi=simdi)
    assert alinan is not None
    kuyruk.kalp("isci-1", simdi=simdi + 190)
    assert kuyruk.temizle(esik=90, simdi=simdi + 200) == 0
    assert kuyruk.oku(alinan["id"])["durum"] == "calisiyor"


def test_kalp_atisi_canli_isciligi_belirler(kuyruk):
    kuyruk.kalp("a", durum="hazir", surum="1", simdi=1_000)
    kuyruk.kalp("a", durum="mesgul", surum="2", is_id="is-9", simdi=1_010)
    kuyruk.kalp("b", simdi=1_000)
    canli = kuyruk.canli_isciler(esik=90, simdi=1_020)
    assert [i["isci"] for i in canli] == ["a", "b"]
    a = canli[0]
    assert a["durum"] == "mesgul"
    assert a["surum"] == "2"
    assert a["is"] == "is-9"
    assert a["yas_sn"] == 10
    assert kuyruk.canli_isciler(esik=90, simdi=1_200) == []


def test_nonce_kalicidir_ve_sure_sonunda_temizlenir(tmp_path):
    yol = str(tmp_path / "isci.db")
    ilk = kq.Kuyruk(sqlite_yolu=yol)
    assert ilk.nonce_al("n-1", 2_000, simdi=1_000) is True
    assert ilk.nonce_al("n-1", 2_000, simdi=1_001) is False

    # Süreç yeniden başladı: aynı nonce hâlâ ikinci kez kullanılamaz.
    ikinci = kq.Kuyruk(sqlite_yolu=yol)
    assert ikinci.nonce_al("n-1", 2_000, simdi=1_002) is False

    # Süresi geçmiş kayıt temizlenir; eski belge zaten kullanılamaz.
    ikinci.temizle(esik=90, simdi=3_000)
    assert ikinci.nonce_al("n-1", 4_000, simdi=3_000) is True


def test_ozet_durumlari_sayar(kuyruk):
    _birak(kuyruk, adim="a1")
    _birak(kuyruk, adim="a2")
    alinan = kuyruk.al("isci-1")
    kuyruk.bitir(alinan["id"], "isci-1", {"ok": True})
    kuyruk.kalp("isci-1", simdi=time.time())
    ozet = kuyruk.ozet()
    assert ozet["bitti"] == 1
    assert ozet["bekliyor"] == 1
    assert ozet["canli"] == 1
    assert [i["isci"] for i in ozet["isciler"]] == ["isci-1"]


def test_paralel_isciler_ayni_isi_alamaz(kuyruk):
    for i in range(8):
        _birak(kuyruk, adim="adim-%d" % i)
    sonuc = []
    kilit = threading.Lock()

    def al(ad):
        satir = kuyruk.al(ad)
        with kilit:
            sonuc.append(satir)

    is_parcaciklari = [
        threading.Thread(target=al, args=("isci-%d" % i,)) for i in range(4)]
    for p in is_parcaciklari:
        p.start()
    for p in is_parcaciklari:
        p.join(timeout=20)
    assert all(not p.is_alive() for p in is_parcaciklari)
    alinan = [s for s in sonuc if s]
    assert len(alinan) == 4
    assert len({s["id"] for s in alinan}) == 4


def test_gecersiz_girdi_acik_hata_verir(kuyruk):
    token, _ = token_uret(
        ANAHTAR, kosu_id=KOSU, adim_id="a1", tur="oku", url=URL,
        argumanlar=_eylem("oku"))
    with pytest.raises(kq.KuyrukHatasi, match="kimliği boş"):
        kuyruk.birak("", "a1", _eylem("oku"), token, URL)
    with pytest.raises(kq.KuyrukHatasi, match="kimliği boş"):
        kuyruk.birak(KOSU, "", _eylem("oku"), token, URL)
    with pytest.raises(kq.KuyrukHatasi, match="eylem boş"):
        kuyruk.birak(KOSU, "a1", {}, token, URL)
    with pytest.raises(kq.KuyrukHatasi, match="onay belgesi"):
        kuyruk.birak(KOSU, "a1", _eylem("oku"), "", URL)
    with pytest.raises(kq.KuyrukHatasi, match="kaynak adresi"):
        kuyruk.birak(KOSU, "a1", _eylem("oku"), token, "file:///etc/passwd")
