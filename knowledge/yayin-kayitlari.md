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
