"""DNS taklidi SSRF kararini atlamaz ve gercek DNS'e cikmaz."""

import socket

import pytest

from tools.web_search import _guvenli_adres


@pytest.mark.usefixtures("sabit_genel_dns")
@pytest.mark.parametrize("adres", [
    "http://127.0.0.1/x", "http://127.1/x", "http://2130706433/x",
    "http://0x7f000001/x", "http://[::1]/x", "http://169.254.169.254/x",
    "http://10.1.2.3/x", "http://localhost/x",
])
def test_ozel_literal_adresler_hala_engelli(adres):
    assert "Guvenlik engeli" in _guvenli_adres(adres)


def test_bilinmeyen_alan_gercek_dns_ile_cozulmez(sabit_genel_dns):
    with pytest.raises(socket.gaierror):
        socket.getaddrinfo("cozulmemeli.invalid", None)


def test_dns_ic_ve_dis_karisiksa_engel_korunur(sabit_genel_dns, monkeypatch):
    def karisik(*args, **kwargs):
        return [
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("93.184.216.34", 443)),
            (socket.AF_INET, socket.SOCK_STREAM, 6, "", ("10.0.0.1", 443)),
        ]
    monkeypatch.setattr(socket, "getaddrinfo", karisik)
    assert "Guvenlik engeli" in _guvenli_adres("https://example.com/x")
