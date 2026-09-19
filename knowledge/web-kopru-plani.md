<!-- ek: 2026-09-20 TUNEL + ESKI WORKER KARARI (Buffy, Casper onayli) -->

## 6. BUGUNUN DURUMU (2026-09-20): TUNEL ACIK — ESKI WORKER KAPATILACAK

### Canli kanit (localhost + tunel)
- Kopru: basak_web.py 8787'de calisiyor; ekran web/ klasorunden.
- Tunel: cloudflared (winget, 2026.9.1) ile acildi:
  https://laptop-lawyer-blend-periodic.trycloudflare.com
  Kanit: ekran HTTP 200, /api/matris tokensuz HTTP 401 (guvenlik kapisi
  internetten de gecerli).
- Token: ayarlar.json "web_token" (git'e GIRMEZ); ekran ilk istekte
  bir kez sorar, localStorage'da tutar (common.js basakToken).

### ESKI WORKER (basak-gate-preview) — IKINCI BEYIN, KAPATILACAK
Casper 3 ekran resmiyle dogruladi: basak-gate-preview.deep-baroness-ee7
.workers.dev HALA YAYINDA (HTTP 200, "kalici web kapisi" vitrini) ve
lab ekraninda kendi itirafi yaziyor: "gercek tool_call -> GUVENLI SAHTE
tool sonucu" + 7 saglayici "BAGLI DEGIL". Bu, temizlikten kacan ikinci
beyindir — repoda degil, CLOUDFLARE HESABINDA yasiyordu.
KARAR (Casper onayli): Worker SİLİNMEZ; ADRES KORUNUR. Adimlar:
1. Casper Cloudflare dash > Workers & Pages > basak-gate-preview >
   Settings > wrangler.toml/icerik: yalniz EKRAN dosyalari (web/)
   + tum istekleri http://127.0.0.1:8787'ye yonlendiren boylece
   beyinsiz boru. Durable Object / LabState / sahte faz mantigi silinir.
   Ya da tamamen bos sayfa + yonlendirme.
2. Boylece sohbet ekranina ulasim KALICI adresle devam eder (Casper'in
   istegi: "erisim kalici olmali"), yeni yapi KURULMAZ.
3. Alternatif (alan adi ister): cloudflared tunnel login + named
   tunnel — hesapta alan adi olmadigi icin su an uygulanamaz.

### Kalici adres yolu (siradaki adim)
- Hesabin workers.dev adresi KALICIDIR (trycloudflare gecicidir —
  kapanirsa yeniden acilir, adres degisir).
- Casper'dan istenen: Workers dash'ta basak-gate-preview'in icerigini
  beyinsiz boruya cevirmek (Bu islem Casper'in dash erisimiyle yapilir;
  ajan API anahtari olmadan dash'a dokunmaz.)

### Notlar
- trycloudflare adresi oturum sureli: bilgisayar/kopru kapalinca olur.
  Kalicilik icin yukaridaki Worker adimi veya alan adi ekleme gerekir.
- Firewall kurali GEREKMEZ: cloudflared giden baglantiyla calisir.
- Login akisi (argotunnel) iptal edildi — hesapta alan adi yok; o sayfa
  bos listede bekler, kapatildi.
