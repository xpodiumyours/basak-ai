# Başak — Yayın Kayıtları

Yayın = main'e birleşme + tek push (Vercel üretim deployu). Her yayında
tek satır: tarih, commit, kapsam, canlı kanıt.

- 2026-09-29 (öğleden sonra): `cfe572e` — ilk büyük kamu yayını.
  Kapsam: 8 araç genişlemesi + reklam/affiliate zemini + reklam-ver
  sayfası + GitHub PR işleri (fatura/kilo). Canlı kanıt: 921 test +
  29/29 duman; HTTP 200 (/ /araclar araç sayfaları /rehber reklam-ver
  sitemap robots), sitemap 171 URL, /api/kimlik 200.
- 2026-09-29 (gece): `947eda1` — üst kademe paketi (ölçüm + geri bildirim +
  rehberler + IndexNow). Kapsam: `/api/olcum`, `/api/oy`, `olcum.js`,
  4 rehber, IndexNow anahtarı + gönderici, GitHub keşif meta.
  NOT: bu kayıt ilk yazıldığında iş henüz push EDİLMEMİŞTİ; aşağıdaki
  kayıt gerçek yayını belgeler.
- 2026-09-30: `6037703` (merge) — üst kademe paketi + sorumluluk şeffaflığı.
  Kapsam: ölçüm/oy uçları, 4 rehber sayfası, IndexNow, `brain/registry.py`
  veri saklama alanı (15 kart), kimliksiz günlük ölçüm tavanı,
  `/api/saglayici-veri` + gizlilik sayfası tablosu, KVKK envanteri.
  Canlı kanıt: 967 test + 19 atlandı (hata 0); HTTP 200 (`/`, `/araclar`,
  `/rehber`, rehber detay, `gizlilik.html`, `cerez.html`, `sitemap.xml`,
  `robots.txt`, IndexNow anahtarı, `/api/saglayici-veri`), sitemap 176 URL,
  `/api/olcum` 401 (token koruması — kasıtlı), IndexNow gönderimi **202**
  (176 adres alındı, anahtar doğrulaması bekliyor).
