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
KARAR (Casper onayi, 2026-09-20): DASH'TAN KOMPLE SILINIR.
- Kanitlanan durum: Cloudflare'de IKI hesap var (Google kimligi tek,
  isim degisligi vixrex.app@gmail.com; Cloudflare kayitlari ayri):
  A) 4c47dd4f... — wrangler bagli, TEMIZ yonlendirici canli
     (basak-gate-preview.xpodiumyours.workers.dev, 302 kanitli)
  B) ee78549a... — eski hesap, IKINCI BEYIN burada yayinda
     (basak-gate-preview.deep-baroness-ee7.workers.dev)
- Casper B hesabinda dash > Workers & Pages > basak-gate-preview >
  Settings > Delete ile silecek. Adres olur; tek kalici adres A'daki
  yonlendirici kalir. Silme sonrasi dogrulama: deep-baroness-ee7
  404/DNS donmeli.

### Kalici adres — TAMAMLANDI (2026-09-20, resmi yolla)
- Worker kaynak kodu REPOYA alindi: basak-kapisi/ (wrangler.jsonc +
  src/index.js — 8 satir, beyin YOK). Dash'ta kod durmaz; her degisiklik
  git gecmisinden wrangler deploy ile gider.
- Casper bir kez npx wrangler login ile tarayicidan izin verdi
  (OAuth). Sonraki dagitimlar izinsiz, komutla.
- LabState veri odasi kapanis kaydi RESMI dokumana gore exports'ta
  verildi: dagitim ciktisi "stale_tombstone — Safe to remove" dedi =
  oda zaten KAPALI, kayit bir dahaki dagitimda cikarilacak (dokuman
  boyle soyler; yama degil, dokumanin temizlik adimi).
- KANIT (curl): kalici adres HTTP 302 -> tunel; /lab/ boş (ikinci
  beyin kaldi); tunel 200.
- KALICI ADRES: https://basak-gate-preview.xpodiumyours.workers.dev
  (onceki deep-baroness-ee7 alt adresi hesap gecisinden; yeni adres
  hesap adiyla sabit).
- Tunel adresi degistiginde: basak-kapisi/src/index.js tek satir
  guncellenir + npx wrangler deploy (30 saniye, izin istemez).
- Hedef daha sabit yol: alan adi ekleme veya Workers'un kopruye
  dogrudan proxy'si (siradaki adimda karar).

### Notlar
- trycloudflare adresi oturum sureli: bilgisayar/kopru kapalinca olur.
  Kalicilik icin yukaridaki Worker adimi veya alan adi ekleme gerekir.
- Firewall kurali GEREKMEZ: cloudflared giden baglantiyla calisir.
- Login akisi (argotunnel) iptal edildi — hesapta alan adi yok; o sayfa
  bos listede bekler, kapatildi.
