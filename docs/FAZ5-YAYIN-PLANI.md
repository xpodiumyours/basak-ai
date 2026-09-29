# FAZ 5 — YAYIN GÜNÜ PLANI (yalnız Casper onayıyla işler)

**Tarih:** 2026-09-28 · **Dal:** `feat/freetools-koprosu`
Kural: bu listede Casper'ın açık "olur"u olmadan hiçbir üretim işlemi yapılmaz.

## 0. Ön denetim (ajan yaptı, 2026-09-28)

| Kontrol | Durum |
|---|---|
| Kod: 851 test yeşil, chatbot yasağı 11/11 | ✅ |
| Preview: tüm Faz 2+3 sayfaları 200 (6/6 canlı doğrulandı) | ✅ |
| `BASAK_WEB_TOKEN` (yönetici kapısı) Production'da var | ✅ |
| `DATABASE_URL` (Postgres — kota + hafıza) Production'da var | ✅ |
| Model anahtarları (GROQ, GEMINI...) Production'da var | ✅ |
| `BASAK_OTURUM_ANAHTARI` Production'da | ❌ **EKLENECEK** |
| `BASAK_ANONIM_KOTA_TAVAN` Production'da | — isteğe bağlı (yoksa 50) |

## 1. Casper'ın yapacakları (sırayla, ~10 dakika)

1. **Oturum anahtarını ekle** (üretimde imzalı çerezin anahtarı):
   - Vercel → basak-vercel → Settings → Environment Variables
   - `BASAK_OTURUM_ANAHTARI` = uzun rastgele bir metin (32+ karakter)
     - üretebilirsin: `python -c "import secrets; print(secrets.token_urlsafe(32))"`
   - Environment: **Production** (Preview'da gerekmez ama eklersen zarar yok)
2. **Preview'da 10 maddeyi test et** (BIRLIKTE-TEST-SENARYOLARI.md) → "olur"
3. **Tek üretim deployu:** ajan `vercel --prod` çalıştırır (1 deploy)
4. Yayın sonrası ajan canlı denetim raporu verir (sayfalar + kota + kimlik)

## 2. Ajanın yayın günü yapacakları (onay sonrası)

- `vercel --prod` — tek deploy (Faz 5 bütçesi: 1)
- Üretimde canlı denetim: `/`, `/araclar`, örnek araç sayfası, `sitemap.xml`,
  `robots.txt`, `/api/kimlik` (anonim ID üretmeli), kota davranışı
- `BASAK_ANONIM_KOTA_TAVAN` üretimde istenirse ayarlanır (varsayılan 50)
- Geri alma planı: sorun olursa Vercel dashboard → önceki production
  deployment → "Promote to Production" (ekstra deploy harcamaz)

## 3. Yayın sonrası görünürlük (Casper hesabıyla)

1. **Google Search Console:** mülk ekle (Domain) → DNS doğrulama
2. `https://<üretim>/sitemap.xml` gönder
3. Bir hafta sonra "Sayfalar" raporundan dizine eklenmeyi izle
4. (İsteğe bağlı) Bing Webmaster Tools — aynı sitemap

## 4. Hukuk/vergi görevleri (ajandan hatırlatma — Casper'ın işi)

| Görev | Kime | Not |
|---|---|---|
| KVKK aydınlatma metni + çerez politikası onayı | Avukat | `web/gizlilik.html`, `web/cerez.html` TASLAK; kaynak: `docs/KVKK-ENVANTER.md` |
| Kullanım şartları + sorumluluk reddi onayı | Avukat | `web/sartlar.html`, `web/sorumluluk.html` TASLAK |
| Bağış/sponsor gelir modeli | Mali müşavir | vergi beyanı, makbuz düzeni |
| (Reklam açılırsa) reklam ağının çerez beyanı | Avukat | onay akışı zaten koda gömülü |

## 5. Yayın kararı kapısı

- [ ] Casper: 10 madde testi "olur"
- [ ] Casper: `BASAK_OTURUM_ANAHTARI` eklendi
- [ ] Casper: "Üretime çık" onayı → ajan tek deploy yapar
