---
kim:    opencode
tarih:  2026-08-24
konu:   sayfa_oku SSRF savunmasi — cozulen IP denetimi
tip:    karar
omur:   sonsuz
kaynak: tools/web_search.py + tests/test_ssrf_korumasi.py
---

Casper'in oncelik listesindeki 5. madde: sayfa_oku'nun SSRF acigi. Eski
koruma URL icinde "localhost"/"127.0.0.1" STRINGINI ariyordu; atlatma
yollari:
- loopback alt agi (127.0.0.2, 127.1.1.1)
- IPv6 ([::1])
- onluk/hex/sekizlik IP gosterimi (2130706433 == 127.0.0.1)
- ozel aglar (10.x, 172.16-31.x, 192.168.x) ve link-local metadata
  (169.254.169.254)
- DNS uzerinden ic IP'ye cozunen domain + kotu sitenin 302 ile ic adrese
  yonlendirmesi

Cozum (`tools/web_search.py`):
- _engelli_ip_nedeni(hostname): getaddrinfo ile TUM cozulen adresler
  ipaddress ozelliklerinden gecer (private/loopback/link-local/reserved/
  multicast/unspecified). Egzotik IP yazimlari cozumleme asamasinda dogal
  olarak yakalanir.
- Port kilidi: yalnizca 80/443 (Ollama 11434 gibi ic servislere kapı kapanir)
- _GuvenliYonlendirme: her redirect adimi yeniden denetlenir; engelli hedefe
  takip etmez.
Eski string-tabanli yasakli liste kaldirildi (yerini tam denetim aldi).

KANIT: 10 yeni test (tests/test_ssrf_korumasi.py, sahte resolver ile
deterministik): loopback alt aglari, IPv6, onluk IP, dort cesit ozel ag,
cozulemeyen host, standart disi port, ftp engellendi; genel adres adres
denetiminden gecti; ic adrese yonlendirme takip edilmedi. Canli kontrol:
6 farkli vektorun hepsi "Guvenlik engeli" dondu. Toplam 381/381 yesil.

Bilinen sinir: DNS-rebinding TOCTOU'su (cozumle fetch arasi IP degisimi)
tam kapatilmaz; klasik getaddrinfo savunmasinin siniri budur — ileride
pinning gerekebilir.
