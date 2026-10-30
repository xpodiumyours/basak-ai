# EDGE MAĞAZASI BAŞVURUSU — ücretsiz yol (Chrome 5 $'ı beklemeden)

**Karar:** Önce Edge Add-ons (ücretsiz), sonra Chrome Web Store.
**Durum (2026-10-30 ölçümü):** Teknik hazırlık **depoda bitmedi.**
Aşağıdaki tabloda ✗ ile işaretli dört varlık depoda yok: mağaza zip'i,
geliştirici zip'i, ikonlar, seçenekler sayfası. `eklenti/manifest.json`
içinde de `icons` ve `options_page` anahtarı yok (sürüm **0.2.1**). Başvuru
öncesi bunlar üretilmeli — "15 dakikada biter" değil.

Kaynak: Microsoft Learn "Publish a Microsoft Edge extension"
(`learn.microsoft.com/.../publish/publish-extension`).

---

## 1. Hazır olanlar (depoda, testli)

| Gereksinim | Durum (2026-10-30 ölçümü) |
|---|---|
| Mağaza paketi | ✗ `/eklenti/eklenti-magaza.zip` **depoda yok**; üreten betik de yok (`.py/.yml/.mjs` taraması boş); anılan `test_magaza_paketi_kokte_manifest_key_yok` testi **yok**. |
| Geliştirici zip'i (manuel kurulum) | ✗ `/eklenti/eklenti.zip` **depoda yok.** |
| İkonlar 16/32/48/128 | ✗ `eklenti/ikon*.png` **hiç commit edilmemiş**; `manifest.json`'da `icons` anahtarı yok. |
| Seçenekler sayfası | ✗ `ayarlar.html` / `ayarlar.js` **depoda hiç yok**; `manifest.json`'da `options_page` yok. |
| Mağaza kimliği sonrası kart | ✗ `web/eklenti-kart.js` ve `#eklentiKarti` 2026-10-24'te `9692e9c` ile silindi; `EKLENTI_IDLER` ve `yoklama bilinen kimlik adresine yapılır` testi artık yok. |
| Gizlilik sayfasında eklenti bölümü | ✓ `/gizlilik.html` (gerçek dosya: `web/gizlilik.html`). |
| Kurulum sayfasında Edge adımları | ✓ `/eklenti.html` (gerçek dosya: `web/eklenti.html`). |
| Uzak kod | ✓ yok (MV3; tüm betikler yerel). |
| İzinler (en az) | ✓ `storage`, `tabs`, `scripting`, `sidePanel` — `manifest.json`'da birebir aynı, hepsi kodda kullanılıyor. |

---

## 2. Başvuru adımları (Casper)

1. **Kayıt (ücretsiz):** `partner.microsoft.com` → Microsoft hesabınla giriş →
   Edge programına kayıt. Ücret yok, kart istenmez.
2. **Yeni uzantı:** Kontrol paneli → Edge kartı → **Create new extension**.
3. **Paket yükle:** `/eklenti/eklenti-magaza.zip` indir, sürükle-bırak.
   Reddederse hata metnini aynen sakla (ajan düzeltir).
4. **Availability:** Visibility `Public`, Markets varsayılan (tümü).
5. **Properties:** Category: **Productivity**. Website: sitenin kökü.
   Support: `/destek.html` adresi.
6. **Privacy** (kopyala-yapıştır hazır):
   - **Single Purpose:** *"Başak'ın açık sekmesini okuyup, kullanıcının tek
     tek onayladığı tıklama/yazma/tuş işlemlerini uygulaması. Eklenti karar
     vermez, model çağırmaz, kendi başına hiçbir şeye basmaz."*
   - **storage:** *"Bağlantı adresi ve anahtar yalnız bu tarayıcıda saklanır."*
   - **tabs:** *"Onay kartında hangi sayfada işlem yapılacağını göstermek
     için etkin sekmenin adresi ve başlığı okunur."*
   - **scripting:** *"Sayfa gözlemini çıkaran içerik betiği sekmeye
     yerleştirilir; başka betik çalıştırılmaz."*
   - **sidePanel:** *"Sohbet ve onay kartı yan panelde gösterilir."*
   - **Remote code:** *No.* **Data usage:** sayfa görünümü + yerel ayarlar.
     **Privacy Policy URL:** sitenin `/gizlilik.html` adresi.
