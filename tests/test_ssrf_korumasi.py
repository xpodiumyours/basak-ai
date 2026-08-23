"""tests/test_ssrf_korumasi.py — sayfa_oku SSRF savunması testleri.

2026-08-24'te Casper'in bulgusu: eski koruma yalnızca URL içinde
"localhost"/"127.0.0.1" stringini arıyordu; 127.0.0.2 gibi loopback alt ağı,
[::1], onluk/hex IP gösterimleri, özel ağlar ve iç IP'ye çözünen domain'ler
geçiyordu.

Yeni kural: hostname COZULUR (getaddrinfo), tüm çözülen IP'ler özel/
loopback/link-local/rezerve ise engellenir; yalnız 80/443 portları;
her yönlendirme adımı yeniden denetlenir.
"""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import pytest

from tools import web_search as ws


def _sahte_resolver(harita):
    """host->ip haritasına göre sahte getaddrinfo üretir."""

    def sahte(host, *a, **kw):
        ip = harita.get(host)
        if ip is None:
            import socket
            raise socket.gaierror(11001, "cozulemedi")
        return [(2, 1, 6, "", (ip, 0))]

    return sahte


@pytest.fixture
def resolver(monkeypatch):
    def kur(harita):
        monkeypatch.setattr(ws.socket, "getaddrinfo", _sahte_resolver(harita))
    return kur


class TestEngelliAdresler:
    def test_loopback_alt_aglari_engellenir(self, resolver):
        resolver({"127.0.0.2": "127.0.0.2", "127.1.1.1": "127.1.1.1"})
        for url in ("http://127.0.0.2/x", "http://127.1.1.1/x"):
            r = ws.sayfa_oku(url)
            assert r.get("error") and "Guvenlik engeli" in r["error"], url

    def test_ipv6_loopback_engellenir(self, resolver):
        resolver({"::1": "::1"})
        r = ws.sayfa_oku("http://[::1]/api")
        assert "Guvenlik engeli" in r.get("error", "")

    def test_onluk_ip_gosterimi_engellenir(self, resolver):
        # 2130706433 == 127.0.0.1 (inet_aton semantigi)
        resolver({"2130706433": "127.0.0.1"})
        r = ws.sayfa_oku("http://2130706433/")
        assert "Guvenlik engeli" in r.get("error", "")

    def test_ozel_aglar_engellenir(self, resolver):
        resolver({
            "dahili.local": "192.168.1.10",
            "sunucu.local": "10.0.0.5",
            "yazici.local": "172.16.5.4",
            "meta.local": "169.254.169.254",
        })
        for host in ("dahili.local", "sunucu.local", "yazici.local",
                     "meta.local"):
            r = ws.sayfa_oku("http://%s/admin" % host)
            assert "Guvenlik engeli" in r.get("error", ""), host

    def test_cozulemeyen_host_engellenir(self, resolver):
        resolver({})   # hicbir sey cozulmez
        r = ws.sayfa_oku("http://olmayan-domain-xyz.example/")
        assert r.get("error")


class TestPortVeSemantik:
    def test_standart_disi_port_engellenir(self, resolver):
        resolver({"ornek.test": "93.184.216.34"})
        r = ws.sayfa_oku("http://ornek.test:11434/api")
        assert "port" in r.get("error", "")

    def test_ftp_engellenir(self):
        assert "http/https" in ws.sayfa_oku("ftp://site/x")["error"]

    def test_bos_url(self):
        assert ws.sayfa_oku("")["error"]


class TestIzinliYol:
    def test_genel_adres_adres_denetiminden_gecer(self, resolver):
        """Genel IP cozen adres 'guvenlik engeli' YEMEDEN ilerler
        (ag yokken baglanti hatasi beklenir — bu da engel degil)."""
        resolver({"genel.example": "93.184.216.34"})
        r = ws.sayfa_oku("http://genel.example/")
        hata = r.get("error", "")
        assert "Guvenlik engeli" not in hata


class TestRedirect:
    def test_yonlendirme_ic_adrese_takilmaz(self, resolver):
        """Kotu site genel IP'den ic adrese yonlendirirse ikinci adim
        engellenmelidir."""
        resolver({"kotu.site": "93.184.184.34",
                  "dahili.local": "10.9.9.9"})
        handler = ws._GuvenliYonlendirme()
        sonuc = handler.redirect_request(None, None, 302, "taşındı", {},
                                         "http://dahili.local/gizli")
        assert sonuc is None   # takip edilmez
