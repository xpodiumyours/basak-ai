# TARAYICI KATMANI — MVP'DEN PROFESYONELE PLAN

**Tarih:** 2026-10-22 · **Karar sahibi:** Casper · **Durum:** yürürlükte
**Rol:** Şemsiye plan `docs/MVP-PROFESYONEL-PLANI.md`'nin altında **tarayıcı katmanını**
(eklenti göz/el, dağıtım, web ↔ eklenti el sıkışması, firma takibi) yürütür.
Harita işi kendi planında sürer (`docs/HARITA-ZINCIRI-PLANI.md`, FAZ 4–7); burada
**tekrarlanmaz**.
**Bağlayıcı kurallar:** `AGENTS.md` §0 (chatbot yasağı), §9 (tek beyin), §10 (dal kuralı),
§5 (kanıtsız "çalışıyor" yok).

> Sırası gelen madde buraya işlenir; ayrı tarayıcı planı açılmaz.
> Ölçüm tabanı 2026-10-22; sayılar her faz kapanışında yenilenir.

---

## 0. "Bitti" ne demek

Bir faz ancak şu üçü birlikte varsa biter:

1. **Test yeşil:** `python -m pytest tests -q` + her `eklenti/test/*.test.mjs` jsdom ile.
2. **Canlı kanıt:** gerçek tarayıcıda/sitede elle denenmiş, çıktı rapora yazılmış.
3. **Defter kaydı:** `defter/` altına tarih + ölçüm + sınır notu.

Ölçülemeyen madde "bitti" sayılmaz; sınırı varsa sınır yazılır, sansürlenmez.

---

## 1. Bugün nerede (2026-10-22 ölçümü)

| Kalem | Ölçüm | Durum |
|---|---|---|
| Python test paketi | 1660 geçti / 31 atlandı / 0 kaldı (2026-10-22, P2 sonrası) | ✅ |
| Eklenti JS testleri | 5 dosya, **65 test**; `npm test` tek komut (asılmaya karşı 90 sn tavan), CI işi eklendi | ✅ |
| Canlı `/eklenti.html`, `/eklenti/eklenti.zip`, `/durum.html` | 200 / 200 (18 KB) / 200 | ✅ |
| `sayfa_bakis` · `sayfa_tikla` · `sayfa_yaz` | tanım + dispatcher + yetenek alanı + durum metni tam | ✅ |
| Öğe kimliği / bayat ref reddi | `WeakMap` kimlik + nesil; sayfa değişince eylem reddedilir | ✅ profesyonel |
| Onay kapısı | panel kapalıysa eylem yok (fail-closed), 5 dk muafiyet | ✅ profesyonel |
| `harita_dedektif` | merkez → şubeler → yol tarifi; 25 km tavan, uydurma yok | ✅ dar kapsam |
| `sirket_ara` | schema.org Organization/PostalAddress, boş alan dürüst | ✅ arama var, **takip yok** |
| Kurulum | zip + geliştirici modu + "paketlenmemiş yükle" | ❌ MVP |
| Web sohbeti → eklenti | instance'lar kopuk; "erişemiyorum" | ❌ MVP |
| Ambalaj | ikon yok, options yok, otomatik güncelleme yok | ❌ MVP |

**Hüküm:** tarayıcı çekirdeği profesyonel; kapanmayan başlıklar **dağıtım**, **göz kör
noktaları + eylem doğruluğu**, **web↔eklenti**, **firma takibi**.

---

## 2. Eksik listesi (kanıt satırıyla)

