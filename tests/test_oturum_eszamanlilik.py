"""tests/test_oturum_eszamanlilik.py — ayni oturuma eszamanli yazma.

2026-10-03 DENETIMI: `chat/oturum.py` oku-degistir-yaz dongusunu
kilitsiz yapiyordu ve "w" modunda yaziyordu (once kirpar, sonra
doldurur). Web sunucusu istekleri paralel isler (app.py her mesaji
asyncio.to_thread ile kosturur), so:

  - iki istek ayni dosyayi ayni anda okur, ikisi de kendi ciftini
    ekler, ikisi de yazar -> bir cift KAYBOLUR (kullanici mesaji
    sessizce silinir),
  - bir okuyucu yarim JSON gormezdi.

Duzeltme: `tools/tasks.py` deseni — `_KILIT` (RLock) + `.tmp` ve
`os.replace` ile atomik yazma.

Bu test ESKI KODDA KIRMILIR: asagida `git stash` ile dogrulandi.
"""
import json
import os
import sys
import threading
import time

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from chat import oturum  # noqa: E402


def _sifirla(monkeypatch, tmp_path):
    monkeypatch.setattr(oturum, "DIZIN", str(tmp_path / "sohbetler"))
    monkeypatch.setattr(oturum, "AKTIF_DOSYA", str(tmp_path / "aktif"))


def test_paralel_kaydet_kayip_yok(monkeypatch, tmp_path):
    """8 thread ayni oturuma yaziyor: 8 ciftin 8'i de durmali.

    `_oku` icine kisa bir bekleme konur: boylece hepsi KILIT OLMADAN
    ayni bos durumu okur ve eski kodda kayip deterministik olur.
    """
    _sifirla(monkeypatch, tmp_path)
    sid = "g8"
    gercek_oku = oturum._oku

    def yavas_oku(s):
        time.sleep(0.005)
        return gercek_oku(s)

    monkeypatch.setattr(oturum, "_oku", yavas_oku)

    hata = []

    def yaz(i):
        try:
            oturum.kaydet_cift("soru-%d" % i, "cevap-%d" % i, sid=sid)
        except Exception as e:  # pragma: no cover - hata gorunur olmali
            hata.append(e)

    ts = [threading.Thread(target=yaz, args=(i,)) for i in range(8)]
    for t in ts:
        t.start()
    for t in ts:
        t.join()

    assert hata == []
    kayit = gercek_oku(sid)
    assert kayit is not None
    assert len(kayit["mesajlar"]) == 16, (
        "kayıp var: 16 mesaj bekleniyordu, %d durdu" % len(kayit["mesajlar"]))

    # Sorularin hepsi bir kez geciyor (silinen degil, ezilen cift yok).
    sorular = [m["content"] for m in kayit["mesajlar"]
               if m["role"] == "user"]
    assert sorted(sorular) == sorted("soru-%d" % i for i in range(8))


def test_aktif_dosya_ham_sid_tutar(monkeypatch, tmp_path):
    """Aktif oturum dosyasi JSON degil, HAM sid metni olmali.

    JSON'a cevrilirse dosya `"abc"` seklinde yazilir, okuyan `.strip()`
    sonrasi tirnaklari gormez ve her acilista YENI oturum uretilir.
    """
    _sifirla(monkeypatch, tmp_path)
    ilk = oturum.aktif_id()
    ikinci = oturum.aktif_id()
    assert ilk == ikinci, "aktif oturum her okumada degisiyor"
    ham = (tmp_path / "aktif").read_text(encoding="utf-8")
    assert ham == ilk
    assert not ham.startswith('"')


def test_eszamanli_okuyucu_yarim_json_gormez(monkeypatch, tmp_path):
    """Yazma sirasinda okuyan hicbir zaman bozuk dosya gormemeli."""
    _sifirla(monkeypatch, tmp_path)
    sid = "r1"
    oturum.kaydet_cift("ilk", "cevap", sid=sid)
    yol = oturum._yol(sid)

    durdur = threading.Event()
    bozuk = []

    def oku():
        while not durdur.is_set():
            try:
                with open(yol, "r", encoding="utf-8") as f:
                    icerik = f.read()
                if icerik.strip():
                    json.loads(icerik)  # yarim JSON -> ValueError
            except FileNotFoundError:
                pass
            except PermissionError:
                # WINDOWS: dosya os.replace ile degistirilirken acik
                # kalmak gecici reddedilir. Bu bozulma DEGILDIR —
                # dosya hicbir zaman yarim gorunmez, ya hic acilmaz ya
                # tam acilir. Uretim kodu da ayni sekilde yeniden dener.
                pass
            except ValueError as e:
                bozuk.append(str(e))

    okuyucu = threading.Thread(target=oku)
    okuyucu.start()
    try:
        for i in range(40):
            oturum.kaydet_cift("s%d" % i, "c%d" % i, sid=sid)
    finally:
        durdur.set()
        okuyucu.join()

    assert bozuk == [], "okuyucu bozuk dosya gordu: %d kez" % len(bozuk)


def test_gecici_dosya_kalmaz(monkeypatch, tmp_path):
    """Atomik yazma sonrasi .tmp artigi durmamali."""
    _sifirla(monkeypatch, tmp_path)
    oturum.kaydet_cift("soru", "cevap", sid="tmp1")
    artik = [p for p in os.listdir(oturum._dizin()) if p.endswith(".tmp")]
    assert artik == [], "gecici dosya kaldi: %s" % artik


def test_kaydet_cift_kilit_tutar(monkeypatch, tmp_path):
    """Yapısal: oku-değiştir-yaz döngüsünün tamamı kilit altında.

    Davranış testi bir hata çıkarmazsa buraya düşer — yarı koruma
    (sadece `_yaz` atomik, döngü kilitsiz) sessizce kayba yol açar.
    """
    import inspect
    kaynak = inspect.getsource(oturum.kaydet_cift)
    assert "with _KILIT:" in kaynak
    # Kilit, okumadan SONRA ama yazmadan ONCE aciliyor olmali:
    # _oku ve _yaz ikisi de blok icinde kalmali.
    with_i = kaynak.index("with _KILIT:")
    assert with_i < kaynak.index("_oku(")
    assert with_i < kaynak.index("_yaz(")
