# WEB KOPRU PLANI — kullaniciya acik sohbet ekrani (plan modu arastirmasi)

Tarih: 2026-09-19 | Yazan: Buffy | Durum: ARASTIRMA TAMAM, kod YOK
On tek kural: AGENTS.md §9 — beyin yalniz cekirdekte; Gate = kopru + ekran.

## 1. SORUNUN CEVABI: MUMKUN MU? EVET — ve yeni mimari GEREKMEZ

Kanıt repoda zaten var: telegram_bot.py ayni cekirdegi (chat/flow.mesaj_isle)
ikinci bir yuzden calistirir ve BasakUI.* olay katarak dizelerini (reply/
bitir/error/thinking) ayiklayip Telegram'a tasir. Web koprusu ucuncu yuzdur
ve AYNI yolu izler:

  tarayici (ekran) ⇄ HTTP koprusu (Python) ⇄ mesaj_isle() ⇄ brain zinciri
                                            ⇄ tools (52 arac, izin katmani)

Yeni ajan dongusu, yeni saglayici zinciri, yeni arac calistirici YOK.
Bu yuzden ikinci-Basak sapmasi burada tekrar edemez: baglanacak tek sey
mesaj_isle'dir; baska bir sey baglanacak yer yoktur.

## 2. KARARLAR (gerekceli)

a) Sunucu katmani: Python stdlib (http.server) + SSE.
   - Yeni bagimlilik YOK (requirements.txt'e dokunulmaz).
   - Kullanici mesaji = POST; BasakUI.parca/bitir/toolStatus/error/thinking
     olaylari SSE olayina dogrudan maplenir (akis dogal tek-yonlu).
   - Kopya: telegram_bot.py'nin olay ayiklayici dongusu.

b) Kosum sekli: ayri script (basak_web.py) — telegram_bot.py ile ayni kalip;
   basak.cmd yanianda basak-web.cmd. Masaustu uygulama kapaliyken de
   web yuzu calisir; ikisi ayni cekirdek dosyalarini kullanir.

c) Erisim kademeleri (varsayilan en dar):
   - VARSAYILAN: 127.0.0.1 (ayni bilgisayarda tarayici) — test ekranin bu.
   - LAN (telefondan): 0.0.0.0 + rastgele token + Windows guvenlik duvari
     kurali — acikca istenirse.
   - Internet: yalniz tunel uzerinden (cloudflared — Casper'in mevcut
     Cloudflare kullanimi; Tailscale alternatif). Duz port yonlendirme YASAK.

d) Guvenlik kapilari (cekirdek degisir, kopyalanmaz):
   - Token dogrulamasi her istekte (rastgele 32 bayt, ayarlar.json'da;
     git'e girmez).
   - Arac izinleri cekirdektekilerdir: salt-okunur/internet otomatik,
     yazma sinirli, SISTEM (ac_uygulama) varsayilan KAPALI — web'den
     gelen istek ayni izin motorundan gecer. Ek katman yazilmaz.
   - Sir asla web yanitina gecmez (ayarlar.json servis edilmez).
   - Audit: her web cagrisi data/audit'e kaynak=web etiketiyle yazilir.
   - Web v1 = yalniz metin; ses (TTS/STT) masaustu yuzde kalir.

e) Test/kullanici ayni ekran: sohbet ekrani herkese aynidir; olcum
   (416 matris) ayri salt-okunur sayfa olur (data/kabul-matrisi.json
   gosteren goruntuleyici). Test araclari kullanici ekranina karismaz.

## 3. KABUL SIRASI (plana bagli, sapmaz)

0. ON KOSUL: kabul planinin Adim 1'i (8/8 native protokol) — kopru
   hazir cekirdege baglanir; bozuk cekirdege kopru kurulmaz.
1. Kopru + ekran: localhost'ta sohbet; dogrudan mesaj_isle kaniti
   (olaylar BasakUI.* izinden gecer) + birim testler.
2. Token + LAN acilimi; uzaktan ayni test.
3. Tunel ile internet; token disi erisimde kapali kalma testi.
4. Kullaniciya acilis: Casper kademeyi acar, her kademe kanitla.

## 4. ARSIV AKTARIMI (2026-09-19, arsiv/feature-basak-web-gate-2-20260919 etiketinden)

### Tasinacaklar (emin emek, dogrudan kullanilir)
- public/styles.css (3.3 KB, oldugu gibi): Inter tabanli temiz sistem —
  shell/topbar/pill/card/chat/bubble/composer/banner siniflari + mobil
  duyarlilik. Yeni yer: web/styles.css. Palet YENIDEN ICAT EDILMEZ.
- public/app/index.html: sohbet ekrani iskeleti (topbar + chat +
  composer + saglik pigili). Faz-5 kabul kutusu CIKARILIR; gerisi aynen.
- public/app.js: balon/gonderme davranisi kalir; iki degisiklikle:
  (1) /api/chat POST yerine /api/sohbet SSE akisi, (2) acceptanceSession
  mantigi tamamen cikar (sahte kabul donemi kalintisi).
- public/lab ekrani + lab.js: 416 matris goruntuleyicisine donusur —
  faz/stage akisi yerine data/kabul-matrisi.json okur (salt-okunur).
- common.js: aynen.

### Alinmayacaklar (nedeniyle)
- src/index.js + wrangler.jsonc Worker'i (basak-gate): `ai` binding +
  LabState Durable Object ikinci-beyin altyapisi kategorisidir; canliya
  ALINMAZ. Arsiv etiketinde kalir.
- Uretimde statik vitrin Worker'i da kurulmaz: ekran, localhost
  Python koprusunden (http.server) servis edilir — tek origin, SSE
  dogal calisir, token tek yerde. Cloudflare arayuzundeki emek
  TUNEL tarafiyla yasar: Zero Trust > Tunnels > DNS (bu kurulum
  zaten Casper'in arayuzunden yapilmisti; aynen kullanilir).

### Ekran dosyalarinin yeni yeri
repo koku > web/ (index.html, app.js, styles.css, common.js, lab.html,
lab.js) — basak_web.py ayni klasorden servis eder; ui/ masaustune
aittir, karismaz.

## 5. BILINEN SINIRLAR

- SSE proxy arkasinda tamponlama yapabilir → tunel secimi buna gore
  (cloudflared SSE'yi dogrudan destekler).
- Ayni anda tek Basin birden fazla yuzden konusmasi: gecmis/hafiza
  cekirdekte ortaktir; cakisma v1'de kabul edilir (kisi kullanimi).
- Web yuzunden gelen yazma araclari (write_file_tool) cekirdek izin
  kurallarina tabidir; LAN/internet kademelerinde Casper istemezse
  ayarlarla daraltilir (cekirdek ayari, kopya degil).
