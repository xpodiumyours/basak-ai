# Başak — sayfa gözü (tarayıcı eklentisi)

Bu eklenti **göz ve bağlantıdır**. Karar vermez, model çağırmaz, sohbet
etmez. Başak'ın beyni Python çekirdeğinde kalır (AGENTS.md §9).

Bugünkü hâli **göz + el**: açık sekmeyi okur, Başak'a iletir; Başak
istediğinde görünen bir öğeye tıklar ve yazılabilir alana yazı yazar.
Kural: görünmeyen, kapalı (disabled), kopmuş öğeye eylem yok; **şifre ve
dosya alanına yazma yok**.

## Ne yapar

1. `chrome.sidePanel` ile sağda panel açar: **sohbet** + bağlantı + önizleme.
2. Açık sekmeyi `icerik.js` ile okur: her düğme/bağlantı/kutu/metin,
   rolü + adı + değeri + kapalı mı bilgisiyle.
3. **Buluttaki** Başak'a bağlanır:
   `wss://basak-vercel.vercel.app/api/eklenti` (2026-10-21'den itibaren
   varsayılan). Yerel geliştirme için panel alanına
   `ws://127.0.0.1:8788` yazılabilir. Sohbet ve sayfa isteği AYNI
   bağlantıdan gider; model döngüsü o bağlantının instance'ında kalır.
4. Panelde yazdığın mesaj **çekirdeğe** gider (`chat.flow.mesaj_isle`);
   cevap aynı kanaldan panele döner. Eklentide ikinci beyin yoktur.
5. Başak `sayfa_bakis` aracını çağırdığında gözlem bu kanaldan gider;
   yani sohbet sırasında sayfa isteği aynı bağlantıyı kilitler.

6. Başak `sayfa_tikla` / `sayfa_yaz` araçlarını çağırdığında eylem aynı
   kanaldan gider. Her öğenin sayfa ömrü boyunca sabit bir kimliği vardır;
   Başak'ın ref'i `<nesil>-<kimlik>` olur. Sayfa yenilenmişse eski ref
   reddedilir — yanlış düğmeye basılmaz.

Gizli öğeler gönderilmez, **şifre alanının değeri asla okunmaz**.

## Kurulum (Chrome / Edge) — 3 adım

1. **Zip'i indir ve aç** → içinden `basak-eklenti` klasörü çıkar.
2. Chrome → `chrome://extensions` → **Geliştirici modu** → **Paketlenmemiş öğe
   yükle** → `basak-eklenti` klasörünü seç.
3. Araç çubuğundaki Başak simgesine bas → sağ panel açılır. **Bağlantı
   kendiliğinden kurulur** (kurulumda ve tarayıcı açılışında); rozet `BAĞLI`
   olur. Paneldeki **Bağlan** düğmesi yalnız bağlantı kopmuşsa gerekir.

Başak sitesinde **giriş yapmış olmak** yeterlidir (eklenti oturum çerezini
kullanır; çerez yoksa ziyaretçi olarak bağlanır ve kişisel hafıza açılmaz).

Panelde yaz: *"bu sayfada ne var, ne yapabilirim?"* — Başak sayfayı kendi
okur (`sayfa_bakis`), Türkçe anlatır. "Şu kutuya adımı yaz, Kaydet'e bas"
gibi bir iş istersen önce bakar, sonra tıklar/yazar.
**Bu sayfayı gör → Gözlem al** → Başak'ın gördüğü ham listeyi gösterir.

Sohbet ayrıca Başak'ın kendi ekranında (`http://127.0.0.1:8787`) da sürer;
üç yüz (panel, web, Telegram) aynı çekirdeği çağırır.

## Anahtar (isteğe bağlı)

`ayarlar.json` içine `"eklenti_anahtari": "uzun-bir-soz"` yazarsan
eklenti aynı anahtarı panelde girmek zorundadır. Anahtar boşsa bağlantı
yalnız 127.0.0.1'e açıktır ve yalnız tarayıcı uzantısı kaynağı kabul edilir
(`chrome-extension://`).

## Sınırlar (dürüst liste)

- **Onay her eylemde sorulur.** Kart hedefin adını gösterir; "5 dakika
  sorma" işaretlenirse yalnız o sekme için muafiyet verilir. **Panel
  kapalıysa onay sorulamaz ve eylem yapılmaz** (fail-closed).
- **Eylem sonrası doğrulama modelin işi.** Tıklama/yazma "yapıldı" der ve
  sayfanın yeni adını döner; sonucu görmek için Başak yeniden bakar.
- **Mağaza yok.** Kurulum zip + "paketlenmemiş öğe yükle" ile yapılır;
  güncelleme el ile. Kurulum sayfası: `/eklenti.html`, paket:
  `/eklenti/eklenti.zip`.
- **Panel şartı.** Sayfayla ilgili işler paneldeki sohbetten yürür; bulutta
  web ekranındaki sohbet eklentinin bağlantısına erişemez (farklı instance).
  Bu durumda araç "bu istek üzerinden erişilemedi" der, uydurmaz.
- **Akış yok.** Cevap tek parça gelir; "yazıyor…" görünür ama kelime kelime
  akmaz.
- **Bulutta çalışır** (2026-10-21 canlı ölçüm: `wss://basak-vercel.
  vercel.app/api/eklenti` → gerçek cevap, sağlayıcı `groq`). İki sınır var:
  bağlantı fonksiyon süresi dolunca kapanır (Hobby: 300 sn) ve eklenti
  yeniden bağlanır; tek tur 300 saniyeyi aşarsa kesilir. Kalıcı disk yok,
  bu yüzden geçmiş istek gövdesiyle taşınır.
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

Tıklama/yazma ayrıca `eklenti/test/eylem.test.mjs` ile ölçülür: gerçek
tıklama, input/change olayları, şifre reddi, kopmuş öğe ve adres değişimi.

```bash
NODE_PATH=/yol/node_modules node eklenti/test/eylem.test.mjs
```

Köprünün kendisi Python tarafında `tests/test_tarayici_ws.py` ile ölçülür:
sahte eklenti bağlanır, `sayfa_bakis` uçtan uca çalışır, yanlış anahtar ve
uzantı dışı kaynak reddedilir.
