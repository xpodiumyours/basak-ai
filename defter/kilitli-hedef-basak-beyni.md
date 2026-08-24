---
kim:    opencode
tarih:  2026-08-24
konu:   KILITLI HEDEF — Basak kendi beyni, modeller hesaplama iscisi
tip:    karar
omur:   sonsuz
kaynak: mimari analiz + bosluk analizi + Casper'in kilit karari
---

CASPER'IN KILIDI: "Bu planı kilitle ve hedeften sapmadan tamamlamaya
özenle devam edeceğiz."

HEDEF TANIMI (tek cümle):
Basak = kendi muhakeme algoritmasi olan bagimsiz beyin;
Groq/Kilo/NVIDIA/gibi free modeller yalnizca ucretsiz hesaplama iscisi.

MEVCUT TAMAMLANMA: ~%25 (altyapi agirlikli)

| # | Bilesen | Bugun | Hedef |
|---|---|---|---|
| 1 | Problem Compiler | %0 | istek -> amac/olcut/kisit/hipotez alani |
| 2 | Hipotez Havuzu (ToT) | %0 | paralel aday uretimi, dallanma |
| 3 | Saldırgan roller (FAY) | ~%20 | FAY-MOTORU.md tasarimi hazir, kod yok |
| 4 | Deney Motoru | ~%15 | olcum araclari var; otomatik deney dongusu yok |
| 5 | Evrim Motoru + Arsiv | %0 | nufus arsivi, capraz birlestirme |
| 6 | Dunya Modeli | ~%30 | bayat+karne+defter yapisal; grafik/belief store yok |
| 7 | Meta-ogrenme secici | ~%10 | stats birikiyor; secici OKUMUYOR |
| 8 | Compute Manager | ~%25 | gercek token sayimi canli; butce dagitimi yok |
| 9 | Sandboxli kendini gelistirme | %0 | bilinclì olarak en son; cift onayli |
| 10 | 10-durumlu orkestrator (OBSERVE..LEARN) | %0 | mevcut akis linear |

KILITLI SIRA (her faz kanit kapili; duraklar korunur):

| Faz | Is | Oncul |
|---|---|---|
| **B1** | Secici <-> karne/stats baglantisi (meta-ogrenmenin ilk halkasi); once/sonra taban olcumuyle kanit | stats, token sayimi |
| **B2** | Borclar: baglam diyeti Adim 2 temiz provasi + Kilo kullanim olcumu | - |
| **B3** | kota.py gercek token butcesine gecis (80-istek tahmini kaldirilir) | B1'in verisi |
| **DENEY-0** | Deney motoru tohumu: hipotez->olcut->calistir->rapor sablonu; salt-okunur; guvenlik kurallari aynen | olcum araclari |
| **FAY-0..3** | Saldigan rollerin ilk gercek kurulusu (tanik/juri/celiski/gerilim) | DENEY-0 |
| **DUNYA-0** | bayat/karne/defter -> sorgulanabilir belief store | FAY verisi |
| **ORKESTRA-0** | Mevcut linear akisi OBSERVE..LEARN dongusune ceviren iskelet | DENEY-0, DUNYA-0 |
| **EVRIM-0+** | Hipotez havuzu + nufus arsivi + kombinasyon | ORKESTRA-0, DENEY-0 olgunlugu |
| **SELF-1** | Sandboxli kendini gelistirme | EVRIM olgunlugu + Python calistirma karari + CIFTCI Casper onayi |

BAGLAYICI ILKELER (degismez):
- "Zeka buyur, yetki buyumez."
- Ucretsiz kal; ucretli varsayilan kapali.
- Her faz kanit kapili; sapma ancak Casper karariyla.
- UX-K2 Cekirdek gorunumu bu planin GORUNTUSUDUR — muhakeme motoru
  varken anlam kazanir; onune gecmez.