- 2026-10-14: `fa2a29f` — kanıt turu (P2.3 + P3.1 + fatura duvarı).
  Kapsam: `/healthz` kimliksiz sağlık ucu (4 test), `/fatura` ekranında
  tarayıcı-içi fotoğraf küçültme (küçültme `web/common.js`te tek yere
  alındı; sohbet ekranı da onu çağırır), `Procfile` + Linux'ta
  `pytest`/`pytest-cov` kurulabilirliği, anahtarsız canlı kabul testi
  (`tests/live/test_canli_site_konusma.py`), plan §8 kaydı.
  Canlı kanıt: `/healthz` **200** `{"ok":true}` (öncesi 404), `/fatura`
  200; **gerçek Chromium + gerçek 8 MP fotoğraf** (ham 5,31 MB / data URL
  7,08 MB → tavan 4,5 MB'ın üstünde) `/fatura` ekranından gönderildi:
  gövde **0,73 MB** (9,7 kat küçültme), okuma `ok=true`
  (`gemini-3-flash-preview`, 63,9 sn), ekranda satıcı VKN 6120729513,
  alıcı VKN 2345678901, fatura no IK-2026-10427, 2 satır, matrah
  54.720,00 / KDV 10.944,00 / genel toplam 65.664,00 ve "Matrah + KDV =
  genel toplam → tutuyor" denetimi. Yerel kapı: 1389 test geçti,
  5 atlandı, 0 kırmızı; ruff + sır kapısı temiz.
  Açık bulgular (canlı koşudan, düzeltilmedi): Base64 + Türkçe harf
  yanlış sonuç; beyaz liste reddi cümlesi ekranda yok; belirsiz yüzde
  sorusu; doğrulanmamış hatırlatıcı iddiası (plan §8.3).
- 2026-10-17: `e787817` (merge) — yarım görev durumu + 58. araç.
  Kapsam: görev kaydına durum alanı (pending/in_progress/paused/done),
  not ve zaman damgaları; yeni `update_task_status` aracı dört noktaya
  işlendi (şema, dağıtıcı, yetenek alanı, durum metni).
  Canlı kanıt: deneme + önizleme adreslerinde uçtan uca 3/3
  (ekle → duraklat+not → listede duraklatıldı görünüyor).
  Yerel kapı: 1377 geçti / 31 atlandı; ruff + sır kapısı temiz.
- 2026-10-17: `2b89658` — proje bağlam temizliği faz-b (denetim sonrası).
  Kapsam: 4 dosya (olmayan klasör sözü mesajdan çıkarıldı, endekse
  3 not eklendi, kilitli talimata tarihsel notlar, terk edilen plana
  başlık). Kod ve canlı işleyiş değişmedi.
  Canlı kanıt: yayın success + site 200.
- 2026-10-21: `1d38f29` — tarayıcı gözü (59. araç) canlıya alındı.
  Kapsam: `tools/tarayici_goz.py` (ham gözlem → numaralı, sayfalanabilir
  öğe listesi; nesle bağlı ref, bayat ref reddi), `tools/tarayici_kopru.py`
  (kişiye bağlı istemci defteri; sohbet sürerken sayfa isteği aynı kanaldan
  cevaplanır), `tools/tarayici_ws.py` (yerel WS köprüsü: anahtar + uzantı
  kaynağı denetimi), `eklenti/` (MV3; içerik betiği gizliyi atlar, şifre
  değerini okumaz, yan panelde sohbet), `basak_web.py` (köprü açılışı;
  panel mesajı `chat.flow.mesaj_isle`).
  Ek düzeltme (`1d38f29` içinde): manifest'e `ws://127.0.0.1/*` izni
  (yoksa yerel kanal sessizce kurulamaz) ve MV3 servis çalışanı için
  20 sn ping (yoksa kanal ~30 sn'de düşer, Başak "bağlı değil" der).
  Yerel kapı: **1439 test geçti / 31 atlandı**; `ruff` gerçek ikiliyle
  temiz (`python -m ruff` PATH'te yoktu, venv'e kurulup koşuldu);
  `node --check` üç betikte temiz; jsdom prova **14/14**.
  Canlı kanıt (push'tan ~100 sn sonra): `/healthz` 200 `{"ok":true}`,
  `/` 200 (7.331 b, başlık "Başak — Sohbet"), `/araclar` 200,
  `/api/durum` 401 (kapı yerinde).
  **Dürüst sınır:** yeni derlemenin içerik düzeyinde canlı olduğu
  doğrulanamadı — `/healthz` sözleşmesi gövdeye sürüm koymayı yasaklıyor,
  oturum açmadan `/api/durum` okunamıyor ve Vercel paneli erişimi yok.
  Eklenti **bugün yalnız yerelde** çalışır. **Düzeltme (2026-10-21):** burada
  önce "Vercel WebSocket tutamaz" yazıyordu, YANLIŞ — Vercel artık WS'i yerel
  destekliyor (public beta, Fluid Compute, tüm planlar). Gerçek engel başka:
  bağlantı fonksiyon azami süresinde kapanır (Hobby 300 sn), tek instance'a
  çivilenir ve sohbet isteği başka instance'a düşebilir; çekirdek sokete
  ulaşamaz. Çözüm ya paylaşımlı depo (Redis/Postgres) + yeniden bağlanma ya da
  Koyeb/Oracle gibi tek kalıcı süreç. Gerçek Chrome'da kurulum bu
  ortamda denenemedi (tarayıcı yok).
  **Açık bulgu:** `preview` dalı `main`den 6 commit geride/ayrık
  (`5131b38`, 38 dosya); §10'daki "preview = main aynası" kuralı bugün
  ihlal durumunda. Zorla eşitleme yapılmadı — içe alma kararı Casper'ın.
- 2026-10-21: `da4acd0` (merge) — önizleme ana dala alındı; **mirror kuralı
  yeniden sağlandı** (main = preview = `da4acd0`, zorlama yok, fast-forward).
  Kapsam: `sube_bul` (marka + konum + yarıçapla OpenStreetMap Overpass'tan
  kayıtlı şubeler), üretilen görselin `/gorsel/{ad}` rotasından çizilmesi ve
  6 dosyadaki sayaç çakışmasının tek gerçeğe göre çözümü. Ajan kataloğu
  **59 → 60 araç**, yetenek alanı **16**; `sayfa_bakis` ile `sube_bul`
  ikisi de kayıtlı, tekrar yok (`validate_registry().ok == True`).
  Yerel kapı: **1477 test geçti / 31 atlandı**; ruff temiz; jsdom **14/14**;
  `node --check` üç betikte temiz.
  **Canlı kanıt (bu kez derleme içeriği de doğrulandı):** `/gorsel/deneme.jpg`
  → **401 `{"error":"giris gerekli"}`** — bu rota yalnız yeni derlemede var;
  eski derlemede FastAPI'nin `{"detail":"Not Found"}` 404'ü dönerdi. Ayrıca
  `/healthz` 200, `/` 200.
  Önceki maddedeki "preview 6 commit ayrık" notu bu merge ile geçersizdir;
  kayıt düzeltilerek değil, eklenerek tutulur.
- 2026-10-21: `b0b9eb0` — eklentinin **bulut kanalı** açıldı (Vercel WS).
  `chat/eklenti_ws.py` (`/api/eklenti`) + `tools/tarayici_kanal.py`:
  sohbet ve sayfa istekleri AYNI WebSocket'ten yürür; model döngüsü
  eklentinin bağlı olduğu instance'ta kalır, instance'lar arası yönlendirme
  gerekmez. `sayfa_bakis` aktif kanal varsa kanalı, yoksa eski yerel köprüyü
  kullanır (geliştirme yolu korunuyor). Eklenti varsayılanı artık
  `wss://basak-vercel.vercel.app/api/eklenti`.
  **Canlı kanıt (yerel süreç YOK):** bu makineden gerçek WSS bağlantısı
  açıldı, panel mesajı gönderildi, cevap aynı soketten geldi:
  `{"ok": true, "sonuc": {"cevap": "Ben Başak, size yardımcı olmak için
  buradayım.", "kaynak": "groq"}}`. Yani sohbet bulutta, eklenti
  protokolüyle koşuyor.
  Yerel kapı: 1511 test geçti / 31 atlandı; ruff temiz; 5 yeni test
  (TestClient WS: panel mesajı → `sayfa_gozlem` aynı soketten gidip döndü).
  **Sınırlar:** Hobby'de bağlantı 300 sn'de kapanır (eklenti yeniden
  bağlanır); tek tur 300 sn'yi aşarsa kesilir; kalıcı disk yok. Sayfa
  gözleminin gerçek Chrome'da uçtan uca denenmesi hâlâ yapılmadı.
- 2026-10-21: `b7f6bcc` — eklentiye **el** (tıklama/yazma) + kopma onarımı.
  `sayfa_tikla` / `sayfa_yaz` (araç sayısı 60 → 62); ref `<nesil>-<kimlik>`
  ile öğenin kalıcı kimliğine bağlandı (süzme sırayı kaydırmıyor). Panel
  her mesajla oturum geçmişini taşır (bulutta kalıcı disk yok).
  Yeniden bağlanma hatası düzeltildi: `if (deneme > 0) return` yüzünden
  ilk başarısız denemeden sonra hiç denemiyordu; artık sınırsız,
  1→30 sn geri çekilme.
  **Canlı kanıt:** bu makineden WSS ile sahte eklenti — `sayfa_gozlem` →
  `sayfa_yaz {sira:11}` → `sayfa_tikla {sira:12}` → cevap (`groq`).
  Kapılar: 1526 test / 31 atlandı; ruff temiz; jsdom eylem 13/13.
- 2026-10-21: onay kapısı + eklenti dağıtımı (`/eklenti.html`).
  Tıklama/yazma artık **panelde onay** ister: kart hedefin adını gösterir,
  Onayla/Vazgeç; "5 dakika sorma" yalnız o sekme için muafiyet verir.
  Panel kapalıysa onay sorulamaz → **eylem yapılmaz** (fail-closed).
  Eylem isteklerinin süresi 90 sn'ye çıktı (onay beklemesi 20 sn'lik
  varsayılana sığmıyordu). Site tarafında `/eklenti.html` kurulum sayfası
  ve `/eklenti/eklenti.zip` (kaynaktan üretilen paket, `test/` hariç);
  sohbet kenar çubuğuna "Tarayıcı eklentisi" bağlantısı eklendi. Bağlı
  istemci yokken araç hatası kurulum adresini taşır.
  Kapılar: pytest 1533 / 31 atlandı; onay akışı node vm ile 6/6
  (onaysız eylem yok, Vazgeç durdurur, panel kapalı = fail-closed).
  **Sınır:** gerçek Chrome'da onay kartının görsel doğrulaması yapılmadı.
  **Ölçülen sınır (aynı gün):** web ekranındaki sohbet eklentiye ULAŞAMAZ.
  `Kanal` yalnız WebSocket isteğinin bağlamında yaşar; web isteği boş
  `KOPRU` görür. Bu yüzden araç hatası "bağlı istemci yok" değil "bu istek
  üzerinden erişilemedi; sohbeti panelden sürdür" der. Canlı kanıt: web
  sohbetine "açık sekmedeki Giriş yap düğmesine bas" yazıldı → cevap
  "eklentiyi kurup bağlanmanız gerekiyor" (kaynak: glm), uydurma yok.
  Kalıcı çözüm: bağlantı kaydını paylaşımlı depoya yazmak (sıradaki iş).
- 2026-10-21: eklenti kurulumu **sohbet ekranına** taşındı (kişiye özel kart).
  `web/eklenti-kart.js` + `#eklentiKarti`: kart bu tarayıcıda eklenti kurulu
  mu diye `chrome-extension://<id>/sinyal.png` ile ölçer (1500 ms sınır;
  cevap yoksa "bildirmedi" der, uydurmaz), "kapat" kararını Başak ID'sine
  göre localStorage'da tutar, kimlik gelince Başak ID'sini yazar.
  Kimlik sabitlendi: manifest'e `key` eklendi → eklenti kimliği her makinede
  aynı (`dpldleggjfdcmddkmmfdijbbojgedmoj`). `web_accessible_resources`
  yalnız Başak adreslerine açık (genel joker yok).
  **Kanıt:** 1537 test / 31 atlandı; kart jsdom 7/7 (kurulu/yok/bilinmiyor/
  kapat/kimlik); onay 6/6; eylem 13/13; ruff temiz.
  **Sınır:** kart "kurulu mu" sorusunu yalnız sabit kimlikli kurulumda
  bilir; eski (key'siz) kurulum farklı kimlik taşır → /eklenti.html SSS'ye
  "kaldır + yeniden yükle" notu eklendi. Gerçek Chrome'da kartın görsel
  doğrulaması yapılmadı.
- 2026-10-21: **canlı kanıt sayfası** (`/durum.html`) + kurulum 4 → 3 adım.
  `web/durum.html` + `web/durum.js`: sayfa KENDİSİNİ ölçer — beyin turu
  (`/api/sohbet`, gerçek cevap + sağlayıcı + süre), araç sayısı ve model
  sağlayıcılar (`/api/durum`), tarayıcı eklentisi kanalı (tarayıcıdan
  `wss://<host>/api/eklenti` el sıkışması — eklentinin kullandığı adres),
  canlı sürüm damgası, cevap akışı ve checkpoint yokluğu. Ölçülemeyen
  satır "yeşil" yazılmaz; "ölçülemedi" yazılır. İkinci beyin/ikinci sağlayıcı
  zinciri yok (AGENTS.md §9: Web Gate = arayüz + köprü + ölçüm ekranı).
  Kayıtlı ölçüm (`web/durum-kabul.json`) canlı DEĞİLDİR; tarihi yazılıdır ve
  canlı araç sayısıyla karşılaştırılır (farklıysa "ölçüm eski" uyarısı).
  `/lab.html` (ölü `/api/matris` ucunu okuyordu) tek kanıt sayfasına
  yönlendirildi; `web/lab.js` silindi. Sohbet ekranının kenar çubuğuna
  "Durum" bağlantısı eklendi.
  **Kurulum 3 adım:** bağlantı zaten kurulumda ve tarayıcı açılışında kendiliğinden
  kuruluyordu (`arka.js` → `baglan()`); "Bağlan" düğmesi yalnız koptuğunda
  gerekiyor. Kart, `/eklenti.html` ve `OKUBENI.md` buna göre yazıldı. Zip artık
  TEK klasör taşıyor (`basak-eklenti/...`): kullanıcı açınca seçilebilir klasör
  bulur, dosyalar dağılmaz. Eklenti sürümü 0.1.0 → 0.2.0.
  Kapılar: pytest 1544 / 31 atlandı; ruff temiz; node --check temiz;
  `tests/test_durum_sayfasi.py` 7 yeni kapı. **Canlı ölçüm (yerel sunucu):**
  beyin turu `kilo` 2,3 sn; 62 araç; eklenti kanalı "Kanal açık"; akış "harf
  harf akıyor"; checkpoint "yok". Canlı Vercel'de de doğrulandı (beynin turu
  `groq` → "7", kanal el sıkışması açık).
  **Sınır:** sayfanın görünümü gerçek Chrome'da gözle doğrulanmadı; ölçüm
  mantığı yerel sunucuya karşı gerçekten koşturuldu (node + DOM taklidi).

- 2026-10-21: `568d08d` + takip commitleri — **kanıt sayfası kendi hatasını
  yakaladı** ve kalıcı kapı kuruldu. Kapsam: `web/durum.js` içinde iki ayrı
  fonksiyon `satirEkle` adını taşıyordu; JavaScript'te ikinci tanım birincisini
  sessizce siler ve sayfa açılır açılmaz "kutu.appendChild is not a function"
  patlaması veriyordu. Yani "çalışıyor mu" diyen sayfa, tam da ölçüm anında
  çöküyordu. Düzeltildi (`isSatirEkle`); sonra hata BILEREK geri konup kapının
  gerçekten yakaladığı kanıtlandı: 5 test kırmızıya döndü.
  **Kalıcı kapı:** `tests/test_durum_js_calisir.py` (6 test) — (a) her web/ ve
  eklenti/ betiği `node --check`; (b) aynı isimli iki fonksiyon taraması
  (sessiz ezme); (c) `web/durum.js` SAHTE TARAYICIDA (mini DOM) gerçekten
  koşturulur: çökerse kırmızı, render edilen satırlar/çalışma özeti kontrol
  edilir. Kapı ağa çıkmaz.
  Ayrıca `/api/calisma` ucu + `tools/calisma.py` (çekirdekten okuyan
  çalışma özeti: yayın kaydı, çalışma notları, fikir tabloları, görevler).
  Kapılar: pytest **1559 geçti / 10 atlandı / 0 hata**; ruff temiz; node
  --check temiz. Canlı ölçüm (yerel sunucu): beyin turu `kilo` 2,1 sn; 62 araç;
  kanal "Kanal açık"; akış "harf harf akıyor"; checkpoint "yok"; çalışma özeti
  6 yayın kaydı + 11 not okundu.

- 2026-10-22: `0f105e7` + `2d25b09` + `0be45fd` (dal `feat/harita-zinciri`,
  henüz main değil) — **Yol A-1 canlı sayaçlar + Yol B-1 kopma kurtarma**.
  Kapsam: çalışma kartında "N komut çalıştırıldı · N sayfa gezildi" sayacı
  (gerçek olaylardan; `toolDone` artık `arac` alanı taşır) + beklenmedik
  akış kesilmesinde iş kaybının kapanması: kesilme işareti + imzalı devam
  kaydı varsa çalışma satırı silinmez, mola ile aynı "Devam et" sunulur;
  kayıt yoksa eski dürüst hata yolu aynen. Mobilde sayaç/düğme kelime
  ortasından kırılması CSS ile düzeltildi (gerçek ekran görüntüsüyle
  yakalandı). Sürüm kilidi app.js?v=26 / chat.css?v=17.
  **Kapılar:** pytest 1658 geçti / 26 atlandı (13 gerçek tarayıcı testi
  bu VM'de ilk kez koştu — Chromium yerel kurulumu `~/pw-deps/KURULUM.md`);
  ruff/py_compile/node --check temiz. Gerçek tarayıcı provası
  (`scripts/olcum/_devam_kanit.py`) 20/20 tutarlı: kopma→"Devam et"→token
  birebir geri gitti, kayıtsız kopmada eski davranış, konsol hatası/
  başarısız istek/taşma yok; görseller `_devam_kanit/`.
  **Canlı ölçüm (Vercel preview, dal adresi):** sürüm damgaları v=26/v=17
  canlıda; uçtan uca canlı kabul (`test_canli_site_konusma.py --live`)
  1 geçti (gerçek konuşma + gerçek araç koşumu) / 1 kırmızı = **bilinen
  açık ürün bulgusu** Base64 yeteneği (§8.3 işi; bu tur dokunmadı, iddia
  da gevşetilmedi); canlı akışta `toolDone.arac` = `list_tasks` /
  `get_reminders` görüldü.
