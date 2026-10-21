"""tests/test_web_govde.py — POST govdesi: `Content-Length` ve chunked.

Neden: bulut onizleme kabugu govdeyi parcali (chunked) iletiyor. Eski kod
yalniz `Content-Length`e bakiyordu, bu yuzden onizlemede her mesaj
"Bir sorun oluştu: gövde boyu" diye reddedildi (olculdu: curl normal 200,
aynı govde chunked 400). Bu dosya iki bicimi de kilitler.

Agirlik yok: chunked cozucu sahte bir okuyucuyla, uctan uca yol ise
gercek soket + `/api/giris` (model cagirmaz, hatali giris 401 doner).
"""

import io
import json
import os
import socket
import sys
import threading

import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
import basak_web


class _SahteIstek:
    """Yalniz `headers` + `rfile` tasiyan asgari istek nesnesi."""

    def __init__(self, govde: bytes, basliklar=None):
        self.headers = basliklar or {}
        self.rfile = io.BytesIO(govde)


def _parcala(istek, sinir=basak_web._SOHBET_GOVDE_SINIRI):
    return basak_web._Kopru._parcali_govde(istek, sinir)


def _chunked(parcalar):
    """Parcalari gercek chunked bicimine cevirir (boy OnALTILIK)."""
    govde = b""
    for parca in parcalar:
        govde += ("%x" % len(parca)).encode("ascii") + b"\r\n" + parca + b"\r\n"
    return govde + b"0\r\n\r\n"


def test_chunked_govde_cozulur():
    ham = _chunked([b'{"metin":', b'"Merhaba"}'])
    assert _parcala(_SahteIstek(ham)) == b'{"metin":"Merhaba"}'


def test_chunked_tavan_asilirsa_hata():
    ham = _chunked([b"x" * 255])
    with pytest.raises(ValueError):
        _parcala(_SahteIstek(ham), sinir=100)


def test_chunked_bozuk_boy_hata_verir():
    with pytest.raises(ValueError):
        _parcala(_SahteIstek(b"zz\r\nabc\r\n0\r\n\r\n"))


def test_content_length_yolu_hala_calisir():
    istek = _SahteIstek(b'{"a":1}', {"Content-Length": "7"})
    assert basak_web._Kopru._istek_govdesi(istek, 100) == b'{"a":1}'


def test_content_length_tavani_asilirsa_hata():
    istek = _SahteIstek(b"x" * 50, {"Content-Length": "50"})
    with pytest.raises(ValueError):
        basak_web._Kopru._istek_govdesi(istek, 10)


def test_govde_yoksa_bos_doner():
    assert basak_web._Kopru._istek_govdesi(_SahteIstek(b""), 100) == b""


@pytest.fixture
def sunucu():
    """Gercek soket uzerinde calisan kopru (kimlik istemez: /api/giris)."""
    from http.server import ThreadingHTTPServer

    onceki = (basak_web.BEYIN, basak_web.TOOLS)
    sunucu = ThreadingHTTPServer(("127.0.0.1", 0), basak_web._Kopru)
    is_parcacigi = threading.Thread(target=sunucu.serve_forever, daemon=True)
    is_parcacigi.start()
    yield sunucu.server_address[1]
    sunucu.shutdown()
    sunucu.server_close()
    basak_web.BEYIN, basak_web.TOOLS = onceki


def _ham_istek(port, govde, chunked):
    basliklar = [
        "POST /api/giris HTTP/1.1",
        "Host: localhost",
        "Content-Type: application/json",
    ]
    if chunked:
        basliklar.append("Transfer-Encoding: chunked")
    else:
        basliklar.append("Content-Length: %d" % len(govde))
    basliklar.append("Connection: close")
    bas = ("\r\n".join(basliklar) + "\r\n\r\n").encode("ascii")
    govde_ham = govde
    if chunked:
        govde_ham = ("%x\r\n" % len(govde)).encode("ascii") + govde + b"\r\n0\r\n\r\n"
    with socket.create_connection(("127.0.0.1", port), timeout=10) as s:
        s.sendall(bas + govde_ham)
        parcalar = []
        while True:
            parca = s.recv(4096)
            if not parca:
                break
            parcalar.append(parca)
    return b"".join(parcalar)


def _durum_ve_govde(cevap):
    bas, _, govde = cevap.partition(b"\r\n\r\n")
    durum = int(bas.split(b" ")[1])
    return durum, govde


@pytest.mark.parametrize("chunked", [False, True])
def test_giris_uctan_uca_her_iki_bicimde_de_401(sunucu, chunked):
    """Onemli olan: chunked istek 'govde boyu' (400) ALMAMALI."""
    govde = json.dumps({"ad": "olmayan", "sifre": "yanlis"}).encode("utf-8")
    durum, ham = _durum_ve_govde(_ham_istek(sunucu, govde, chunked))
    assert durum == 401, ham
    assert "govde boyu" not in ham.decode("utf-8", "replace")