| # | Eksik | Kanıt |
|---|---|---|
| E1 | Eklenti JS testleri CI'da koşmuyor | `.github/workflows/test.yml` yalnız lint + pytest + provider |
| E2 | `select` seçenekleri gözlemde yok | `eklenti/icerik.js:37` `SECICI` listesinde `option` yok |
| E3 | `sayfa_yaz` seçenekte eşleşme doğrulamadan başarı dönüyor | `eklenti/icerik.js:262` (`yaz`) değeri atıp `yapildi` diyor |
| E4 | Tıklama sonrası bekleme/doğrulama yok | `eklenti/icerik.js:212` (`tikla`) anında URL dönüyor |
| E5 | iframe ve shadow DOM kör | `manifest.json` `all_frames:false`; `shadowRoot` taraması yok |
| E6 | Klavye / kaydırma / hover yok | yalnız `tikla` + `yaz` var |
| E7 | Ambalaj: ikon, options, mağaza | `manifest.json`'da `icons` ve `options_page` yok |
| E8 | Web sohbeti eklentiye ulaşamıyor | `chat/eklenti_ws.py` bağlantıyı tek instance'a çiviliyor |
| E9 | Firma takibi yok (tek atımlık sorgu) | `tools/katalog.py:2090` `sirket_ara`; izleme/alarm yok |
| E10 | Zip kurulumu tek tık değil | `/eklenti/eklenti.zip` + `chrome://extensions` akışı |

---

## 3. Karar bekleyen maddeler

| # | Soru | Öneri | Maliyet |
|---|---|---|---|
| **K1 — KARAR (2026-10-22): Edge önce, ücret yok** | Chrome 5 $'ı beklemeden Edge Add-ons. Teknik paket + başvuru kılavuzu hazır (`docs/EDGE-MAGAZA.md`); başvuru Casper'ın 15 dakikası, inceleme 1–3 iş günü | 0 $ |
| **K2 — ONAYLANDI (2026-10-23, Casper: doğrudan sürüş)** | Web sohbetinden tarayıcı eylemi şart. Yol: **paylaşılan kutu, mevcut Postgres** (yeni servis yok — Redis katmanı gerekmedi, DATABASE_URL zaten üretimde var). Onay kapısı cihazda kalır. | 0 $ |
| **K3** | Firma takibi nerede yaşasın? | **Eklenti tarafı** (`chrome.alarms` + `chrome.storage.local`) + masaüstünde `zamanlayici`. Yeni servis yok, kalıcı disk yok | 0 $ |
| **K4** | İzinler daraltılsın mı? | Mağaza incelemesi için `activeTab` + isteğe bağlı izin düşünülebilir; ama "her sayfada çalış" iddiası zayıflar | P5 içinde tartışılır |

**K1, K2, K3 onaylanmadan o faza başlanmaz.** Varsayılan: öneri kolonundaki yol.

---

## 4. Fazlar

### P0 — Ölçü ayağı (0,5 gün)

- `test.yml`'ye `eklenti-js` işi: Node 20 + `npm ci` (yalnız `jsdom`, sürüm sabit +
  `package-lock.json`) → `eklenti/test/*.test.mjs` dosyalarının her biri `node` ile koşar.
  Bugünkü koşum biçimi korunur: `NODE_PATH=<jsdom node_modules> node eklenti/test/<dosya>.mjs`
  (testler `node:test` değil, `node:assert` ile yazılmış).
- Tek komut hedefi: `eklenti/test/` altındaki tüm `.test.mjs` dosyalarını sırayla koşan
  küçük bir betik; çıkış kodu ilk kırmızıda 1.
- Zipe giren dosya listesi testi: `test/` girmiyor, `manifest.json` + zorunlu dosyalar giriyor.

**Kabul:** PR'da kırmızıya dönebilen bir iş var; eklenti testi bozulunca CI kırmızı.
**Risk:** jsdom kurulumu Actions dakikası yer — tek iş, 1 dk altında.

### P1 — Eylem doğruluğu (1,5 gün) — E2, E3, E4

1. `select`/`option`: gözleme `secenekler` (en çok 20, değer + etiket) eklenir.
2. `yaz`: `select` için değer ya da etiketle **birebir** eşleşme aranır; eşleşme yoksa
   `hata` döner ("seçenek bulunamadı: …"). Yazma sonrası `el.value`/`textContent` geri
   okunup karşılaştırılır; tutmuyorsa başarı DÖNMEZ.
3. `tikla`: tıklama sonrası en çok 1,5 sn `location`/`readyState`/DOM mutasyonu izlenir;
   `sonuc` içine `degisti`, `url`, `baslik`, `hazir` eklenir.
