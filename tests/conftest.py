"""tests/conftest.py — test kosusu teshis dosyasina (hata.log) yazmaz.

Denetim bulgusu (2026-10-01): hata.log 36.016 satira cikmisti ve agirligi
TEST gurultusuydu — sayim: ~15.500 satir "Optional ajan stream acilamadi:
testte stream yok" + ~13.500 satir httpx2 "HTTP Request" kaydi.

Kaynak: test dosyalarindan biri basak_app'i import ettiginde (toplama
asamasinda bile) basak_app.py'deki basicConfig(force=True)
RotatingFileHandler'i KURUYOR; sonrasi tum test kayitlari teshis
dosyasina dusuyordu ve gercek kok sebep gomuluyordu.

Cozum: conftest toplanmadan once yuklenir; buradaki bayrak basak_app'e
test ortaminda oldugunu soyler, basak_app dosya handler'i kurmaz.
Konsol kaydi aynen kalir, uretimde (python basak_app.py) bayrak yoktur.
"""

import os
import socket

import pytest

os.environ["BASAK_TEST_KOSUSU"] = "1"


@pytest.fixture
def sabit_genel_dns(monkeypatch):
    """Yalniz isteyen cevrimdisi testlerde DNS'i sabitler.

    HTTP hatlari zaten test doubles'dir. SSRF karar fonksiyonlari aynen
    calisir: sabit dis adresleri onaylar, literal ozel IP'leri reddeder.
    Listede olmayan alan adlari gercek DNS'e cikmak yerine cozulemez.
    """
    alanlar = {
        "example.com", "tr.wikipedia.org", "ornek.com", "ornek.com.tr",
        "www.accio.com", "freetools.org", "www.freetools.org",
        "photon.komoot.io", "api.openrouteservice.org",
    }
    gercek = socket.getaddrinfo

    def coz(host, port, family=0, type=0, proto=0, flags=0):
        if host in alanlar:
            return [(socket.AF_INET, socket.SOCK_STREAM, socket.IPPROTO_TCP,
                     "", ("93.184.216.34", port or 0))]
        if host == "localhost":
            host = "127.0.0.1"
        # AI_NUMERICHOST ag/DNS'e cikmaz; 127.1 ve onluk/hex IP gibi
        # alternatif literal gosterimleri de gercek cozumleyici isler.
        return gercek(host, port, family, type, proto, flags | socket.AI_NUMERICHOST)

    monkeypatch.setattr(socket, "getaddrinfo", coz)
    return coz
