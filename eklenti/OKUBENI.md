# Başak — sayfa gözü (tarayıcı eklentisi)

Bu eklenti **göz ve bağlantıdır**. Karar vermez, model çağırmaz, sohbet
etmez. Başak'ın beyni Python çekirdeğinde kalır (AGENTS.md §9).

Bugünkü hâli **salt-okunur**: açık sekmeyi okur, Başak'a iletir. Hiçbir
yere basmaz, hiçbir kutuya yazmaz.

## Ne yapar

1. `chrome.sidePanel` ile sağda panel açar: **sohbet** + bağlantı + önizleme.
2. Açık sekmeyi `icerik.js` ile okur: her düğme/bağlantı/kutu/metin,
   rolü + adı + değeri + kapalı mı bilgisiyle.
3. Yerel Başak köprüsüne (`ws://127.0.0.1:8788`) bağlanır.
4. Panelde yazdığın mesaj **çekirdeğe** gider (`chat.flow.mesaj_isle`);
   cevap aynı kanaldan panele döner. Eklentide ikinci beyin yoktur.
5. Başak `sayfa_bakis` aracını çağırdığında gözlem bu kanaldan gider;
   yani sohbet sırasında sayfa isteği aynı bağlantıyı kilitler.

Gizli öğeler gönderilmez, **şifre alanının değeri asla okunmaz**.

## Kurulum (Chrome / Edge)

1. Başak'ı bu bilgisayarda başlat: `basak-web.cmd` (ya da `python basak_web.py`).
   Konsolda şu satırı gör: `Basak eklenti koprusu: ws://127.0.0.1:8788`.
2. Chrome → `chrome://extensions` → sağ üstten **Geliştirici modu** aç.
3. **Paketlenmemiş öğe yükle** → bu `eklenti/` klasörünü seç.
4. Araç çubuğundaki Başak simgesine bas → sağ panel açılır.
5. Panelde **Bağlantı** bölümünü aç → **Bağlan** → rozet `BAĞLI` olur.
6. Panelde yaz: *"bu sayfada ne var, ne yapabilirim?"* — Başak sayfayı kendi
   okur (`sayfa_bakis`), Türkçe anlatır.
7. **Bu sayfayı gör → Gözlem al** → Başak'ın gördüğü ham listeyi gösterir.

Sohbet ayrıca Başak'ın kendi ekranında (`http://127.0.0.1:8787`) da sürer;
üç yüz (panel, web, Telegram) aynı çekirdeği çağırır.

## Anahtar (isteğe bağlı)

`ayarlar.json` içine `"eklenti_anahtari": "uzun-bir-soz"` yazarsan
eklenti aynı anahtarı panelde girmek zorundadır. Anahtar boşsa bağlantı
yalnız 127.0.0.1'e açıktır ve yalnız tarayıcı uzantısı kaynağı kabul edilir
(`chrome-extension://`).

## Sınırlar (dürüst liste)

- **Tıklama/yazma yok.** Bu sürüm yalnız okur. Tıklama ayrı iş (onay kapısı
  ve "gerçekten oldu mu" doğrulaması gerekiyor).
- **Akış yok.** Cevap tek parça gelir; "yazıyor…" görünür ama kelime kelime
  akmaz.
- **Bulutta bugün çalışmaz.** (Düzeltme 2026-10-21: Vercel artık WebSocket'i
  yerel destekliyor — public beta, Fluid Compute, tüm planlar.) Yine de
  bağlantı fonksiyon süresi dolunca kapanır (Hobby: 300 sn), tek bir
  instance'a çivilenir ve sohbet isteği başka instance'a düşebilir. Bu
  yüzden bulut için ya paylaşımlı depo (Redis/Postgres) + yeniden bağlanma,
  ya da Koyeb/Oracle gibi tek kalıcı süreç gerekir. Yerelde çalışır.
- **`chrome://` ve mağaza sayfaları okunamaz** (tarayıcının kendi kısıtı).
- Eklenti, kurulmadan önce açılmış sekmelerde içerik betiğini kendisi
  enjekte eder; yine olmazsa "bu sekme okunamıyor" der, uydurmaz.

## Test

```bash
# jsdom kurulu bir dizinle
NODE_PATH=/yol/node_modules node eklenti/test/gozlem.test.mjs
```

Üç bambaşka sayfa şekli (vitrin, form, panel) aynı `icerik.js` ile okunur;
gizli öğe, şifre sızıntısı, adsız alan kaybı ve site adı gömülü olması
testle yasaklanmıştır. jsdom yoksa betik **kırmızı** çıkar (sessiz geçmez).

Köprünün kendisi Python tarafında `tests/test_tarayici_ws.py` ile ölçülür:
sahte eklenti bağlanır, `sayfa_bakis` uçtan uca çalışır, yanlış anahtar ve
uzantı dışı kaynak reddedilir.