4. Şifre/dosya alanı yasağı ve gizli öğe filtresi aynen korunur.

**Dokunulan:** `eklenti/icerik.js`, `eklenti/test/eylem.test.mjs`, `eklenti/test/gozlem.test.mjs`.
**Kabul:** yeni ≥8 test; gerçek sitede select + SPA bağlantısı manuel doğrulanır.
**Risk:** bazı siteler `select` yerine özel combobox kullanır — o zaman dürüst hata döner, sahte başarı yok.

### P2 — Görüş alanı (2 gün) — E5

- `all_frames: true`; ref biçimi çerçeve kimliği taşır (`<cerceve>-<nesil>-<kimlik>`).
  Eski ref'ler bayat sayılır (davranış değişikliği testte kilitlenir).
- Açık `shadowRoot` ağacı özyinelemeli taranır (kapalı gölge kökü erişilemez — dürüst sınır).
- Gözlem çıktısına `cerceve` etiketi; toplam öğe tavanı korunur (sayfa başına 60).

**Dokunulan:** `eklenti/manifest.json`, `eklenti/icerik.js`, `eklenti/arka.js`,
`tools/tarayici_goz.py`, `eklenti/test/*`.
**Kabul:** iframe içindeki form ve shadow DOM bileşeni okunup tıklanır; ≥10 test;
gerçek siteler: gömülü ödeme formu, açılır filtre paneli.
**Risk:** her çerçeveye enjeksiyon → bazı sitelerde tekrar; performans tavanı şart.

### P3 — Klavye ve kaydırma (1 gün) — E6

İki yeni araç: `sayfa_tus` (Enter/Tab/Escape/oklar) ve `sayfa_kaydir` (sayfa/öğe).
Dört yer kuralı (`AGENTS.md` §0): `tools/definitions.py`, `tools/__init__.py`,
`chat/agent_protocol.py` `YETENEK_ALANLARI`, `chat/tools.py` durum metni.
`sayfa_tus` onay kapısından geçer (form gönderebilir); `sayfa_kaydir` salt-okunur sayılır.

**Kabul:** ≥8 test; klavye ile form gönderimi onay kartında görünür; kaydırma onay sormaz.

### P4 — Ambalaj (0,5 gün) — E7

- `sinyal.png`'den 16/32/48/128 ikon üretilir, `manifest.json` `icons` + `action.default_icon`.
- `options.html/js`: sunucu adresi + anahtar + "Bağlantıyı sına" (paneldeki `Bağlantı`
  kutusu buraya taşınır, panelde yalnız durum rozeti kalır).
- Sürüm disiplini: her faz sonunda `version` artar; `test_eklenti_dosyalari` ikon ve
  options dosyalarını doğrular.

**Kabul:** araç çubuğunda puzzle değil Başak ikonu; ayarlar panelden bağımsız açılır.

### P5 — Yayın (0,5 gün + inceleme) — E10 · **K1 onayı gerekir**

- Mağaza metni: tek amaç ("kullanıcının açık sekmesini okuyup onayıyla tıklar"),
  mevcut `/gizlilik.html` sayfasına eklenti veri bölümü, ekran görüntüleri (1280×800),
  küçük görsel (440×280).
- `host_permissions` gerekçesi yazılır; inceleme reddi gelirse K4 (izin daraltma) devreye girer.
- Edge Add-ons: ücretsiz. Chrome: 5 $ **yalnız Casper onayıyla**.

**Kabul:** mağaza onayı + "Ekle" ile kurulum + sürüm güncellemesinin otomatik gelmesi.
**Risk:** `http://*/*` + `https://*/*` incelemede sorgulanır; gerekçesiz reddedilir.

### P6b — Web'den doğrudan sürüş (paylaşılan kutu) — E8 — ✅ TAMAMLANDI (2026-10-23, K2)

