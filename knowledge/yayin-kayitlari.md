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
