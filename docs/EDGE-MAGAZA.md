# EDGE MAĞAZASI BAŞVURUSU — ücretsiz yol (Chrome 5 $'ı beklemeden)

**Karar:** Önce Edge Add-ons (ücretsiz), sonra Chrome Web Store.
**Durum:** Teknik hazırlık depoda bitti; başvuru Casper'ın 15 dakikası.

Kaynak: Microsoft Learn "Publish a Microsoft Edge extension"
(`learn.microsoft.com/.../publish/publish-extension`).

---

## 1. Hazır olanlar (depoda, testli)

| Gereksinim | Durum |
|---|---|
| Mağaza paketi | `/eklenti/eklenti-magaza.zip` — manifest ZIP kökünde, `key` yok, `test/` ve `OKUBENI.md` girmez (test: `test_magaza_paketi_kokte_manifest_key_yok`) |
| Geliştirici zip'i (manuel kurulum) | `/eklenti/eklenti.zip` — değişmedi, tek klasör altında |
| İkonlar 16/32/48/128 | `eklenti/ikon*.png`, `ui/style.css` paletinden üretildi |
| Seçenekler sayfası | `ayarlar.html` — adres/anahtar + "Bağlantıyı sına" (kaydetmeden dener) |
| Mağaza kimliği sonrası kart | `web/eklenti-kart.js` kimlik LİSTESİ yoklar; onay sonrası atanan kimlik listenin başına eklenir (test: `yoklama bilinen kimlik adresine yapılır`) |
| Gizlilik sayfasında eklenti bölümü | `/gizlilik.html` §2a (okunan/okunmayan veri, yerel saklama, tek amaç) |
| Kurulum sayfasında Edge adımları | `/eklenti.html` — `edge://extensions` + mağaza paketi bağlantısı |
| Uzak kod | yok (MV3; tüm betikler yerel) |
| İzinler (en az) | `storage` (ayar), `tabs` (etkin sekme bilgisi), `scripting` (sayfaya içerik betiği enjeksiyonu), `sidePanel` (yan panel). Hepsi kodda gerçekten kullanılır. |

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

1. Mağazanın verdiği **eklenti kimliği** `web/eklenti-kart.js`
   `EKLENTI_IDLER` listesinin başına eklenir.
2. Testler koşar (`test_eklenti_kimligi_kartta` yeni kimliği de yoklar —
   test güncellenir).
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
