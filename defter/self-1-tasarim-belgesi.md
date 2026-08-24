---
kim:    opencode
tarih:  2026-08-24
konu:   SELF-1 TASARIM BELGESI — sandboxli kendini gelistirme (cifte onayli)
tip:    karar
omur:   sonsuz
kaynak: kilitli hedef + Darwin Godel Machine / AlphaEvolve yaklasimi
---

# SELF-1 — Kendini geliştirme (EN SON FAZ, CIFTE ONAY GEREKTIRIR)

## Durum
TASARIM ASAMASINDA. Kod YOKTUR ve Casper'in acik cifte onayı olmadan
hicbir zaman otomatik baslamaz. Bu belge, planin %100'unde ne anlaşildiğini
netlestirmek icindir.

## Ilke (degismez kural)
"Zeka buyur, yetki buyumez."
Basak kendi algoritmasini dogrudan canlide DEGISTIREMEZ. Her degisiklik
aday olarak uretilir, SANDBOX'ta eski testler + yeni benchmark ile
sinanir, insana sunulur. Onaysiz hicbir aday canliya giremez.

## Onerilen dongu (DGM yaklasimi)
    Basak v(n)
      -> yeni fikir uret (evrim motoru, EVRIM-0 arsivinden)
      -> Basak v(n)-candidate-k
      -> SANDBOX: tum mevcut testler + yeni benchmark
         + guvenlik sondalari (path/junction/SSRF/izin katmani)
      -> gercekten daha iyi mi?
           hayir -> sil
           evet  -> aday arsivine al
      -> CASPER ONAYI -> v(n+1)

## On sartlar (hepsi gerceklesmeden baslamaz)
1. Casper'in CIFTCI ACIK ONAYI (iki farkli oturumda "evet")
2. Python calistirma yasağinin sandbox cercevesinde kaldirilma karari
3. EVRIM-0+ motorunun en az birkac hafta gercek veriyle calismis olmasi
4. Guvenlik sondalarinin (path, SSRF, izin) otomatik benchmark'a girmesi

## Simdiki anlamı
Bu faz planin SONUNDADIR. Oncesindeki her faz (B1..ORKESTRA, EVRIM)
SELF-1 olmadan da tam degerdir — Basak zaten hafizasi, olcu disiplini,
araclari ve izli orkestrasiyla calisan bir sistemdir.