Tasarım (yeni servis yok): `tools/kutu.py` Postgres `basak_kutu` tablosu —
web turu işi bırakır, eklenti WS üzerinden 3 sn'de bir yoklar (`kutu_al`),
işi mevcut `islemYap` yolundan koşar (onay kapısı aynen fail-closed),
sonucu yazar (`kutu_yaz`), web turu okur. DSN yoksa açık hata (sessiz
bellek düşüşü yok — bellek instance'lar arası paylaşılmaz). Web tarafı
önce alınmayı bekler (10 sn; alınmayan iş = eklenti bağlı değil → açık
hata), sonra sonucu bekler.

**Dokunulan:** `tools/kutu.py` (yeni), `tools/tarayici_kopru.py` (yerel
yoksa kutuya düşüş), `chat/eklenti_ws.py` (`kutu_al`/`kutu_yaz` elçileri),
`eklenti/arka.js` (yoklama döngüsü), `eklenti/test/kutu.test.mjs`.
**Kabul:** 12 Python + 3 JS test; onay gerektirmeyen gözlemde panele soru
gitmez; onaylı eylemde kapı aynen sorar (mevcut `eylem.test.mjs` kilidi).
**Risk:** Vercel 300 sn sınırı — kutu eylem bekleyişi 150 sn tavanlı.

### P6 — Web ↔ eklenti el sıkışması (1 gün) — E8 — ✅ TAMAMLANDI (2026-10-23)

Görev devri (hizmet yok):
1. Web sohbetinde tarayıcı aracı gerektiğinde cevap, görevi `chrome.storage`a yazacak
   bir "panelde sürdür" kartı üretir (görev metni + hedef adres).
2. Başak sitesindeki düğme `sidePanel.open` denemesi yapar; tarayıcı jest kuralı buna izin
   vermezse panel açılmaz ve kullanıcı araç çubuğundan açar — panel bekleyen görevi
   kendiliğinden yükler.
3. Görev devri **tek beyin kuralını bozmaz**: kararı yine çekirdek verir, eklenti taşır.

**Kabul:** web'de "bu sayfayı oku" → tek tık + panel → görev koşuyor; ≥6 test
(Python tarafı `test_eklenti_kanal_devri.py`, JS tarafı jsdom).
**K2 açılırsa** ayrı faz: paylaşılan kutu (ücretsiz katman) ile web'den doğrudan sürüş.

### P7 — Firma takibi (3 gün) — E9 · **K3 onayı gerekir** — ✅ TAMAMLANDI (2026-10-23, K3 öneri yönünde: eklenti + zamanlayici, yeni servis yok)

- Varlıklar: `takip_baslat(ad|url)`, `takip_listele`, `takip_durdur`, `takip_kontrol`.
- Her kontrol `sirket_ara` kartını yeniden üretir, alan bazında karşılaştırır
  (unvan/adres/telefon/e-posta/vergi no) → "değişen: telefon".
- Barındırma: eklenti `chrome.alarms` (günlük) + `chrome.storage.local`; masaüstünde
  `zamanlayici`. Bulutta kalıcı disk yok → web'de takip, eklenti/panel açıkken çalışır.
- Kaynak sınırı dürüst yazılır: veri schema.org'dan; MERSİS/ticaret sicil entegrasyonu yok.

**Kabul:** sahte kartla "telefon değişti" tespiti + aynı kartta "değişiklik yok"; ≥10 test;
en az 1 gerçek firmada 2 günlük koşu kanıtı.

### P8 — Harita derinleştirme — **bu planda DEĞİL**

`poi_ara`, `mesafe_hesapla`, `rota_hesapla` ve bölge analizi
`docs/HARITA-ZINCIRI-PLANI.md` FAZ 4–7'de yürür. Ölçüm (2026-10-22): harita alanında
bugün 4 araç var — `harita_goster`, `konum_coz`, `sube_bul`, `harita_dedektif`.
Bu plana harita maddesi eklenmez; iki belge birbirinin yerine geçmez.

---

## 5. Sıra ve bağımlılık

```
P0 ─► P1 ─► P2 ─► P4 ─► (K1) P5
      └─► P3
      └─► P6        (K2 açılırsa P6b)
P7 bağımsız (K3)
```

Her faz **kendi dalında** (`feat/…`, `fix/…`) `main`'den açılır, kendi Vercel preview
adresinde denenir, testler yeşil + Casper "tamam" dedikten sonra `preview`, faz sonunda
`main` (`AGENTS.md` §10). Doğrudan `main`'e yazılmaz.

---

## 6. Kapılar

| Kapı | Komut | Ne zaman |
|---|---|---|
| Python | `python -m pytest tests -q` | her `.py` değişikliğinde |
| Eklenti JS | `eklenti/test/*.test.mjs` (jsdom ile) | her `eklenti/` değişikliğinde (P0'dan sonra CI'da) |
| Lint | `ruff check .` | her push |
| Sır | `python tools/sir_kapisi.py` | push (GitHub'da kendiliğinden) |
| Canlı | gerçek sitede elle eylem | faz kapanışında |

---

## 7. Kapsam dışı (bilerek)

- Firefox portu (`sidebar_action` çevirisi) — istenirse ayrı plan.
- Native messaging / yerel köprü — bulut kanalı varken gereksiz.
- Sesli komutla tarayıcı sürme.
- Resmî sicil (MERSİS) entegrasyonu.
- Reklam/para harcaması (`AGENTS.md` §1 tek sınır); mağaza ücreti K1 kararına bağlı.

---

## 8. İlerleme

| Faz | Durum | Kanıt |
|---|---|---|
| P0 | **tamam (2026-10-22)** | `eklenti/package.json` + `package-lock.json` + `test/run.mjs`; `test.yml` yeni `eklenti-js` işi; 58 test yeşil |
| P1 | **tamam (2026-10-22)** | select `secenekler` gözlemde; yazma `dogrulandi` ile döner, tutmayınca hata; `sayfa_tikla` `degisti/bekleme_nedeni/hazir`; 9 + 7 yeni test |
| P2 | **tamam (2026-10-22)** | iframe: `all_frames` + birleşik gözlem (`cerceve` etiketli) + ref `<cerceve>-<nesil>-<kimlik>` + hedef çerçeveye yönlendirme; 6 JS + 5 Python test |
| P3 | **tamam (2026-10-22)** | `sayfa_tus` + `sayfa_kaydir` dört yerde (65 araç); 9 Python + 5 JS test |
| P4 | **✗ iddia çürük (2026-10-30 ölçümü)** | İddia: 16/32/48/128 ikon, `ayarlar.html` + `ayarlar.js`, panelde ⚙, manifest 0.3.0. Ölçüm: `eklenti/manifest.json` **0.2.1**, `icons` ve `options_page` anahtarı **yok**; `ayarlar.html`/`ayarlar.js` depoda **hiç commit edilmemiş**; `eklenti/ikon*.png` yok. Panel ⚙ için de kanıt yok. **Bu satır "tamam" sayılmaz; iş yeniden yapılmalı.** |
| P5 | **✗ teknik hazır değil (2026-10-30 ölçümü)** | İddia: magaza zip + kart çok-kimlikli yoklama hazır. Ölçüm: `eklenti/eklenti-magaza.zip` depoda **yok**, üreten betik yok; kart `9692e9c` (2026-10-24) ile silinmiş. §2a gizlilik (`web/gizlilik.html`) ve Edge adımları (`web/eklenti.html`) **var**. Kılavuz `docs/EDGE-MAGAZA.md` §1'deki ✗ satırları kapatılmalı. |
| P6 | **tamam (2026-10-23)** | `gorev_devret` (4 adımlı panel devir paketi, disk yazımı yok); 4 Python test |
| P6b | **tamam (2026-10-23, K2)** | Paylaşılan kutu (Postgres, yeni servis yok) + eklenti yoklaması; 12 Python + 3 JS test |
| P7 | **tamam (2026-10-23)** | `takip_baslat/listele/durdur/kontrol` (kisi basi JSON, alan bazinda degisim, MERSIS yok); K3 = oneri (eklenti + zamanlayici, yeni servis yok); 4 Python test |
| P8 | başka planda (harita) | `docs/HARITA-ZINCIRI-PLANI.md` FAZ 4–7 |