7. **Store listing (dil: Türkçe + İngilizce):**
   - Ad (manifestten gelir, salt-okunur): `Başak — sayfa gözü`
   - Kısa açıklama: *"Başak'ın açık sekmeyi görmesini sağlar; tıklama ve
     yazma yalnız senin onayınla yapılır."*
   - İngilizce: *"Let Başak see your open tab; clicks and typing only run
     with your approval."*
   - **En az 1 ekran görüntüsü:** 1280×800 veya 640×480, JPEG/PNG
     (şeffaflık yok). 3 kare yeter: (a) panel + onay kartı, (b) gözlem
     önizlemesi, (c) ayarlar sayfası. Üzerinde kişisel veri olmasın.
   - Search terms: `başak, panel, sayfa okuma, otomasyon, asistan`
8. **Certification notes (incelemeciye not):** *"Kurulum sonrası rozet
   BAĞLI olur (wss://basak-vercel.vercel.app/api/eklenti). Herhangi bir
   sayfada 'bu sayfada ne var' yazın; gözlem panelde görünür. Tıklama/yazma
   için panelde Onayla'ya basın. Şifre alanına yazmayı reddettiğini
   görmek için bir giriş formunda deneyin."*
9. **Submit.** İnceleme genelde 1–3 iş günü.

---

## 3. Onay SONRASI (tek iş, ajan yapar)

1. Mağazanın verdiği **eklenti kimliği** bir kimlik listesine eklenir.
   ⚠️ 2026-10-30 ölçümü: bu listenin taşıyıcısı `web/eklenti-kart.js`
   `9692e9c` (2026-10-24) ile silindi ve yerine konulmadı — **bu adım şu an
   uygulanamaz**, önce yeni bir kimlik listesi yazılmalı.
2. İlgili test koşar. ⚠️ `test_eklenti_kimligi_kartta` artık yok; kart
   kaldırılırken silinmiş.
3. Yayınlanır; kart hem zip kurulumunu hem mağaza sürümünü "kurulu" tanır.

---

## 4. Mobilde eklenti (araştırma notu, 2026-10-23)

| Tarayıcı | Durum | Hüküm |
|---|---|---|
| Chrome Android | Eklenti desteği **yok** (2026'da da açılmadı) | O yolda mobil imkânsız |
| Edge Android | Menü → Extensions ile mağaza eklentileri kurulur (liste genişliyor); yayınlanmamış paketi kararlı sürüme yandan yükleme **yok** (Canary'de yalnız mağaza kimliğiyle kurulum) | **Mobil = mağaza kaydı gerektirir.** Bu başvuru aynı zamanda mobilin anahtarıdır |
| Firefox Android | Açık katalog + özel koleksiyon var, ama kodumuz Chromium MV3 (`sidePanel` dahil) — **port gerektirir** + Mozilla imzası (ücretsiz) | Ayrı proje, bu planda yok |
| iOS (Safari) | Xcode uygulama sarmalayıcı + Apple Developer (yıllık 99 $) ister | Para sınırı nedeniyle kapsam dışı |
| Masaüstü (zip) | `eklenti.zip` + `chrome://extensions` / `edge://extensions` geliştirici modu — bugün çalışıyor | Mağazasız kullanımın yolu; otomatik güncelleme yok |

**Sonuç:** Masaüstü bugün zip ile tamam; **mobilin tek gerçekçi yolu Edge
mağaza kaydıdır** (yayınlanınca Edge Android'den kurulur). Firefox portu
istenirse ayrı plan açılır.
